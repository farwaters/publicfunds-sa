"""Data-quality suite. Runs inside every build (results -> ops.dq_result) and again under pytest.

Each check returns a failure count; 0 = pass. Severity 'error' fails the build/tests; 'warn' is reported.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from thusa.raw import sha256_file

CURATED_LINEAGE_TABLES = ["gov_body", "muni_fin_line", "muni_total", "nat_budget_line", "uifw_line", "audit_outcome", "award",
                          "ocds_release", "restriction", "payment", "fuel_price", "cpi"]
MIN_ROWS = {"curated.gov_body": 250, "curated.muni_fin_line": 50_000, "curated.nat_budget_line": 50,
            "curated.uifw_line": 1_000, "curated.audit_outcome": 1_000, "curated.award": 1_000,
            "curated.ocds_release": 10_000, "curated.restriction": 100, "marts.coverage_cell": 1_000}

# CHG-2026-035: months of curated.fuel_price that are known to be absent between the first and the last month present.
# Each entry is (year, month) -> "KE id: reason". EMPTY on purpose: no month is missing from 2019-01 to the latest month
# (KE-012, CHG-2026-027 recovered 2025-12). Pre-2019 history is outside the range, so it is not a gap here. Months
# whose DMPR monthly workbook returns HTTP 404 (2023-02, 2023-06) are present in the series from the history PDFs,
# so they are not gaps either. Adding an entry needs an RFC row that names the known error and the source.
FUEL_KNOWN_GAPS: dict[tuple[int, int], str] = {}


def month_gaps(months: Iterable[tuple[int, int]], known: Mapping[tuple[int, int], str]) -> dict:
    """Pure: the months missing between the first and the last (year, month) present, split into expected (in
    `known`) and new (not in `known`). `stale_known` lists `known` months that are present after all (remove them)."""
    present = set()
    for y, m in months:
        if not (isinstance(y, int) and isinstance(m, int) and 1 <= m <= 12):
            raise ValueError(f"not a (year, month): {(y, m)!r}")
        present.add((y, m))
    if not present:
        return {"first": None, "last": None, "present": 0, "missing": [], "expected": [], "new": [], "stale_known": []}
    first, last = min(present), max(present)
    missing, y, m = [], *first
    while (y, m) < last:
        if (y, m) not in present:
            missing.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return {"first": first, "last": last, "present": len(present), "missing": missing,
            "expected": [g for g in missing if g in known], "new": [g for g in missing if g not in known],
            "stale_known": sorted(g for g in known if g in present)}


def fuel_continuity(con, known: Mapping[tuple[int, int], str] | None = None) -> dict:
    """Read-only month-continuity check of curated.fuel_price (CHG-2026-035)."""
    rows = con.execute("SELECT DISTINCT year, month FROM curated.fuel_price").fetchall()
    return month_gaps([(int(y), int(m)) for y, m in rows], FUEL_KNOWN_GAPS if known is None else known)


def checks(min_rows: dict | None = None) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for t, n in (min_rows if min_rows is not None else MIN_ROWS).items():
        out.append((f"row_count_min:{t}>={n}", "error", f"SELECT CASE WHEN count(*) >= {n} THEN 0 ELSE 1 END FROM {t}"))
    for t in CURATED_LINEAGE_TABLES:
        out.append((f"lineage_present:{t}", "error",
                    f"SELECT count(*) FROM curated.{t} WHERE source_id IS NULL OR source_file IS NULL "
                    f"OR source_sha256 IS NULL OR fetched_at_utc IS NULL"))
        out.append((f"lineage_resolves:{t}", "error",
                    f"SELECT count(*) FROM curated.{t} c LEFT JOIN ops.raw_file r ON r.sha256 = c.source_sha256 "
                    f"WHERE r.sha256 IS NULL"))
    out += [
        ("money_columns_are_bigint_cents", "error",
         "SELECT count(*) FROM information_schema.columns WHERE table_schema IN ('staging','curated','marts') "
         "AND column_name LIKE '%cents' AND data_type <> 'BIGINT'"),
        ("nulls_preserved:muni_fin_line", "error",
         "SELECT abs((SELECT count(*) FROM staging.muni_incexp WHERE amount_cents IS NULL) - "
         "(SELECT count(*) FROM curated.muni_fin_line WHERE amount_cents IS NULL))"),
        ("province_codes_official", "error",
         "SELECT count(*) FROM curated.gov_body WHERE sphere = 'local' AND (province IS NULL OR province NOT IN "
         "('EC','FS','GT','KZN','LP','MP','NC','NW','WC'))"),
        ("derived_totals_match_published", "error",
         "SELECT CASE WHEN count(*) FILTER (WHERE abs(derived_expenditure_cents - published_expenditure_cents) "
         "<= 0.005 * abs(published_expenditure_cents)) >= 0.99 * count(*) THEN 0 ELSE 1 END "
         "FROM curated.muni_total WHERE published_expenditure_cents IS NOT NULL"),
        ("zero_placeholder_is_null:award", "error",
         "SELECT count(*) FROM curated.award WHERE value_note IN ('missing','zero_placeholder') AND value_cents IS NOT NULL"),
        ("no_zero_award_values", "error", "SELECT count(*) FROM curated.award WHERE value_cents = 0"),
        ("sentinel_is_null:nt_bva", "error",
         "SELECT count(*) FROM staging.nt_bva WHERE value_note = 'sentinel' AND amount_cents IS NOT NULL"),
        ("unique:muni_fin_line", "error",
         "SELECT count(*) - count(DISTINCT (gov_body_id, fye, amount_type, item_code)) FROM curated.muni_fin_line"),
        ("unique:award", "error",
         "SELECT count(*) - count(DISTINCT (ocid, award_id, coalesce(supplier_id,''), coalesce(supplier_name,''))) FROM curated.award"),
        ("unique:coverage_cell", "error",
         "SELECT count(*) - count(DISTINCT (gov_body_id, fye, data_type)) FROM marts.coverage_cell"),
        ("coverage_states_valid", "error",
         "SELECT count(*) FROM marts.coverage_cell WHERE state NOT IN ('present','partial','missing','n.a.')"),
        ("coverage_reason_for_non_present", "error",
         "SELECT count(*) FROM marts.coverage_cell WHERE state <> 'present' AND reason_code IS NULL"),
        ("popia_no_raw_sa_id_in_restriction", "error",
         "SELECT count(*) FROM curated.restriction WHERE regexp_matches(coalesce(name,'') || coalesce(cipc_reg_no,'') "
         "|| coalesce(reason,''), '\\d{13}')"),
        ("popia_no_raw_sa_id_in_staging_rsr", "error",
         "SELECT count(*) FROM staging.rsr WHERE regexp_matches(coalesce(name,'') || coalesce(cipc_reg_no,''), '\\d{13}')"),
        ("popia_person_hmac_shape", "error",
         "SELECT count(*) FROM curated.restriction WHERE person_id_hmac IS NOT NULL AND NOT regexp_matches(person_id_hmac, '^[0-9a-f]{64}$')"),
        ("popia_no_person_names_in_flags", "error",
         "SELECT count(*) FROM marts.flag f JOIN curated.restriction r ON r.is_person AND f.subject_name = r.name"),
        ("flags_named_supplier_pending_review", "error",
         "SELECT count(*) FROM marts.flag WHERE names_supplier AND review_status <> 'pending human review'"),
        ("flags_never_published_unreviewed", "error",
         "SELECT count(*) FROM marts.flag WHERE publish_status = 'published' AND review_status <> 'reviewed'"),
        ("flags_have_evidence_url", "error",
         "SELECT count(*) FROM marts.flag WHERE json_array_length(evidence_json) = 0 "
         "OR NOT list_contains(list_transform(CAST(json_extract(evidence_json, '$[*].url') AS VARCHAR[]), x -> x IS NOT NULL), true)"),
        ("unique:fuel_price", "error",
         "SELECT count(*) - count(DISTINCT (year, month, grade)) FROM curated.fuel_price"),
        ("fuel_price_plausible", "error",
         "SELECT count(*) FROM curated.fuel_price WHERE cents_per_litre <= 0 OR cents_per_litre > 10000"),
        ("cpi_plausible", "error", "SELECT count(*) FROM curated.cpi WHERE index_value <= 0 OR index_value > 1000"),
        # CHG-2026-018: CPI freshness (warn only): latest month older than the 120-day target, or OECD fallback in use.
        ("cpi_fresh_imf_info", "warn",
         "SELECT CASE WHEN count(*) FILTER (WHERE source_id = 'oecd_cpi') > 0 OR max(make_date(year, month, 1) "
         "+ INTERVAL 1 MONTH - INTERVAL 1 DAY) < coalesce(getvariable('as_of'), current_date) - 120 "
         "THEN 1 ELSE 0 END FROM curated.cpi"),
        ("award_buyer_match_rate_info", "warn",
         "SELECT count(*) FILTER (WHERE buyer_gov_body_id IS NULL AND buyer_name ILIKE '%municipal%') FROM curated.award"),
    ]
    return out


def run(con, build_id: str, min_rows: dict | None = None, raw_root: Path | None = None) -> list[dict]:
    con.execute("CREATE TABLE IF NOT EXISTS ops.dq_result (build_id VARCHAR, test_name VARCHAR, severity VARCHAR, "
                "status VARCHAR, failures BIGINT, run_at_utc TIMESTAMPTZ DEFAULT now())")
    results = []
    for name, sev, sql in checks(min_rows):
        try:
            failures = int(con.execute(sql).fetchone()[0] or 0)
            status = "pass" if failures == 0 else ("fail" if sev == "error" else "warn")
        except Exception as exc:  # a broken check is a failure, never a silent pass
            failures, status = -1, f"error: {exc}"
        results.append({"test_name": name, "severity": sev, "status": status, "failures": failures})
    # CHG-2026-035: a NEW fuel month gap is reported (warn), never a build failure; known gaps (none today) are not counted.
    try:
        c = fuel_continuity(con)
        failures = len(c["new"]) + len(c["stale_known"])
        status = "pass" if failures == 0 else "warn"
    except Exception as exc:  # a broken check is a failure, never a silent pass
        failures, status = -1, f"error: {exc}"
    results.append({"test_name": "fuel_month_continuity_info", "severity": "warn", "status": status, "failures": failures})
    if raw_root is not None:  # checksum of every referenced raw file still matches
        bad = 0
        for path, sha in con.execute("SELECT path, sha256 FROM ops.raw_file").fetchall():
            p = Path(raw_root) / path
            bad += int(not p.exists() or sha256_file(p) != sha)
        results.append({"test_name": "raw_files_checksum_match", "severity": "error",
                        "status": "pass" if bad == 0 else "fail", "failures": bad})
    for r in results:
        con.execute("INSERT INTO ops.dq_result (build_id, test_name, severity, status, failures) VALUES (?,?,?,?,?)",
                    [build_id, r["test_name"], r["severity"], r["status"], r["failures"]])
    return results
