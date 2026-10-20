"""MVP red-flag detectors (D1, D3, D4, D5, D8, D13). Each returns flag dicts; build() writes marts.flag.

Flags are automated indicators, not findings. Every flag starts unreviewed; any flag that names a supplier or
person is 'pending human review' and must never be published as confirmed (ADR-0005).
"""
from __future__ import annotations

import hashlib
import json
import re

import duckdb

MUNI_API = "https://municipaldata.treasury.gov.za/api/cubes"
MUNI_PROFILE = "https://municipalmoney.gov.za/profiles/municipality-{code}/"
OCDS_BULK = "https://data.open-contracting.org/en/publication/143"
RSR_URL = "https://ocpo.treasury.gov.za/RestrictedSupplier/RestrictedSuppliersReport.pdf"


def _id(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _rand(cents) -> str:
    return "unknown" if cents is None else f"R{cents / 100:,.0f}"


def _muni_query(cube: str, code: str, fye: int, extra: str = "") -> str:
    from urllib.parse import quote
    cut = f'demarcation.code:"{code}"|financial_year_end.year:{fye}{extra}'
    dd = "item.code|amount_type.code" if cube == "incexp_v2" else "item.code"
    return f"{MUNI_API}/{cube}/aggregate?drilldown={quote(dd)}&cut={quote(cut)}&aggregates=amount.sum"


def _flag(detector, cfg, subject_type, subject_id, subject_name, gov_body_id, period, severity, score, title,
          explanation, evidence, names_supplier):
    return {
        "flag_id": _id(detector, subject_id, gov_body_id, period),
        "detector_id": detector, "detector_version": cfg["version"],
        "subject_type": subject_type, "subject_id": subject_id, "subject_name": subject_name,
        "gov_body_id": gov_body_id, "period_label": period, "severity": severity, "score": score,
        "title": title, "explanation": explanation, "evidence_json": json.dumps(evidence),
        "names_supplier": names_supplier,
        "review_status": "pending human review" if names_supplier else "unreviewed",
        "publish_status": "not published",
    }


# ------------------------------------------------------------------------------------------------ D1
def d1_overspend(con: duckdb.DuckDBPyConnection, cfg: dict) -> list[dict]:
    t, hi, min_budget = cfg["threshold"], cfg["severity"]["high"], cfg["min_budget_rand"] * 100
    flags = []
    rows = con.execute("""
        WITH l AS (
          SELECT gov_body_id, fye, fy_label, amount_type, sum(amount_cents) AS v, count(amount_cents) AS n,
                 max(source_sha256) AS sha, max(fetched_at_utc) AS fetched
          FROM curated.muni_fin_line
          WHERE item_code BETWEEN '3000' AND '4300' AND NOT list_contains(?, item_code)
          GROUP BY ALL),
        x AS (
          SELECT gov_body_id, fye, fy_label,
                 max(v) FILTER (WHERE amount_type='AUDA' AND n > 0) AS auda,
                 max(v) FILTER (WHERE amount_type='ADJB' AND n > 0) AS adjb,
                 max(v) FILTER (WHERE amount_type='ORGB' AND n > 0) AS orgb,
                 max(sha) AS sha, max(fetched) AS fetched
          FROM l GROUP BY ALL)
        SELECT x.*, coalesce(adjb, orgb) AS budget, CASE WHEN adjb IS NOT NULL THEN 'ADJB' ELSE 'ORGB' END AS basis,
               g.name, g.demarcation_code, t.total_expenditure_cents AS total_auda
        FROM x JOIN curated.gov_body g USING (gov_body_id)
        LEFT JOIN curated.muni_total t ON t.gov_body_id = x.gov_body_id AND t.fye = x.fye AND t.amount_type = 'AUDA'
        WHERE auda IS NOT NULL AND coalesce(adjb, orgb) >= ? AND auda > coalesce(adjb, orgb) * (1 + ?)
        ORDER BY auda::DOUBLE / coalesce(adjb, orgb) DESC""", [cfg["non_cash_items"], min_budget, t]).fetchall()
    cols = [d[0] for d in con.description]
    for r in rows:
        r = dict(zip(cols, r))
        ratio = r["auda"] / r["budget"] - 1
        drivers = con.execute("""
            SELECT item_label, max(amount_cents) FILTER (WHERE amount_type='AUDA') -
                   max(amount_cents) FILTER (WHERE amount_type=?) AS diff
            FROM curated.muni_fin_line WHERE gov_body_id=? AND fye=? AND item_code BETWEEN '3000' AND '4300'
              AND NOT list_contains(?, item_code)
            GROUP BY 1 HAVING diff IS NOT NULL ORDER BY diff DESC LIMIT 3""",
                              [r["basis"], r["gov_body_id"], r["fye"], cfg["non_cash_items"]]).fetchall()
        drv = "; ".join(f"{lbl} +{_rand(d)}" for lbl, d in drivers if d and d > 0)
        suspect = ratio >= cfg["suspect_data_error_ratio"]
        flags.append(_flag(
            "D1_overspend_vs_budget", cfg, "gov_body", r["gov_body_id"], r["name"], r["gov_body_id"], r["fy_label"],
            "info" if suspect else ("high" if ratio >= hi else "med"), round(ratio, 4),
            ("Possible source data error - " if suspect else "")
            + f"{r['name']}: audited cash operating expenditure {ratio:.0%} above {r['basis']} budget ({r['fy_label']})",
            f"Audited operating expenditure excluding non-cash items (depreciation, debt impairment, write-offs, "
            f"losses) {_rand(r['auda'])} vs {'adjusted' if r['basis']=='ADJB' else 'original'} budget "
            f"{_rand(r['budget'])} on the same basis (audited total expenditure incl. non-cash: "
            f"{_rand(r['total_auda'])}). Largest item overruns: {drv or 'n/a'}. Overspending a budget vote can be "
            "unauthorised expenditure under the MFMA, but classification differences between budget and AFS also "
            "cause gaps: a prompt to look, not a finding.",
            [{"label": "Municipal Finance API query (incexp_v2)",
              "url": _muni_query("incexp_v2", r["demarcation_code"], r["fye"], '|period_length.length:"year"'),
              "sha256": r["sha"], "fetched_at_utc": str(r["fetched"])},
             {"label": "Municipal Money profile", "url": MUNI_PROFILE.format(code=r["demarcation_code"])}],
            False))
    # national departments: audit outcome vs final appropriation
    nat = con.execute("""
        WITH x AS (SELECT gov_body_id, department, financial_year, fy_label,
                     max(amount_cents) FILTER (WHERE budget_phase='Audit Outcome') AS actual,
                     max(amount_cents) FILTER (WHERE budget_phase='Final Appropriation') AS final,
                     max(n_unknown_lines) AS unk, max(source_file) AS file, max(source_sha256) AS sha
                   FROM curated.nat_budget_line GROUP BY ALL)
        SELECT * FROM x WHERE actual IS NOT NULL AND final IS NOT NULL AND final >= ?
          AND actual > final * (1 + ?) ORDER BY actual::DOUBLE / final DESC""",
                      [min_budget, cfg["national_threshold"]]).fetchall()
    ncols = [d[0] for d in con.description]
    for r in nat:
        r = dict(zip(ncols, r))
        ratio = r["actual"] / r["final"] - 1
        flags.append(_flag(
            "D1_overspend_vs_budget", cfg, "gov_body", r["gov_body_id"], r["department"], r["gov_body_id"],
            r["fy_label"], "high" if ratio >= hi else "med", round(ratio, 4),
            f"{r['department']}: audited expenditure {ratio:.1%} above final appropriation ({r['fy_label']})",
            f"Audit outcome {_rand(r['actual'])} vs final appropriation {_rand(r['final'])} (sum of Vulekamali "
            f"budget-vs-actual lines; {r['unk']} line(s) with unknown value excluded). Spending above the "
            "appropriation is unauthorised expenditure under the PFMA unless authorised; check the AG report.",
            [{"label": "Vulekamali: Budgeted and Actual National Expenditure",
              "url": "https://vulekamali.gov.za/datasets/budgeted-and-actual-national-expenditure",
              "file": r["file"], "sha256": r["sha"]}], False))
    return flags


# ------------------------------------------------------------------------------------------------ D3
def d3_restricted_awarded(con, cfg: dict) -> list[dict]:
    rows = con.execute("""
        WITH m AS (
          SELECT a.*, r.subject_id, r.is_person, r.name AS rsr_name, r.cipc_reg_no, r.restriction_type, r.reason,
                 r.period_from, r.period_to, r.authorised_by, r.source_locator AS rsr_locator,
                 r.source_sha256 AS rsr_sha,
                 CASE WHEN r.is_person AND a.supplier_person_key = r.name_key THEN 0.90
                      WHEN NOT r.is_person AND a.supplier_key = r.name_key AND len(string_split(r.name_key, ' ')) >= 2 THEN 0.92
                      WHEN NOT r.is_person AND a.supplier_key = r.name_key THEN 0.60 END AS confidence
          FROM curated.award a JOIN curated.restriction r
            ON (NOT r.is_person AND a.supplier_key = r.name_key) OR (r.is_person AND a.supplier_person_key = r.name_key)
        )
        SELECT * FROM m WHERE confidence >= ? AND award_date BETWEEN period_from AND period_to
        ORDER BY value_cents DESC NULLS LAST""", [cfg["min_match_confidence"]]).fetchall()
    cols = [d[0] for d in con.description]
    flags = []
    for r in map(lambda x: dict(zip(cols, x)), rows):
        shown = "Natural person (name withheld pending review)" if r["is_person"] else r["supplier_name"]
        flags.append(_flag(
            "D3_restricted_supplier_awarded", cfg, "person" if r["is_person"] else "supplier", r["subject_id"],
            shown, r["buyer_gov_body_id"] or f"BUYER:{r['buyer_id']}", str(r["award_date"]), "high",
            r["confidence"],
            f"Award to a name matching the Restricted Supplier register, inside the restriction window: {shown}",
            f"eTenders award {r['ocid']} / {r['award_id']} by {r['buyer_name']} dated {r['award_date']} "
            f"({r['award_date_basis']}), value {_rand(r['value_cents'])}. Register entry ({r['restriction_type']}, "
            f"{r['reason']}, imposed by {r['authorised_by']}) runs {r['period_from']} to {r['period_to']}. "
            f"MATCH IS BY NAME ONLY (eTenders publishes no registration number); confidence {r['confidence']}. "
            "Could be a different entity with the same name. Pending human review; not a finding.",
            [{"label": "eTenders OCDS record", "ocid": r["ocid"], "url": OCDS_BULK, "locator": r["source_locator"],
              "sha256": r["source_sha256"]},
             {"label": "Tender document", "url": r["doc_url"]},
             {"label": "Restricted Supplier and Tender Defaulter Report", "url": RSR_URL,
              "locator": r["rsr_locator"], "sha256": r["rsr_sha"]}], True))
    return flags


# ------------------------------------------------------------------------------------------------ D4
def d4_concentration(con, cfg: dict) -> list[dict]:
    rows = con.execute("""
        WITH a AS (
          SELECT buyer_id, any_value(buyer_name) AS buyer_name, any_value(buyer_gov_body_id) AS gb,
                 supplier_key, any_value(supplier_name) AS supplier_name, sum(value_cents) AS v, count(*) AS n
          FROM curated.award
          WHERE n_suppliers = 1 AND value_cents IS NOT NULL AND value_note IS NULL
            AND award_date >= (SELECT max(award_date) FROM curated.award) - INTERVAL (?) YEAR
          GROUP BY buyer_id, supplier_key),
        b AS (SELECT buyer_id, sum(v) AS total, sum(n) AS n_awards, count(*) AS n_suppliers FROM a GROUP BY 1),
        s AS (SELECT a.*, b.total, b.n_awards, b.n_suppliers, a.v::DOUBLE / b.total AS share FROM a JOIN b USING (buyer_id))
        SELECT buyer_id, any_value(buyer_name) AS buyer_name, any_value(gb) AS gb, any_value(total) AS total,
               any_value(n_awards) AS n_awards, any_value(n_suppliers) AS n_suppliers,
               sum((share * 100) ^ 2) AS hhi, max(share) AS top_share, arg_max(supplier_name, share) AS top_supplier,
               arg_max(v, share) AS top_value
        FROM s GROUP BY buyer_id
        HAVING any_value(n_awards) >= ? AND any_value(total) >= ? AND sum((share * 100) ^ 2) > ? AND max(share) > ?
        ORDER BY hhi DESC""", [cfg["window_years"], cfg["min_awards"], cfg["min_total_rand"] * 100,
                                cfg["hhi_threshold"], cfg["top_share_threshold"]]).fetchall()
    cols = [d[0] for d in con.description]
    out = []
    for r in map(lambda x: dict(zip(cols, x)), rows):
        out.append(_flag(
            "D4_supplier_concentration", cfg, "gov_body", r["gb"] or f"BUYER:{r['buyer_id']}", r["buyer_name"],
            r["gb"] or f"BUYER:{r['buyer_id']}", f"last {cfg['window_years']}y", "low", round(r["hhi"], 1),
            f"{r['buyer_name']}: award value highly concentrated (HHI {r['hhi']:,.0f}; top supplier {r['top_share']:.0%})",
            f"Across {r['n_awards']} single-supplier awards with a known value ({_rand(r['total'])}) to "
            f"{r['n_suppliers']} supplier(s), the largest recipient ({r['top_supplier']}) received "
            f"{_rand(r['top_value'])}. Concentration can be legitimate (framework contracts, sole providers); "
            "multi-supplier awards and awards without values are excluded. Pending human review.",
            [{"label": "eTenders OCDS (buyer id)", "buyer_id": r["buyer_id"], "url": OCDS_BULK}], True))
    return out


# ------------------------------------------------------------------------------------------------ D5
def d5_value_gaps(con, cfg: dict) -> list[dict]:
    rows = con.execute("""
        SELECT buyer_id, any_value(buyer_name) AS buyer_name, any_value(buyer_gov_body_id) AS gb,
               count(DISTINCT ocid || award_id) AS n,
               count(DISTINCT ocid || award_id) FILTER (WHERE value_cents IS NULL) AS n_unknown,
               count(DISTINCT ocid || award_id) FILTER (WHERE value_note = 'implausible_low') AS n_low,
               count(DISTINCT ocid || award_id) FILTER (WHERE value_note = 'implausible_high') AS n_high
        FROM curated.award GROUP BY buyer_id
        HAVING count(DISTINCT ocid || award_id) >= ?
           AND (count(DISTINCT ocid || award_id) FILTER (WHERE value_cents IS NULL OR value_note IN ('implausible_low','implausible_high')))::DOUBLE
               / count(DISTINCT ocid || award_id) >= ?
        ORDER BY n DESC""", [cfg["min_awards"], cfg["gap_share_threshold"]]).fetchall()
    cols = [d[0] for d in con.description]
    out = []
    for r in map(lambda x: dict(zip(cols, x)), rows):
        share = (r["n_unknown"] + r["n_low"] + r["n_high"]) / r["n"]
        out.append(_flag(
            "D5_award_value_gaps", cfg, "gov_body", r["gb"] or f"BUYER:{r['buyer_id']}", r["buyer_name"],
            r["gb"] or f"BUYER:{r['buyer_id']}", "all loaded", "info", round(share, 4),
            f"{r['buyer_name']}: {share:.0%} of published awards have no usable value",
            f"{r['n']} awards on eTenders OCDS: {r['n_unknown']} with no value or a 0 placeholder, {r['n_low']} below "
            f"R100 (e.g. R10 placeholders), {r['n_high']} above R20bn (implausible). Spending by this buyer cannot "
            "be totalled from public award data.",
            [{"label": "eTenders OCDS (buyer id)", "buyer_id": r["buyer_id"], "url": OCDS_BULK}], False))
    return out


# ------------------------------------------------------------------------------------------------ D8
def d8_irregular_trend(con, cfg: dict) -> list[dict]:
    rows = con.execute("""
        WITH x AS (
          SELECT u.gov_body_id, u.fye, u.fy_label, u.amount_cents AS cur, u.source_sha256 AS sha,
                 lag(u.amount_cents) OVER w AS prev, lag(u.fye) OVER w AS prev_fye,
                 lag(u.amount_cents, 2) OVER w AS prev2, lag(u.fye, 2) OVER w AS prev2_fye
          FROM curated.uifw_line u WHERE uifw_type = 'irregular'
          WINDOW w AS (PARTITION BY gov_body_id ORDER BY fye))
        SELECT x.*, g.name, g.demarcation_code, ao.opinion_label, ao.report_url
        FROM x JOIN curated.gov_body g USING (gov_body_id)
        LEFT JOIN curated.audit_outcome ao USING (gov_body_id, fye)
        WHERE fye >= ? AND prev_fye = fye - 1 AND prev >= ? AND cur IS NOT NULL AND cur >= ?
          AND cur::DOUBLE / prev - 1 >= ?
          AND (NOT ? OR (prev2_fye = fye - 2 AND prev2 IS NOT NULL AND prev > prev2))
        ORDER BY cur - prev DESC""", [cfg["fye_min"], cfg["min_prev_rand"] * 100, cfg["min_amount_rand"] * 100,
                                      cfg["growth_yoy"], cfg["require_two_year_rise"]]).fetchall()
    cols = [d[0] for d in con.description]
    out = []
    for r in map(lambda x: dict(zip(cols, x)), rows):
        g = r["cur"] / r["prev"] - 1
        sev = "high" if g >= cfg["high_growth_yoy"] and r["cur"] >= cfg["high_min_amount_rand"] * 100 else "med"
        ev = [{"label": "Municipal Finance API query (uifwexp)",
               "url": _muni_query("uifwexp", r["demarcation_code"], r["fye"]), "sha256": r["sha"]},
              {"label": "Municipal Money profile", "url": MUNI_PROFILE.format(code=r["demarcation_code"])}]
        if r["report_url"]:
            ev.append({"label": f"AGSA audit report ({r['opinion_label']})", "url": r["report_url"]})
        out.append(_flag(
            "D8_irregular_expenditure_trend", cfg, "gov_body", r["gov_body_id"], r["name"], r["gov_body_id"],
            r["fy_label"], sev, round(g, 4),
            f"{r['name']}: reported irregular expenditure up {g:.0%} year on year ({r['fy_label']})",
            f"Reported irregular expenditure {_rand(r['cur'])} in {r['fy_label']} vs {_rand(r['prev'])} the year "
            f"before and {_rand(r['prev2'])} two years before (AFS note amounts via the Municipal Finance API; whether these are amounts incurred in the year "
            "or closing balances is not stated by the API - unverified). Irregular means a process was not followed, "
            "not necessarily that money was lost.",
            ev, False))
    return out


# ------------------------------------------------------------------------------------------------ D13
PPD_PORTAL = "https://data.etenders.gov.za/"
FUEL_TYPES = {  # UNSPSC commodity codes (class 15101500 Petroleum and distillates) and description words
    "diesel": ({"15101505", "15101513"}, r"\bdiesel\b", ("diesel_005_inland", "diesel_005_coast")),
    "petrol": ({"15101506"}, r"\b(petrol|gasoline|unleaded)\b", ("petrol_93_inland", "petrol_95_coast", "petrol_95_inland")),
    "paraffin": ({"15101502"}, r"\b(paraffin|kerosene)\b", ("paraffin_coast", "paraffin_inland")),
}
_LITRE = re.compile(r"(?i)^(l|lt|ltr|ltrs|litre|litres|liter|liters)$")


def _fuel_type(code, *texts):
    for ft, (codes, rx, _g) in FUEL_TYPES.items():
        if (code or "").strip()[:8] in codes or any(t and re.search(rx, t, re.I) for t in texts):
            return ft
    return None


def _fy_months(label):
    """'2024/25' or '2024/2025' -> the 12 (year, month) pairs April 2024 - March 2025; anything else -> None."""
    m = re.fullmatch(r"\s*(\d{4})\s*/\s*(\d{2}|\d{4})\s*", label or "")
    if not m or int(m.group(2)[-2:]) != (int(m.group(1)) + 1) % 100:
        return None
    y = int(m.group(1))
    return [(y, mo) for mo in range(4, 13)] + [(y + 1, mo) for mo in range(1, 4)]


def d13_fuel_unit_price(con, cfg: dict) -> list[dict]:
    """Implied price per litre on a PPD fuel line (amount / quantity, litres only) above the highest official DMPR
    price for that fuel type in the period by more than `threshold`. Lines without litres, a period or enough
    benchmark months are not assessed (unknown, not 'fine'). Names a supplier: review queue only, never published
    (publication.yaml never_publish)."""
    bench: dict = {}
    for y, mo, grade, c, url, loc in con.execute("SELECT year, month, grade, cents_per_litre, source_url, source_locator "
                                                  "FROM curated.fuel_price").fetchall():
        bench.setdefault((y, mo), {})[grade] = (c, url, loc)
    rows = con.execute("""SELECT department, supplier_name, supplier_key, amount_cents, quantity, unit, payment_date,
                                 financial_year, item_description, commodity_code, commodity_title, source_file,
                                 source_sha256, source_locator
                          FROM curated.payment WHERE amount_cents IS NOT NULL AND quantity > 0""").fetchall()
    cols = [d[0] for d in con.description]
    out = []
    for r in map(lambda x: dict(zip(cols, x)), rows):
        ft = _fuel_type(r["commodity_code"], r["item_description"], r["commodity_title"])
        if not ft or not _LITRE.match((r["unit"] or "").strip()):
            continue
        if r["payment_date"]:
            months, period = [(r["payment_date"].year, r["payment_date"].month)], r["payment_date"].strftime("%Y-%m")
        else:
            months, period = _fy_months(r["financial_year"]), r["financial_year"]
        if not months:
            continue
        grades = FUEL_TYPES[ft][2]
        pts = [(bench[m][g], m) for m in months if m in bench for g in grades if g in bench[m]]
        if len({m for _, m in pts}) < min(len(months), cfg["min_benchmark_months"]):
            continue
        (top, top_url, top_loc), top_m = max(pts, key=lambda p: p[0][0])
        implied = r["amount_cents"] / r["quantity"]
        ratio = implied / top
        if ratio <= 1 + cfg["threshold"]:
            continue
        sev = "high" if ratio >= cfg["high_ratio"] else "med"
        sid = "PPD:" + _id(r["department"], r["supplier_key"], ft, period)
        out.append(_flag(
            "D13_fuel_unit_price", cfg, "payment_line", sid, r["supplier_name"], None, period, sev, round(ratio, 2),
            f"{r['department']}: {ft} at about R{implied / 100:,.2f}/litre vs official up to R{top / 100:,.2f}/litre ({period})",
            f"A Procurement Payments Dashboard line shows {_rand(r['amount_cents'])} paid to {r['supplier_name']} for "
            f"{r['quantity']:,.0f} litres of {ft}, about R{implied / 100:,.2f} per litre. The highest official DMPR price "
            f"for {ft} in {period} was R{top / 100:,.2f} per litre ({top_m[0]}-{top_m[1]:02d}). Diesel and paraffin "
            "figures are wholesale list prices (pump prices are a little higher), and PPD lines are yearly totals per "
            "department, supplier and item; LOGIS quantities can be averages over an item group (PPD user guide, "
            "section 7). A data or unit error is possible. Pending human review; not published.",
            [{"label": "Procurement Payments Dashboard export", "url": PPD_PORTAL, "file": r["source_file"],
              "locator": r["source_locator"], "sha256": r["source_sha256"]},
             {"label": "DMPR Fuel Price History", "url": top_url, "locator": top_loc}], True))
    return out


DETECTORS = {
    "D1_overspend_vs_budget": d1_overspend,
    "D3_restricted_supplier_awarded": d3_restricted_awarded,
    "D4_supplier_concentration": d4_concentration,
    "D5_award_value_gaps": d5_value_gaps,
    "D8_irregular_expenditure_trend": d8_irregular_trend,
    "D13_fuel_unit_price": d13_fuel_unit_price,
}

FLAG_COLS = ["flag_id", "detector_id", "detector_version", "subject_type", "subject_id", "subject_name",
             "gov_body_id", "period_label", "severity", "score", "title", "explanation", "evidence_json",
             "names_supplier", "review_status", "publish_status", "created_run_id"]


def build(con, cfg_all: dict, run_id: str) -> dict:
    con.execute("""CREATE OR REPLACE TABLE marts.flag (
        flag_id VARCHAR PRIMARY KEY, detector_id VARCHAR NOT NULL, detector_version VARCHAR NOT NULL,
        subject_type VARCHAR NOT NULL, subject_id VARCHAR NOT NULL, subject_name VARCHAR, gov_body_id VARCHAR,
        period_label VARCHAR, severity VARCHAR CHECK (severity IN ('info','low','med','high')), score DOUBLE,
        title VARCHAR NOT NULL, explanation VARCHAR NOT NULL, evidence_json JSON NOT NULL,
        names_supplier BOOLEAN NOT NULL,
        review_status VARCHAR NOT NULL CHECK (review_status IN ('unreviewed','pending human review','reviewed','dismissed')),
        publish_status VARCHAR NOT NULL CHECK (publish_status IN ('not published','published')),
        created_run_id VARCHAR NOT NULL)""")
    counts = {}
    for det_id, fn in DETECTORS.items():
        flags = fn(con, cfg_all[det_id])
        seen = set()
        for f in flags:
            if f["flag_id"] in seen:
                continue
            seen.add(f["flag_id"])
            f["created_run_id"] = run_id
            con.execute(f"INSERT INTO marts.flag VALUES ({','.join('?' * len(FLAG_COLS))})", [f[c] for c in FLAG_COLS])
        counts[det_id] = len(seen)
    return counts
