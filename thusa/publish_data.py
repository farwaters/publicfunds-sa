"""Public data export for the public dashboard (ADR-0010, CHG-2026-006).

`pf publish-data` writes compact, versioned, browser-friendly JSON to public-data/v1/. The folder is committed to git
and served from the public site (same origin as the dashboard), so the Grok Build dashboard (and anyone else) can read it.

Rules (tests/test_publish_data.py enforces them):
- Money is integer cents; unknown is null (never 0). Every figure points to a source file entry ("src") with its URL.
- Flags: ONLY review-confirmed flags on current evidence (four-eyes for named suppliers, config/publication.yaml).
  Everything else is reduced to a count per detector ("unreviewed leads hidden"); no titles, names or ids.
- Never exported: reviewer names, notes, tokens, the review DB, SA ID numbers or their hashes, restricted-register
  person names. A final scan refuses to write if anything ID-like slips through.
- Size budget from config/public-data.yaml (split per file).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from thusa.settings import REPO_ROOT, Paths, load_yaml

SAST = ZoneInfo("Africa/Johannesburg")
SCHEMA = "publicfunds.public-data/v1"
DOC_PREFIX = "https://www.etenders.gov.za/home/Download?blobName="
AUDIT_PREFIX = "http://mfma.treasury.gov.za/Documents/"
STATE_CODE = {"present": "P", "partial": "p", "missing": "m", "n.a.": "-"}
PHASES = {"Main appropriation": "main", "Adjusted appropriation": "adjusted", "Final Appropriation": "final",
          "Audit Outcome": "audited"}
FORBIDDEN_KEYS = {"reviewer", "reviewer_id", "reviewer_name", "username", "notes", "note", "token", "password",
                  "person_id_hmac", "decided_by", "display_name", "session"}
SA_ID = re.compile(r"(?<!\d)(\d{2})(\d{2})(\d{2})\d{7}(?!\d)")


class UnsafeExport(RuntimeError):
    """The export contains something that must never be public. Nothing is written."""


def sast(ts) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(SAST).isoformat(timespec="seconds")


def fy_label(fye: int) -> str:
    return f"{fye - 1}/{str(fye)[-2:]}"


def _rows(con, sql, params=None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def looks_like_sa_id(text: str) -> bool:
    for m in SA_ID.finditer(text):
        mm, dd = int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31 and _luhn(m.group(0)):
            return True
    return False


def scrub(text: str | None) -> str | None:
    """Remove anything shaped like an SA ID number from free text (it is replaced, never published)."""
    if text is None:
        return None
    return SA_ID.sub(lambda m: "[number removed]" if looks_like_sa_id(m.group(0)) else m.group(0), text)


def assert_public_safe(obj, banned_strings: set[str] = frozenset(), path: str = "$") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN_KEYS:
                raise UnsafeExport(f"forbidden key {k!r} at {path}")
            assert_public_safe(v, banned_strings, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_public_safe(v, banned_strings, f"{path}[{i}]")
    elif isinstance(obj, str):
        if looks_like_sa_id(obj):
            raise UnsafeExport(f"SA-ID-like number at {path}")
        if re.fullmatch(r"[0-9a-f]{64}", obj) and not path.endswith(".sha256"):
            raise UnsafeExport(f"64-hex value outside a sha256 field at {path} (possible ID hash)")
        if obj.lower() in banned_strings:
            raise UnsafeExport(f"restricted-register person name at {path}")


class SourceRefs:
    """Raw files referenced by a payload: short key -> {source, url, file, fetched_at_sast}."""

    def __init__(self, con):
        self.all = {r["sha256"]: r for r in _rows(con, "SELECT sha256, source_id, name, url, fetched_at_utc FROM ops.raw_file")}

    def ref(self, sha: str | None, used: dict) -> str | None:
        if not sha:
            return None
        key = sha[:8]
        if key not in used and sha in self.all:
            r = self.all[sha]
            used[key] = {"source_id": r["source_id"], "url": r["url"], "file": r["name"],
                         "fetched_at_sast": sast(r["fetched_at_utc"])}
        return key


# --------------------------------------------------------------------------------------------- payloads
def municipalities(con, refs: SourceRefs) -> dict:
    used: dict = {}
    ents = _rows(con, """SELECT g.gov_body_id, g.demarcation_code AS code, g.name, g.long_name, g.province, g.body_type,
            e.category, e.miif_category, g.valid_from, g.valid_to
        FROM curated.gov_body g LEFT JOIN (SELECT DISTINCT demarcation_code, category, miif_category FROM staging.muni_entity) e
          USING (demarcation_code)
        WHERE g.sphere = 'local' ORDER BY g.province, g.name""")
    years: dict = defaultdict(lambda: defaultdict(dict))
    labels: dict = {}
    for r in _rows(con, "SELECT * FROM curated.muni_total"):
        key = {"ORGB": "budget", "ADJB": "adjusted", "AUDA": "audited"}.get(r["amount_type"])
        if key:
            years[r["gov_body_id"]][r["fye"]][key] = {
                "rev": r["total_revenue_cents"], "exp": r["total_expenditure_cents"],
                "basis": "pub" if r["expenditure_basis"] == "published_subtotal" else "sum",
                "src": refs.ref(r["source_sha256"], used)}
    for r in _rows(con, "SELECT * FROM curated.uifw_line WHERE measure = 'reported'"):
        u = years[r["gov_body_id"]][r["fye"]].setdefault("uifw", {})
        u[r["uifw_type"]] = r["amount_cents"]
        u["src"] = refs.ref(r["source_sha256"], used)
    for r in _rows(con, "SELECT * FROM curated.audit_outcome"):
        labels[r["opinion_code"]] = r["opinion_label"]
        years[r["gov_body_id"]][r["fye"]]["audit"] = {"code": r["opinion_code"],
                                                       "report": _strip(r["report_url"], AUDIT_PREFIX), "src": refs.ref(r["source_sha256"], used)}
    out = []
    for e in ents:
        y = years.get(e["gov_body_id"], {})
        out.append({"id": e["gov_body_id"], "code": e["code"], "name": e["name"], "long_name": e["long_name"],
                    "province": e["province"], "type": e["body_type"], "category": e["category"],
                    "miif_category": e["miif_category"],
                    "exists_from": str(e["valid_from"]) if e["valid_from"] else None,
                    "exists_to": str(e["valid_to"]) if e["valid_to"] else None,
                    "profile": f"https://municipalmoney.gov.za/profiles/municipality-{e['code']}/",
                    "years": {str(fye): d for fye, d in sorted(y.items())}})
    return {"schema": SCHEMA, "kind": "municipalities", "money_unit": "cents (ZAR)", "report_prefix": AUDIT_PREFIX,
            "audit_opinions": labels,
            "about": ["Financial year ends 30 June: fye 2025 = 2024/25.",
                      "budget = original budget (ORGB), adjusted = adjusted budget (ADJB), audited = audited actual (AUDA).",
                      "uifw = unauthorised, irregular, fruitless & wasteful expenditure as reported in the audited AFS notes.",
                      "basis: pub = total as published, sum = summed from published line items (KE-008).",
                      "years are keyed by financial-year end; audit.code labels are in audit_opinions.",
                      "audit.report: AGSA audit report link; prepend report_prefix unless it starts with http.",
                      "null = unknown (not published or not loaded); never read it as zero."],
            "sources": used, "municipalities": out}


def departments(con, refs: SourceRefs) -> dict:
    used: dict = {}
    by: dict = {}
    for r in _rows(con, "SELECT * FROM curated.nat_budget_line ORDER BY department, financial_year"):
        d = by.setdefault(r["gov_body_id"], {"id": r["gov_body_id"], "name": r["department"], "vote": r["vote_number"],
                                             "years": {}})
        y = d["years"].setdefault(str(r["financial_year"]), {"fy": r["fy_label"]})
        y[PHASES.get(r["budget_phase"], r["budget_phase"])] = {
            "amount": r["amount_cents"], "lines": r["n_lines"], "unknown_lines": r["n_unknown_lines"],
            "approx_lines": r["n_approx_lines"], "src": refs.ref(r["source_sha256"], used)}
    return {"schema": SCHEMA, "kind": "departments", "money_unit": "cents (ZAR)",
            "about": ["National government financial year starts 1 April: 2025 = 2025/26.",
                      "main = main appropriation, adjusted = adjusted appropriation, final = final appropriation, "
                      "audited = audit outcome (actual spending).",
                      "unknown_lines: budget lines with no usable value; they are left out of the amount, never zeroed.",
                      "approx_lines: lines published in Excel scientific notation (about 6 significant digits, KE-010)."],
            "sources": used, "departments": list(by.values())}


def coverage(con) -> dict:
    from thusa.report import headline
    cells = _rows(con, "SELECT gov_body_id, fye, data_type, state, reason_code FROM marts.coverage_cell")
    years = sorted({c["fye"] for c in cells})
    types = ["budget", "actual_audited", "uifw", "audit_opinion", "procurement"]
    reasons = sorted({c["reason_code"] for c in cells if c["reason_code"]})
    grid: dict = defaultdict(lambda: {t: ["?"] * len(years) for t in types})
    rgrid: dict = defaultdict(lambda: {t: ["0"] * len(years) for t in types})
    for c in cells:
        i = years.index(c["fye"])
        grid[c["gov_body_id"]][c["data_type"]][i] = STATE_CODE[c["state"]]
        if c["reason_code"]:
            rgrid[c["gov_body_id"]][c["data_type"]][i] = str(reasons.index(c["reason_code"]) + 1)
    h = headline(con)
    h = {k: v for k, v in h.items() if k != "by_year"} | {"by_year": [
        {"fye": r["fye"], "fy": r["fy_label"], "applicable": r["applicable"], "complete": r["complete"],
         "all_core_due": r["all_core_due"]} for r in h["by_year"]]}
    return {"schema": SCHEMA, "kind": "coverage", "years": years, "fy_labels": [fy_label(y) for y in years],
            "data_types": types, "states": {"P": "present", "p": "partial", "m": "missing", "-": "not applicable",
                                            "?": "not computed"},
            "reasons": reasons, "reason_note": "r strings: one digit per year; 0 = none, n = reasons[n-1]",
            "headline": h,
            "entities": [{"id": k, "c": {t: "".join(v[t]) for t in types}, "r": {t: "".join(rgrid[k][t]) for t in types}}
                         for k, v in sorted(grid.items())]}


def tenders(con, refs: SourceRefs, withheld_keys: set[str]) -> tuple[dict, dict[int, dict]]:
    used: dict = {}
    awards = _rows(con, """SELECT a.*, coalesce(al.gov_body_id, a.buyer_gov_body_id) AS gb FROM curated.award a
        LEFT JOIN (SELECT DISTINCT buyer_id, gov_body_id FROM curated.buyer_alias) al USING (buyer_id)
        ORDER BY award_date, ocid, award_id""")
    buyers: dict = {}
    stats: dict = defaultdict(lambda: defaultdict(lambda: {"awards": 0, "valued": 0, "missing": 0, "implausible": 0,
                                                           "value": 0, "by_supplier": defaultdict(int)}))
    per_year: dict[int, list] = defaultdict(list)
    for a in awards:
        b = a["buyer_id"] or a["buyer_name"]
        buyers.setdefault(b, {"id": b, "name": a["buyer_name"], "gov_body_id": a["gb"]})
        yr = a["award_date"].year if a["award_date"] else None
        for key in (str(yr), "all"):
            s = stats[b][key]
            s["awards"] += 1
            if a["value_note"] in ("missing", "zero_placeholder") or a["value_cents"] is None:
                s["missing"] += 1
            elif a["value_note"]:
                s["implausible"] += 1
            else:
                s["valued"] += 1
                s["value"] += a["value_cents"]
                s["by_supplier"][a["supplier_key"] or "?"] += a["value_cents"]
        supplier = a["supplier_name"]
        if a["supplier_person_key"] in withheld_keys or a["supplier_key"] in withheld_keys:
            supplier = "(name withheld)"
        doc = _compact_doc(a["doc_url"])
        per_year[yr or 0].append([a["ocid"], a["award_id"], a["award_date"].isoformat() if a["award_date"] else None,
                                  "signed" if a["award_date_basis"] == "contract.dateSigned" else "release",
                                  b, scrub(supplier), a["value_cents"] if not a["value_note"] else None, a["value_note"],
                                  scrub(a["tender_title"]), a["procurement_method"], a["main_category"] or None,
                                  scrub(doc), refs.ref(a["source_sha256"], used)])

    def conc(s):
        tot = s["value"]
        shares = [v / tot for v in s["by_supplier"].values()] if tot > 0 else []
        return {"awards": s["awards"], "valued": s["valued"], "missing_value": s["missing"],
                "implausible_value": s["implausible"], "missing_share": round(s["missing"] / s["awards"], 4),
                "known_value": s["value"] if s["valued"] else None, "suppliers": len(s["by_supplier"]),
                "top_supplier_share": round(max(shares), 4) if shares else None,
                "hhi": round(sum((x * 100) ** 2 for x in shares)) if shares else None}
    by_buyer = [{**buyers[b], "years": {k: conc(v) for k, v in sorted(st.items())}} for b, st in stats.items()]
    by_buyer.sort(key=lambda x: -x["years"]["all"]["awards"])
    nat: dict = defaultdict(lambda: {"awards": 0, "valued": 0, "missing": 0, "implausible": 0, "value": 0,
                                     "by_supplier": defaultdict(int)})
    for st in stats.values():
        for k, v in st.items():
            n = nat[k]
            for f in ("awards", "valued", "missing", "implausible", "value"):
                n[f] += v[f]
            for sk, sv in v["by_supplier"].items():
                n["by_supplier"][sk] += sv
    summary = {"schema": SCHEMA, "kind": "tenders_summary", "money_unit": "cents (ZAR)",
               "about": ["Tender awards published by National Treasury's eTenders portal (OCDS). Year = calendar year of the "
                         "contract signature date, or of the release date when no signature date is published.",
                         "known_value sums only awards with a plausible value; missing_value counts no value or a R0 "
                         "placeholder; implausible_value counts values below R100 or above R20bn (KE-007). Values are as published "
                         "and can be multi-year, framework or estimated contract values, so totals are not annual spending.",
                         "top_supplier_share and hhi (Herfindahl index, 0-10,000) describe how concentrated the known "
                         "award value is across suppliers; suppliers are not named here.",
                         "Award records (awards-YYYY.json) are public records as published; they are not flags or findings."],
               "award_files": {str(y): f"awards-{y if y else 'undated'}.json" for y in sorted(per_year)},
               "all_years": {k: conc(v) for k, v in sorted(nat.items())},
               "buyers": by_buyer}
    files = {}
    for y, rows in per_year.items():
        files[y] = {"schema": SCHEMA, "kind": "awards", "year": y or None, "money_unit": "cents (ZAR)",
                    "doc_prefix": DOC_PREFIX,
                    "columns": ["ocid", "award_id", "date", "date_basis", "buyer", "supplier", "value", "value_note",
                                "reference", "method", "category", "doc", "src"],
                    "about": ["doc: tender document. 'blob|file name' means doc_prefix + blob + '&downloadedFileName=' + "
                              "encodeURIComponent(file name); a value starting with http is a full link.",
                              "value null = unknown (see value_note)."],
                    "sources": {}, "rows": rows}
    for y, f in files.items():
        keys = {r[-1] for r in f["rows"]}
        f["sources"] = {k: used[k] for k in keys if k}
    summary["sources"] = used
    return summary, files


def flags(paths: Paths, con) -> dict:
    from thusa.publish import public_flags
    from thusa.review.service import Service
    confirmed, _leads, policy = public_flags(paths)
    hidden: dict = defaultdict(lambda: {"hidden": 0, "names_a_supplier": 0, "awaiting_second_review": 0})
    from thusa.settings import publication_config
    never = set(publication_config()["flags"].get("never_publish", []))
    for f in Service(paths).list_flags():
        if f["publishable"] and f["detector_id"] not in never:
            continue
        h = hidden[f["detector_id"]]
        h["hidden"] += 1
        h["names_a_supplier"] += 1 if f["names_supplier"] else 0
        h["awaiting_second_review"] += 1 if f["status"] == "awaiting second review" else 0
    det = load_yaml("public-data.yaml")["detectors"]
    safe = [{k: f[k] for k in ("flag_id", "detector_id", "detector_version", "severity", "title", "explanation",
                               "gov_body_id", "body_name", "period_label", "confirmed_at_sast", "review_reason",
                               "evidence_urls")} for f in confirmed]
    for f in safe:
        f["explanation"], f["review_reason"], f["title"] = scrub(f["explanation"]), scrub(f["review_reason"]), scrub(f["title"])
    return {"schema": SCHEMA, "kind": "flags",
            "policy": {"published": "review-confirmed flags only, on unchanged evidence",
                       "four_eyes": "a flag that names a supplier needs two different reviewers to confirm it",
                       "unconfirmed": "never exported; counted below",
                       "publication_yaml": policy},
            "disclaimer": "Flags are automated indicators that a pattern in official data deserves a closer look. A "
                          "confirmed flag means reviewers checked that the data pattern is real - not that anyone "
                          "acted unlawfully.",
            "detectors": det,
            "confirmed": safe,
            "hidden_leads": {"total": sum(v["hidden"] for v in hidden.values()),
                             "by_detector": {k: hidden[k] for k in sorted(hidden)}}}


IMF_BACK_SERIES_NOTE = ("Values from 2025-01 match Stats SA P0141. Earlier values are the IMF's linked back-series "
                        "(OECD 2015-base series scaled) and can differ from Stats SA's rebased figures by about "
                        "0.1-0.2 index points.")


def prices(con, refs: SourceRefs) -> dict:
    used: dict = {}
    from thusa.parsers import FUEL_GRADES
    fuel = _rows(con, "SELECT * FROM curated.fuel_price ORDER BY year, month, grade")
    cpi = _rows(con, "SELECT * FROM curated.cpi ORDER BY year, month")
    imf = bool(cpi) and cpi[0]["source_id"] == "imf_cpi"
    return {"schema": SCHEMA, "kind": "prices",
            "fuel": {"unit": "South African cents per litre", "period": "month of the official price adjustment "
                     "(prices change on the first Wednesday of the month)",
                     "grades": [{"id": g, "label": lbl} for g, lbl in FUEL_GRADES],
                     "about": ["Petrol prices are regulated pump prices (inland = Gauteng, coast = coastal zones).",
                               "DMPR's history table heads the 93 inland column 'Leaded Replacement Petrol'. The "
                               "October 2026 DMPR price breakdown gives one inland price for '93 ULP & LRP', equal to "
                               "this column; whether the two grades shared a price in every earlier month is unknown.",
                               "The same 'Leaded Replacement Petrol' heading also covers the 95 coast column. The "
                               "October 2026 breakdown gives one coastal price for '95 ULP & LRP', equal to this "
                               "column; whether the two grades shared a price in every earlier month is unknown.",
                               "The 95 inland column sits under DMPR's 'Unleaded' heading (Unleaded Petrol, ULP).",
                               "Diesel and illuminating paraffin are not regulated at the pump, so retail prices can "
                               "differ from these official figures.",
                               "Only months published in the loaded DMPR history table are included (KE-012)."],
                     "columns": ["year", "month", "grade", "cents_per_litre", "src"],
                     "rows": [[r["year"], r["month"], r["grade"], float(r["cents_per_litre"]),
                               refs.ref(r["source_sha256"], used)] for r in fuel],
                     "last_period": f"{fuel[-1]['year']}-{fuel[-1]['month']:02d}" if fuel else None},
            "cpi": {"measure": ("Headline consumer price index, all items, all urban areas (Stats SA)" if imf else
                                "Headline consumer price index, all items, South Africa"),
                    "base": f"{cpi[0]['base_period']} = 100" if cpi and cpi[0]["base_period"] else None,
                    "publisher": ("Stats SA headline CPI (all urban areas), as republished by the IMF. Source: International "
                                  "Monetary Fund, Consumer Price Index (CPI), https://data.imf.org/en/datasets/IMF.STA:CPI "
                                  "(Stats SA blocks automated downloads, KE-003)" if imf else
                                  "Statistics South Africa (as republished by the OECD; Stats SA blocks automated "
                                  "downloads, KE-003)"),
                    "columns": ["period", "index", "src"],
                    "rows": [[f"{r['year']}-{r['month']:02d}", r["index_value"], refs.ref(r["source_sha256"], used)]
                             for r in cpi],
                    "last_period": f"{cpi[-1]['year']}-{cpi[-1]['month']:02d}" if cpi else None,
                    **({"back_series_note": IMF_BACK_SERIES_NOTE} if imf else {})},
            "sources": used}


def _strip(url: str | None, prefix: str) -> str | None:
    return url[len(prefix):] if url and url.startswith(prefix) else url


def _compact_doc(url: str | None) -> str | None:
    from urllib.parse import parse_qs, urlsplit
    if not url or not url.startswith(DOC_PREFIX):
        return url
    q = parse_qs(urlsplit(url).query)
    blob, fname = q.get("blobName", [None])[0], q.get("downloadedFileName", [None])[0]
    if not blob or "|" in blob or (fname and "|" in fname):
        return url
    return f"{blob}|{fname}" if fname else blob


def _known_errors() -> list[dict]:
    p = REPO_ROOT / "itil" / "knowledge" / "known-errors.md"
    out = []
    for line in p.read_text(encoding="utf-8").splitlines() if p.exists() else []:
        m = re.match(r"\|\s*(KE-\d+)\s*\|\s*([^|]+)\|", line)
        if m:
            txt = re.sub(r"[`*]", "", m.group(2)).strip()
            out.append({"id": m.group(1), "symptom": txt[:280] + ("…" if len(txt) > 280 else "")})
    return out


def manifest(con, cfg: dict, files: dict[str, bytes], counts: dict, cov_headline: dict) -> dict:
    srcs = {s["id"]: s for s in load_yaml("sources.yaml")["sources"]}
    runs = {r["source_id"]: r for r in _rows(con, """SELECT * FROM ops.ingest_run
        QUALIFY row_number() OVER (PARTITION BY source_id ORDER BY ended_at_utc DESC) = 1""")}
    fetched = {r["source_id"]: r for r in _rows(con, """SELECT source_id, max(fetched_at_utc) AS last_new_bytes,
        max(checked_at_utc) AS last_checked, count(*) AS files FROM ops.raw_file GROUP BY ALL""")}
    build = json.loads(con.execute("SELECT summary FROM ops.build").fetchone()[0])
    sources = []
    for sid in sorted(set(runs) | set(fetched) | {k for k, v in srcs.items() if v.get("mvp")}):
        s, r, f = srcs.get(sid, {}), runs.get(sid, {}), fetched.get(sid, {})
        disp = cfg.get("display_sources", {}).get(sid, {})
        errs = json.loads(r["errors"]) if r.get("errors") else []
        sources.append({"id": sid, "name": s.get("name"), "publisher": s.get("owner_org"),
                        "page": disp.get("page") or s.get("url"), "licence": disp.get("licence") or s.get("licence"),
                        "last_run_status": r.get("status"), "last_run_sast": sast(r.get("ended_at_utc")),
                        "last_new_data_sast": sast(f.get("last_new_bytes")),
                        "last_checked_sast": sast(f.get("last_checked")), "raw_files": f.get("files", 0),
                        "freshness_slo_days": s.get("freshness_slo_days"),
                        "problem": "; ".join(e[:200] for e in errs) or (None if r or f else
                                   (s.get("notes") or "not loaded yet"))})
    now = datetime.now(SAST)
    return {"schema": SCHEMA, "schema_version": cfg["schema_version"], "kind": "manifest",
            "generated_at_sast": now.isoformat(timespec="seconds"),
            "build": {"id": build["build_id"], "as_of": build["as_of"], "code_commit": build.get("git_commit"),
                      "data_quality": {"pass": build["dq"]["pass"], "warn": build["dq"]["warn"],
                                       "fail": len(build["dq"]["fail"])}},
            "base_url": cfg["base_url"],
            "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in sorted(files.items())],
            "counts": counts, "coverage": cov_headline,
            "sources": sources,
            "known_gaps": cfg.get("known_gaps", []),
            "known_errors": _known_errors(),
            "population": cfg.get("population"),
            "disclaimers": [
                "This site shows official public data as published, with its gaps. Blank means unknown, not zero.",
                "Flags are automated indicators checked by people, not findings of wrongdoing. Only flags confirmed by "
                "review are shown; other leads stay hidden while they are checked.",
                "Tender award records are public records published by National Treasury, shown as published."],
            "freshness_slo": "Public data is refreshed after each successful daily pipeline run; target: no older than "
                             "48 hours (itil/sla-slo.md, SLO-PD-1)."}


def export(paths: Paths, out_dir: Path | None = None) -> dict:
    cfg = load_yaml("public-data.yaml")
    out_dir = Path(out_dir or REPO_ROOT / "public-data" / "v1")
    if not paths.warehouse.exists():
        raise UnsafeExport(f"no warehouse at {paths.warehouse}; run `thusa run` first")
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    try:
        dq_fail = json.loads(con.execute("SELECT summary FROM ops.build").fetchone()[0])["dq"]["fail"]
        if dq_fail:
            raise UnsafeExport(f"quality gate: the current build failed {len(dq_fail)} data-quality check(s)")
        refs = SourceRefs(con)
        withheld = {r[0] for r in con.execute("SELECT name_key FROM curated.restriction WHERE is_person AND name_key IS NOT NULL").fetchall()}
        banned = {r[0].lower() for r in con.execute("SELECT name FROM curated.restriction WHERE is_person AND name IS NOT NULL").fetchall()}
        mun, dep, cov = municipalities(con, refs), departments(con, refs), coverage(con)
        tsum, award_files = tenders(con, refs, withheld)
        fl, pr = flags(paths, con), prices(con, refs)
        payloads = {"municipalities.json": mun, "departments.json": dep, "coverage.json": cov,
                    "tenders-summary.json": tsum, "flags.json": fl, "prices.json": pr}
        for y, f in award_files.items():
            payloads[f"awards-{y if y else 'undated'}.json"] = f
        for name, obj in payloads.items():
            assert_public_safe(obj, banned, name)
        blobs = {n: json.dumps(o, ensure_ascii=False, separators=(",", ":"), default=str).encode() for n, o in payloads.items()}
        counts = {"municipalities": len(mun["municipalities"]), "departments": len(dep["departments"]),
                  "awards": sum(len(f["rows"]) for f in award_files.values()), "buyers": len(tsum["buyers"]),
                  "fuel_rows": len(pr["fuel"]["rows"]), "cpi_months": len(pr["cpi"]["rows"]),
                  "flags_confirmed": len(fl["confirmed"]), "leads_hidden": fl["hidden_leads"]["total"]}
        man = manifest(con, cfg, blobs, counts, cov["headline"])
        assert_public_safe(man, banned, "manifest.json")
    finally:
        con.close()
    out_dir = Path(out_dir)
    ch = changelog(out_dir, blobs, man, cfg)
    feed = json_feed(ch, cfg)
    for name, obj in (("changes.json", ch), ("feed.json", feed)):
        assert_public_safe(obj, banned, name)
        blobs[name] = json.dumps(obj, ensure_ascii=False, indent=1, default=str).encode()
        man["files"].append({"name": name, "bytes": len(blobs[name]), "sha256": hashlib.sha256(blobs[name]).hexdigest()})
    man["files"].sort(key=lambda f: f["name"])
    blobs["manifest.json"] = json.dumps(man, ensure_ascii=False, indent=1, default=str).encode()
    total = sum(len(b) for b in blobs.values())
    big = [n for n, b in blobs.items() if len(b) > cfg["file_budget_bytes"]]
    if total > cfg["size_budget_bytes"] or big:
        raise UnsafeExport(f"size budget exceeded: total {total} bytes, oversized files {big}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        if old.name not in blobs:
            old.unlink()
    for n, b in blobs.items():                    # manifest last, so a reader never sees a manifest for missing files
        if n == "manifest.json":
            continue
        _atomic_write(out_dir / n, b)
    _atomic_write(out_dir / "manifest.json", blobs["manifest.json"])
    return {"out": str(out_dir), "files": {n: len(b) for n, b in sorted(blobs.items())}, "total_bytes": total,
            "counts": counts}


META_FILES = {"manifest.json", "changes.json", "feed.json"}
CHANGES_KEEP = 100
COUNT_LABELS = {"municipalities": "municipalities", "departments": "national departments", "awards": "tender award records",
                "buyers": "buyers with awards", "fuel_rows": "fuel price rows", "cpi_months": "CPI months",
                "flags_confirmed": "confirmed flags", "leads_hidden": "hidden leads awaiting review"}


def _data_hash(shas: dict[str, str]) -> str:
    h = hashlib.sha256()
    for n in sorted(shas):
        h.update(f"{n}:{shas[n]}\n".encode())
    return h.hexdigest()[:16]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def changelog(out_dir: Path, blobs: dict[str, bytes], man: dict, cfg: dict) -> dict:
    """'What's new' log: one entry per export whose data differs from the previous one (CHG-2026-008).
    Re-exporting unchanged data leaves the file byte-identical, so the nightly publish makes no commit."""
    shas = {n: hashlib.sha256(b).hexdigest() for n, b in blobs.items() if n not in META_FILES}
    dh = _data_hash(shas)
    prev = _read_json(out_dir / "changes.json") or {}
    entries = list(prev.get("entries") or [])
    if entries and entries[0].get("data_hash") == dh:
        return {**_changes_head(cfg), "entries": entries}
    pm = _read_json(out_dir / "manifest.json") or {}
    old_shas = {f["name"]: f["sha256"] for f in pm.get("files", []) if f["name"] not in META_FILES}
    old_counts, new_counts = pm.get("counts") or {}, man["counts"]
    deltas = {k: v - old_counts[k] for k, v in new_counts.items()
              if isinstance(v, int) and isinstance(old_counts.get(k), int) and v != old_counts[k]}
    cov_old, cov_new = (pm.get("coverage") or {}).get("complete_pct"), man["coverage"].get("complete_pct")
    lines = []
    if not pm:
        lines.append("First public release of this data.")
    elif not entries:
        lines.append("Change log started with this build.")
    for k, d in deltas.items():
        lines.append(f"{'+' if d > 0 else '-'}{abs(d):,} {COUNT_LABELS.get(k, k)} (now {new_counts[k]:,}).".replace(",", " "))
    if cov_old is not None and cov_new is not None and cov_old != cov_new:
        lines.append(f"Coverage of core municipal data {'rose' if cov_new > cov_old else 'fell'} from {cov_old}% to {cov_new}%.")
    changed = sorted(n for n in shas if n in old_shas and shas[n] != old_shas[n])
    added, removed = sorted(set(shas) - set(old_shas)), sorted(set(old_shas) - set(shas))
    if pm and len(lines) <= (0 if entries else 1):
        if changed or added:
            lines.append("Figures updated or corrected in: " + ", ".join(changed + added) + ".")
        elif entries:
            lines.append("Data files re-published.")
    entry = {"build_id": man["build"]["id"], "published_sast": man["generated_at_sast"], "data_hash": dh,
             "summary": lines, "count_changes": deltas, "counts": new_counts,
             "coverage_pct": cov_new, "coverage_pct_before": cov_old,
             "files_changed": changed, "files_added": added if pm else [], "files_removed": removed,
             "data_quality": man["build"]["data_quality"]}
    return {**_changes_head(cfg), "entries": ([entry] + entries)[:CHANGES_KEEP]}


def _changes_head(cfg: dict) -> dict:
    return {"schema": SCHEMA, "kind": "changes",
            "about": "One entry per published build whose data changed, newest first. count_changes compare with the "
                     "previous published build; counts are totals in that build. Re-publishing identical data adds no entry."}


def json_feed(ch: dict, cfg: dict) -> dict:
    """JSON Feed 1.1 (https://jsonfeed.org/version/1.1) of new public data, derived only from changes.json."""
    site = cfg.get("site_url", "").rstrip("/") + "/"
    items = []
    for e in ch["entries"][:30]:
        items.append({"id": f"{e['build_id']}-{e['data_hash']}", "url": f"{site}#/changes",
                      "title": f"New public data: build {e['build_id']}",
                      "content_text": " ".join(e["summary"]), "date_published": e["published_sast"]})
    return {"version": "https://jsonfeed.org/version/1.1", "title": "PublicFunds SA: new public data",
            "home_page_url": site, "feed_url": cfg["base_url"] + "feed.json",
            "description": "A new item each time the published South African public-spending data changes.",
            "language": "en-ZA", "items": items}


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)
