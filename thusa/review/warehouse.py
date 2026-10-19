"""Read-only access to the DuckDB build for the review app. Parameterised SQL only; NULL stays NULL (never 0).

A fresh read-only connection is opened per call, so an atomic warehouse swap by `thusa build` is picked up on
the next request without restarting the app.
"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path

import duckdb

FLAG_ID_RE = re.compile(r"^[0-9a-f]{16}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GOV_BODY_RE = re.compile(r"^(MUN|NAT|BUYER):[A-Za-z0-9_.:-]{1,80}$")
FY_RE = re.compile(r"^(\d{4})/(\d{2})$")
DATA_TYPES = ["budget", "actual_audited", "uifw", "audit_opinion", "procurement"]
TYPE_LABEL = {"core": "Core (all four)", "budget": "Budget (orig. + adj.)", "actual_audited": "Audited actuals",
              "uifw": "UIF&W expenditure", "audit_opinion": "Audit opinion", "procurement": "eTenders awards"}
SEVERITIES = ["high", "med", "low", "info"]
SEV_ORDER = {s: i for i, s in enumerate(SEVERITIES)}


class WarehouseMissing(RuntimeError):
    pass


def rand(cents) -> str:
    if cents is None:
        return "unknown"
    v = cents / 100
    for div, suf in ((1e9, "bn"), (1e6, "m")):
        if abs(v) >= div:
            return f"R{v / div:,.2f}{suf}"
    return f"R{v:,.0f}"


def fy_to_fye(label: str | None) -> int | None:
    m = FY_RE.match(label or "")
    return int(m.group(1)) + 1 if m else None


class Warehouse:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        if not self.path.exists():
            raise WarehouseMissing(f"warehouse not built: {self.path}")
        con = duckdb.connect(str(self.path), read_only=True)
        try:
            yield con
        finally:
            con.close()

    def rows(self, sql: str, params: list | None = None) -> list[dict]:
        with self.connect() as con:
            cur = con.execute(sql, params or [])
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def build_id(self) -> str | None:
        try:
            r = self.rows("SELECT build_id FROM ops.build ORDER BY build_id DESC LIMIT 1")
        except (WarehouseMissing, duckdb.Error):
            return None
        return r[0]["build_id"] if r else None

    # ------------------------------------------------------------------ flags
    def flags(self) -> list[dict]:
        out = self.rows("""SELECT f.*, coalesce(g.name, f.subject_name) AS body_name, g.province
                           FROM marts.flag f LEFT JOIN curated.gov_body g ON g.gov_body_id = f.gov_body_id""")
        for f in out:
            f["evidence"] = json.loads(f["evidence_json"])
        return out

    def flag(self, flag_id: str) -> dict | None:
        if not FLAG_ID_RE.match(flag_id or ""):
            return None
        r = self.rows("""SELECT f.*, coalesce(g.name, f.subject_name) AS body_name, g.province, g.demarcation_code
                         FROM marts.flag f LEFT JOIN curated.gov_body g ON g.gov_body_id = f.gov_body_id
                         WHERE f.flag_id = ?""", [flag_id])
        if not r:
            return None
        f = r[0]
        f["evidence"] = json.loads(f["evidence_json"])
        return f

    def raw_files(self, shas: list[str]) -> dict[str, dict]:
        shas = [s for s in shas if s and SHA_RE.match(s)]
        if not shas:
            return {}
        return {r["sha256"]: r for r in self.rows("SELECT * FROM ops.raw_file WHERE list_contains(?, sha256)", [shas])}

    def matched_records(self, f: dict) -> dict:
        """The records a reviewer needs to judge the flag, per detector."""
        det, gb, out = f["detector_id"], f["gov_body_id"], {"tables": []}
        fye = fy_to_fye(f["period_label"])
        if det.startswith("D3"):
            ocids = [e["ocid"] for e in f["evidence"] if e.get("ocid")]
            r = self.rows("""SELECT subject_id, is_person,
                                    CASE WHEN is_person THEN 'Natural person (name withheld, POPIA)' ELSE name END AS name,
                                    name_key, cipc_reg_no, restriction_type, reason, period_from, period_to,
                                    authorised_by, source_url, source_locator, source_sha256, fetched_at_utc
                             FROM curated.restriction WHERE subject_id = ?""", [f["subject_id"]])
            keys = [x["name_key"] for x in r]
            aw = self.rows("""SELECT ocid, award_id, buyer_name, supplier_name, supplier_id, value_cents, value_note,
                                     award_date, award_date_basis, tender_title, procurement_method, doc_url,
                                     source_locator, source_sha256, fetched_at_utc
                              FROM curated.award WHERE list_contains(?, ocid)
                                AND (list_contains(?, supplier_key) OR list_contains(?, supplier_person_key))""",
                           [ocids, keys, keys])
            person = any(x["is_person"] for x in r)
            for x in r:
                x.pop("name_key", None)
                if x["is_person"]:
                    x["cipc_reg_no"] = None
            if person:
                for a in aw:
                    a["supplier_name"], a["supplier_id"] = "Natural person (name withheld, POPIA)", None
            out["tables"] = [("Award(s) on eTenders", aw), ("Restricted Supplier register entry", r)]
            out["match"] = {"confidence": f["score"], "basis": "exact normalised-name match only "
                            "(eTenders publishes no registration numbers)",
                            "award_supplier": aw[0]["supplier_name"] if aw else None,
                            "register_name": r[0]["name"] if r else None}
        elif det.startswith(("D4", "D5")):
            where = "buyer_gov_body_id = ?" if not gb.startswith("BUYER:") else "buyer_id = ?"
            key = gb if not gb.startswith("BUYER:") else gb.split(":", 1)[1]
            if det.startswith("D4"):
                t = self.rows(f"""SELECT supplier_name, count(*) AS awards, sum(value_cents) AS value_cents,
                                         min(award_date) AS first_award, max(award_date) AS last_award
                                  FROM curated.award WHERE {where} AND n_suppliers = 1 AND value_cents IS NOT NULL
                                    AND value_note IS NULL
                                    AND award_date >= (SELECT max(award_date) FROM curated.award) - INTERVAL 3 YEAR
                                  GROUP BY 1 ORDER BY value_cents DESC LIMIT 15""", [key])
                tot = sum(x["value_cents"] for x in t) or None
                for x in t:
                    x["share_of_top15"] = f"{x['value_cents'] / tot:.1%}" if tot else None
                out["tables"] = [("Largest suppliers (single-supplier awards with a usable value, last 3 years)", t)]
            else:
                t = self.rows(f"""SELECT coalesce(value_note, CASE WHEN value_cents IS NULL THEN 'unknown (no value or 0)'
                                         ELSE 'usable' END) AS value_class, count(DISTINCT ocid || award_id) AS awards
                                  FROM curated.award WHERE {where} GROUP BY 1 ORDER BY 2 DESC""", [key])
                out["tables"] = [("Award values by class", t)]
            out["tables"].append(("Sample awards", self.rows(
                f"""SELECT ocid, award_id, supplier_name, value_cents, value_note, award_date, tender_title,
                           source_locator, source_sha256 FROM curated.award WHERE {where}
                    ORDER BY award_date DESC LIMIT 10""", [key])))
        elif det.startswith("D1") and gb.startswith("MUN:"):
            out["tables"] = [("Totals (municipal, all amount types)", self.rows(
                """SELECT fy_label, amount_type, total_expenditure_cents, expenditure_basis, total_revenue_cents,
                          revenue_basis, source_locator, source_sha256, fetched_at_utc FROM curated.muni_total
                   WHERE gov_body_id = ? AND fye = ? ORDER BY amount_type""", [gb, fye]))]
        elif det.startswith("D1"):
            out["tables"] = [("National budget vs actual", self.rows(
                """SELECT fy_label, budget_phase, amount_cents, n_lines, n_unknown_lines, n_approx_lines,
                          source_locator, source_sha256 FROM curated.nat_budget_line
                   WHERE gov_body_id = ? AND fy_label = ? ORDER BY budget_phase""", [gb, f["period_label"]]))]
        elif det.startswith("D8"):
            out["tables"] = [("UIF&W history", self.rows(
                """SELECT fy_label, uifw_type, measure, amount_cents, source_locator, source_sha256, fetched_at_utc
                   FROM curated.uifw_line WHERE gov_body_id = ? ORDER BY fye, uifw_type""", [gb])),
                ("Audit outcomes", self.rows(
                    """SELECT fy_label, opinion_label, report_url, source_sha256 FROM curated.audit_outcome
                       WHERE gov_body_id = ? ORDER BY fye""", [gb]))]
        return out

    # ------------------------------------------------------------------ coverage
    def provinces(self) -> list[str]:
        return [r["province"] for r in self.rows(
            "SELECT DISTINCT province FROM marts.coverage_cell WHERE province IS NOT NULL ORDER BY 1")]

    def years(self) -> list[dict]:
        return self.rows("SELECT DISTINCT fye, fy_label FROM marts.coverage_cell ORDER BY fye")

    def coverage(self, data_type: str, province: str | None, q: str | None, fye_from: int | None,
                 fye_to: int | None) -> tuple[list[dict], list[dict]]:
        params: list = []
        where = ["1=1"]
        if province:
            where.append("province = ?"), params.append(province)
        if q:
            where.append("(name ILIKE ? OR gov_body_id ILIKE ?)"), params.extend([f"%{q}%", f"%{q}%"])
        if fye_from:
            where.append("fye >= ?"), params.append(fye_from)
        if fye_to:
            where.append("fye <= ?"), params.append(fye_to)
        w = " AND ".join(where)
        if data_type == "core":
            cells = self.rows(f"""SELECT gov_body_id, name, body_type, province, fye, fy_label,
                                         CASE core_state WHEN 'complete' THEN 'present' ELSE core_state END AS state,
                                         core_present || '/' || core_applicable || ' core types present' AS reason_code
                                  FROM marts.coverage_entity_year WHERE {w}
                                    AND gov_body_id IN (SELECT gov_body_id FROM marts.coverage_entity_year
                                                        GROUP BY 1 HAVING bool_or(core_state <> 'n.a.'))
                                  ORDER BY province, name, fye""", params)
        else:
            cells = self.rows(f"""SELECT gov_body_id, name, body_type, province, fye, fy_label, state, reason_code
                                  FROM marts.coverage_cell WHERE data_type = ? AND {w}
                                    AND gov_body_id IN (SELECT gov_body_id FROM marts.coverage_entity_year
                                                        GROUP BY 1 HAVING bool_or(core_state <> 'n.a.'))
                                  ORDER BY province, name, fye""", [data_type, *params])
        years = sorted({(c["fye"], c["fy_label"]) for c in cells})
        ents: dict[str, dict] = {}
        for c in cells:
            e = ents.setdefault(c["gov_body_id"], {"gov_body_id": c["gov_body_id"], "name": c["name"],
                                                   "province": c["province"], "body_type": c["body_type"],
                                                   "cells": {}})
            e["cells"][c["fye"]] = c
        return [{"fye": y, "fy_label": lbl} for y, lbl in years], list(ents.values())

    def coverage_summary(self, data_type: str, ents: list[dict]) -> dict:
        counts = {"present": 0, "partial": 0, "missing": 0, "n.a.": 0}
        for e in ents:
            for c in e["cells"].values():
                counts[c["state"]] = counts.get(c["state"], 0) + 1
        app = counts["present"] + counts["partial"] + counts["missing"]
        counts["present_pct"] = round(100 * counts["present"] / app, 1) if app else None
        return counts

    # ------------------------------------------------------------------ entity drill-down
    def entity(self, gov_body_id: str) -> dict | None:
        if not GOV_BODY_RE.match(gov_body_id or ""):
            return None
        if gov_body_id.startswith("BUYER:"):
            bid = gov_body_id.split(":", 1)[1]
            b = self.rows("SELECT any_value(buyer_name) AS name FROM curated.award WHERE buyer_id = ?", [bid])
            if not b or b[0]["name"] is None:
                return None
            return {"gov_body_id": gov_body_id, "name": b[0]["name"], "sphere": "buyer (unmatched eTenders buyer)",
                    "body_type": None, "province": None, "sections": [
                        ("Awards (latest 50)", self.rows(
                            """SELECT ocid, award_id, supplier_name, value_cents, value_note, award_date, tender_title,
                                      source_locator, source_sha256, fetched_at_utc FROM curated.award
                               WHERE buyer_id = ? ORDER BY award_date DESC LIMIT 50""", [bid]))]}
        g = self.rows("SELECT * FROM curated.gov_body WHERE gov_body_id = ?", [gov_body_id])
        if not g:
            return None
        e = g[0]
        if gov_body_id.startswith("MUN:"):
            e["sections"] = [
                ("Coverage by data type and year", self.rows(
                    """SELECT fy_label, data_type, state, reason_code, expected_n, present_n FROM marts.coverage_cell
                       WHERE gov_body_id = ? ORDER BY fye, data_type""", [gov_body_id])),
                ("Income and expenditure totals", self.rows(
                    """SELECT fy_label, amount_type, total_revenue_cents, revenue_basis, total_expenditure_cents,
                              expenditure_basis, source_locator, source_sha256, fetched_at_utc FROM curated.muni_total
                       WHERE gov_body_id = ? ORDER BY fye, amount_type""", [gov_body_id])),
                ("Unauthorised, irregular, fruitless & wasteful expenditure", self.rows(
                    """SELECT fy_label, uifw_type, measure, amount_cents, source_locator, source_sha256, fetched_at_utc
                       FROM curated.uifw_line WHERE gov_body_id = ? ORDER BY fye, uifw_type""", [gov_body_id])),
                ("Audit outcomes", self.rows(
                    """SELECT fy_label, opinion_label, report_url, source_locator, source_sha256 FROM curated.audit_outcome
                       WHERE gov_body_id = ? ORDER BY fye""", [gov_body_id])),
                ("eTenders awards (largest 25 with a usable value, then unknown)", self.rows(
                    """SELECT ocid, award_id, supplier_name, value_cents, value_note, award_date, tender_title,
                              source_locator, source_sha256, fetched_at_utc FROM curated.award
                       WHERE buyer_gov_body_id = ? ORDER BY value_cents DESC NULLS LAST LIMIT 25""", [gov_body_id])),
            ]
        else:
            e["sections"] = [("Budget vs actual (national)", self.rows(
                """SELECT fy_label, budget_phase, amount_cents, n_lines, n_unknown_lines, n_approx_lines,
                          source_locator, source_sha256, fetched_at_utc FROM curated.nat_budget_line
                   WHERE gov_body_id = ? ORDER BY financial_year, budget_phase""", [gov_body_id]))]
        return e

    def lineage(self, sha: str) -> dict | None:
        if not SHA_RE.match(sha or ""):
            return None
        r = self.rows("SELECT * FROM ops.raw_file WHERE sha256 = ?", [sha])
        return r[0] if r else None
