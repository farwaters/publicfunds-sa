"""Raw -> staging. Python parsers emit typed rows; DuckDB ingests them via JSONL (fast, typed, reproducible).

Every staging row carries raw_file_id (= sha256 of the raw file) and source_locator, so curated rows can be
traced back to the exact bytes they came from (ADR-0004).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pdfplumber

from thusa import parsers
from thusa.normalise import muni_key
from thusa.raw import RawFile, RawStore

MUNI_API = "https://municipaldata.treasury.gov.za/api/cubes"


def _default(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(type(o))


def write_table(con: duckdb.DuckDBPyConnection, staging_dir: Path, table: str, rows, columns: dict[str, str]) -> int:
    staging_dir.mkdir(parents=True, exist_ok=True)
    path = staging_dir / f"{table.replace('.', '__')}.jsonl"
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({k: r.get(k) for k in columns}, default=_default) + "\n")
            n += 1
    cols = ", ".join(f"'{k}': '{v}'" for k, v in columns.items())
    if n:
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_json('{path}', format='newline_delimited', "
                    f"columns={{{cols}}})")
    else:
        con.execute(f"CREATE OR REPLACE TABLE {table} ({', '.join(f'{k} {v}' for k, v in columns.items())})")
    return n


def load_raw_files(con, store: RawStore) -> int:
    """ops.raw_file: one row per distinct stored file (latest manifest view)."""
    rows = {}
    for e in store.entries():
        rows[(e.source_id, e.name)] = e
    con.execute("""CREATE OR REPLACE TABLE ops.raw_file (raw_file_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL,
        name VARCHAR NOT NULL, path VARCHAR NOT NULL, url VARCHAR, sha256 VARCHAR NOT NULL, bytes BIGINT,
        fetched_at_utc TIMESTAMPTZ NOT NULL, checked_at_utc TIMESTAMPTZ, http_status INTEGER)""")
    seen = set()
    for e in rows.values():
        if e.sha256 in seen:
            continue
        seen.add(e.sha256)
        con.execute("INSERT INTO ops.raw_file VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [e.sha256, e.source_id, e.name, "data/raw/" + e.path, e.url, e.sha256, e.bytes,
                     e.fetched_at_utc, e.checked_at_utc, e.http_status])
    return len(seen)


def _files(store: RawStore, source_id: str, prefix: str = "") -> list[RawFile]:
    return sorted((f for f in store.latest_files(source_id) if f.name.startswith(prefix)), key=lambda f: f.name)


def _json(store, f):
    return json.loads(store.path_of(f).read_bytes())


# --------------------------------------------------------------------------------------------- loaders
def stage_muni(con, store: RawStore, sdir: Path) -> dict:
    counts = {}

    def entities():
        for f in _files(store, "muni_api", "municipalities_p"):
            for i, m in enumerate(parsers.muni_facts(_json(store, f))):
                yield {"demarcation_code": m["municipality.demarcation_code"], "name": m["municipality.name"],
                       "long_name": m["municipality.long_name"], "province_code": m["municipality.province_code"],
                       "province_name": m["municipality.province_name"], "category": m["municipality.category"],
                       "miif_category": m.get("municipality.miif_category"), "name_key": muni_key(m["municipality.name"]),
                       "raw_file_id": f.sha256,
                       "source_locator": f"{f.name}#data[{i}]"}
    counts["staging.muni_entity"] = write_table(con, sdir, "staging.muni_entity", entities(), {
        "demarcation_code": "VARCHAR", "name": "VARCHAR", "long_name": "VARCHAR", "province_code": "VARCHAR",
        "province_name": "VARCHAR", "category": "VARCHAR", "miif_category": "VARCHAR", "name_key": "VARCHAR",
        "raw_file_id": "VARCHAR",
        "source_locator": "VARCHAR"})

    def changes():
        for f in _files(store, "muni_api", "demarcation_changes_p"):
            for m in parsers.muni_facts(_json(store, f)):
                yield {"old_code": m["old_demarcation.code"], "new_code": m["new_demarcation.code"],
                       "old_transition": m["old_code_transition.code"], "new_transition": m["new_code_transition.code"],
                       "change_date": m["date.date"], "raw_file_id": f.sha256}
    counts["staging.muni_demarcation_change"] = write_table(con, sdir, "staging.muni_demarcation_change", changes(), {
        "old_code": "VARCHAR", "new_code": "VARCHAR", "old_transition": "VARCHAR", "new_transition": "VARCHAR",
        "change_date": "DATE", "raw_file_id": "VARCHAR"})

    def items():
        for f in _files(store, "muni_api", "incexp_v2_members_item"):
            for m in _json(store, f)["data"]:
                yield {"item_code": m["item.code"], "item_label": m["item.label"],
                       "return_form_structure": m.get("item.return_form_structure")}
    counts["staging.muni_incexp_item"] = write_table(con, sdir, "staging.muni_incexp_item", items(), {
        "item_code": "VARCHAR", "item_label": "VARCHAR", "return_form_structure": "VARCHAR"})

    def incexp():
        for f in _files(store, "muni_api", "incexp_v2_fye"):
            for i, c in enumerate(parsers.muni_cells(_json(store, f))):
                from thusa.normalise import to_cents
                yield {"demarcation_code": c["demarcation.code"], "fye": c["financial_year_end.year"],
                       "amount_type": c["amount_type.code"], "item_code": c["item.code"],
                       "amount_cents": to_cents(c.get("amount.sum")), "raw_file_id": f.sha256,
                       "source_locator": f"{f.url}#cells[{i}]"}
    counts["staging.muni_incexp"] = write_table(con, sdir, "staging.muni_incexp", incexp(), {
        "demarcation_code": "VARCHAR", "fye": "INTEGER", "amount_type": "VARCHAR", "item_code": "VARCHAR",
        "amount_cents": "BIGINT", "raw_file_id": "VARCHAR", "source_locator": "VARCHAR"})

    def uifw():
        from thusa.normalise import to_cents
        for f in _files(store, "muni_api", "uifwexp_p"):
            for i, c in enumerate(parsers.muni_cells(_json(store, f))):
                yield {"demarcation_code": c["demarcation.code"], "fye": c["financial_year_end.year"],
                       "item_code": c["item.code"], "amount_cents": to_cents(c.get("amount.sum")),
                       "raw_file_id": f.sha256, "source_locator": f"{f.url}#cells[{i}]"}
    counts["staging.muni_uifw"] = write_table(con, sdir, "staging.muni_uifw", uifw(), {
        "demarcation_code": "VARCHAR", "fye": "INTEGER", "item_code": "VARCHAR", "amount_cents": "BIGINT",
        "raw_file_id": "VARCHAR", "source_locator": "VARCHAR"})

    def audits():
        for f in _files(store, "muni_api", "audit_opinions_p"):
            for i, m in enumerate(parsers.muni_facts(_json(store, f))):
                yield {"demarcation_code": m["demarcation.code"], "fye": m["financial_year_end.year"],
                       "opinion_code": m.get("opinion.code"), "opinion_label": m.get("opinion.label"),
                       "report_url": m.get("opinion.report_url"), "raw_file_id": f.sha256,
                       "source_locator": f"{f.name}#data[{i}]"}
    counts["staging.muni_audit"] = write_table(con, sdir, "staging.muni_audit", audits(), {
        "demarcation_code": "VARCHAR", "fye": "INTEGER", "opinion_code": "VARCHAR", "opinion_label": "VARCHAR",
        "report_url": "VARCHAR", "raw_file_id": "VARCHAR", "source_locator": "VARCHAR"})
    return counts


REL_COLS = {"ocid": "VARCHAR", "release_id": "VARCHAR", "release_date": "DATE", "buyer_id": "VARCHAR",
            "buyer_name": "VARCHAR", "buyer_key": "VARCHAR", "tender_id": "VARCHAR", "tender_title": "VARCHAR", "tender_status": "VARCHAR",
            "procurement_method": "VARCHAR", "main_category": "VARCHAR", "category": "VARCHAR",
            "province": "VARCHAR", "tender_value_cents": "BIGINT", "tender_value_note": "VARCHAR",
            "doc_url": "VARCHAR", "source_locator": "VARCHAR", "raw_file_id": "VARCHAR"}
AWD_COLS = {"ocid": "VARCHAR", "award_id": "VARCHAR", "award_status": "VARCHAR", "supplier_id": "VARCHAR",
            "supplier_name": "VARCHAR", "supplier_key": "VARCHAR", "supplier_person_key": "VARCHAR", "n_suppliers": "INTEGER", "value_cents": "BIGINT",
            "value_note": "VARCHAR", "date_signed": "DATE", "release_date": "DATE", "source_locator": "VARCHAR",
            "raw_file_id": "VARCHAR"}


def stage_ocds(con, store: RawStore, sdir: Path) -> dict:
    """Bulk + delta compiled releases; the newest release per ocid wins (delta overrides bulk)."""
    latest: dict[str, tuple] = {}
    for f in _files(store, "etenders_ocds"):
        if f.name.endswith(".jsonl.gz"):
            it = ((f"{f.name}:line {i}", r) for i, r in parsers.iter_jsonl_gz(store.path_of(f).read_bytes()))
        else:
            it = ((f"{f.url}#releases[{i}]", r) for i, r in enumerate(_json(store, f).get("releases", [])))
        for loc, rel in it:
            key = rel.get("ocid")
            if key is None:
                continue
            prev = latest.get(key)
            if prev is None or (rel.get("date") or "") >= (prev[2].get("date") or ""):
                latest[key] = (f.sha256, loc, rel)
    rels, awds = [], []
    for sha, loc, rel in latest.values():
        r, a = parsers.ocds_release_rows(rel, loc)
        r["raw_file_id"] = sha
        rels.append(r)
        for x in a:
            x["raw_file_id"] = sha
            awds.append(x)
    return {"staging.ocds_release": write_table(con, sdir, "staging.ocds_release", rels, REL_COLS),
            "staging.ocds_award": write_table(con, sdir, "staging.ocds_award", awds, AWD_COLS)}


RSR_COLS = {"row_no": "INTEGER", "page": "INTEGER", "name": "VARCHAR", "name_key": "VARCHAR", "is_person": "BOOLEAN",
            "identifier_kind": "VARCHAR", "cipc_reg_no": "VARCHAR", "person_id_hmac": "VARCHAR",
            "restriction_type": "VARCHAR", "reason": "VARCHAR", "period_from": "DATE", "period_to": "DATE",
            "authorised_by": "VARCHAR", "raw_file_id": "VARCHAR", "source_locator": "VARCHAR"}


def stage_rsr(con, store: RawStore, sdir: Path, secret: bytes) -> dict:
    rows = []
    for f in _files(store, "rsr"):
        with pdfplumber.open(store.path_of(f)) as pdf:
            words = [p.extract_words() for p in pdf.pages]
        for r in parsers.rsr_records(parsers.rsr_rows_from_words(words), secret):
            r["raw_file_id"] = f.sha256
            r["source_locator"] = f"page {r['page']}, row {r['row_no']}"
            rows.append(r)
    return {"staging.rsr": write_table(con, sdir, "staging.rsr", rows, RSR_COLS)}


NT_COLS = {"vote_number": "VARCHAR", "department": "VARCHAR", "programme": "VARCHAR", "econ1": "VARCHAR",
           "econ2": "VARCHAR", "financial_year": "INTEGER", "budget_phase": "VARCHAR", "amount_cents": "BIGINT",
           "value_note": "VARCHAR", "source_locator": "VARCHAR", "raw_file_id": "VARCHAR"}


def stage_nt_budget(con, store: RawStore, sdir: Path) -> dict:
    def rows():
        for f in _files(store, "nt_budget"):
            if f.name.lower().endswith(".csv"):
                for r in parsers.nt_bva_rows(store.path_of(f).read_bytes()):
                    r["raw_file_id"] = f.sha256
                    r["source_locator"] = f"{f.name}:{r['source_locator']}"
                    yield r
    return {"staging.nt_bva": write_table(con, sdir, "staging.nt_bva", rows(), NT_COLS)}


PPD_COLS = {"department": "VARCHAR", "supplier_name": "VARCHAR", "supplier_key": "VARCHAR", "amount_cents": "BIGINT",
            "payment_date": "DATE", "system": "VARCHAR", "financial_year": "VARCHAR", "quantity": "DOUBLE",
            "unit": "VARCHAR", "item_description": "VARCHAR", "commodity_code": "VARCHAR",
            "commodity_title": "VARCHAR", "province": "VARCHAR", "source_locator": "VARCHAR", "raw_file_id": "VARCHAR"}


def stage_ppd(con, store: RawStore, sdir: Path) -> dict:
    def rows():
        for f in _files(store, "ppd_payments"):
            for r in parsers.ppd_rows(store.path_of(f).read_bytes()):
                r["raw_file_id"] = f.sha256
                r["source_locator"] = f"{f.name}:{r['source_locator']}"
                yield r
    return {"staging.ppd_payment": write_table(con, sdir, "staging.ppd_payment", rows(), PPD_COLS)}


FUEL_COLS = {"year": "INTEGER", "month": "INTEGER", "grade": "VARCHAR", "grade_label": "VARCHAR",
             "cents_per_litre": "DECIMAL(10,3)", "source_locator": "VARCHAR", "raw_file_id": "VARCHAR",
             "fetched_at_utc": "VARCHAR"}
CPI_COLS = {"year": "INTEGER", "month": "INTEGER", "index_value": "DOUBLE", "base_period": "VARCHAR",
            "source_locator": "VARCHAR", "raw_file_id": "VARCHAR"}


def stage_prices(con, store: RawStore, sdir: Path) -> dict:
    """Fuel price history (DMPR) and CPI (OECD republication of Stats SA). Several monthly DMPR documents can
    hold the same month; the most recently fetched document wins (deduplicated in the curated model)."""
    def fuel():
        for f in _files(store, "dmpr_fuel"):
            parse = parsers.fuel_history_pdf_rows if f.name.endswith(".pdf") else parsers.fuel_history_rows
            for r in parse(store.path_of(f).read_bytes(), f.name):
                r["raw_file_id"], r["fetched_at_utc"] = f.sha256, f.fetched_at_utc
                r["source_locator"] = f"{f.name}:{r['source_locator']}"
                yield r

    def cpi():
        for f in _files(store, "oecd_cpi"):
            for r in parsers.oecd_cpi_rows(store.path_of(f).read_bytes()):
                r["raw_file_id"] = f.sha256
                r["source_locator"] = f"{f.name}:{r['source_locator']}"
                yield r
    return {"staging.fuel_price": write_table(con, sdir, "staging.fuel_price", fuel(), FUEL_COLS),
            "staging.cpi": write_table(con, sdir, "staging.cpi", cpi(), CPI_COLS)}
