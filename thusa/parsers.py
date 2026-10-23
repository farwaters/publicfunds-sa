"""Source-specific parsers: raw bytes -> plain row dicts (no DB). Unit-tested in tests/test_parsers.py."""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
from typing import Iterator

from thusa.normalise import (classify_identifier, hmac_id, muni_key, norm_name, ocds_value_cents, parse_date,
                             person_key, to_cents)

# --------------------------------------------------------------------------------------------- muni
def muni_cells(payload: dict) -> list[dict]:
    return payload.get("cells", [])


def muni_facts(payload: dict) -> list[dict]:
    return payload.get("data", [])


# --------------------------------------------------------------------------------------------- RSR
RSR_COLUMNS = [  # (name, x_start) from the SSRS header row; verified on the 15 Sep 2026 report
    ("name", 56), ("identifier", 205), ("restriction_type", 342), ("reason", 449),
    ("period_from", 583), ("period_to", 695), ("authorised_by", 800),
]


def _col_for(x0: float) -> str | None:
    col = None
    for name, start in RSR_COLUMNS:
        if x0 >= start:
            col = name
    return col


def rsr_rows_from_words(pages_words: list[list[dict]], header_bottom: float = 150.0) -> list[dict]:
    """Rebuild table rows from pdfplumber words. A row starts where a bare integer sits left of the
    name column; continuation lines belong to the row above. Page header and footer lines are skipped."""
    rows: list[dict] = []
    for page_no, words in enumerate(pages_words, start=1):
        footer_top = min((w["top"] for w in words if w["text"] == "Page:"), default=float("inf"))
        body = [w for w in words if header_bottom <= w["top"] < footer_top - 2]
        cur = rows[-1] if rows else None  # a row may continue across a page break
        for w in sorted(body, key=lambda w: (round(w["top"]), w["x0"])):
            if w["x0"] < 56 and w["text"].isdigit():
                cur = {"row_no": int(w["text"]), "page": page_no, **{c: [] for c, _ in RSR_COLUMNS}}
                rows.append(cur)
            elif cur is not None and (col := _col_for(w["x0"])):
                cur[col].append(w["text"])
    return [{k: " ".join(v).strip() if isinstance(v, list) else v for k, v in r.items()} for r in rows]


def rsr_records(rows: list[dict], secret: bytes) -> list[dict]:
    """Typed RSR records. SA ID numbers become HMACs here and are never emitted raw (POPIA)."""
    out = []
    for r in rows:
        kind, ident = classify_identifier(r.get("identifier"))
        # 'other' identifiers are malformed ID numbers in practice; treat as personal data, never store raw
        is_person = kind in ("sa_id", "other") or ("," in (r.get("name") or "") and kind != "cipc_reg")
        out.append({
            "row_no": r["row_no"], "page": r["page"],
            "name": r.get("name") or None,
            "name_key": person_key(r.get("name")) if is_person else norm_name(r.get("name")),
            "is_person": is_person,
            "identifier_kind": kind,
            "cipc_reg_no": ident if kind == "cipc_reg" else None,
            "person_id_hmac": hmac_id(secret, ident) if kind in ("sa_id", "other") else None,
            "restriction_type": r.get("restriction_type") or None,
            "reason": r.get("reason") or None,
            "period_from": parse_date(r.get("period_from")),
            "period_to": parse_date(r.get("period_to")),
            "authorised_by": r.get("authorised_by") or None,
        })
    return out


# --------------------------------------------------------------------------------------------- OCDS
def iter_jsonl_gz(data: bytes) -> Iterator[tuple[int, dict]]:
    with gzip.open(io.BytesIO(data), "rt", encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            if line.strip():
                yield i, json.loads(line)


def ocds_release_rows(rel: dict, locator: str) -> tuple[dict, list[dict]]:
    """One compiled release -> (release row, award-supplier rows). Contact persons are dropped (POPIA)."""
    tender = rel.get("tender") or {}
    buyer = rel.get("buyer") or {}
    tv, tnote = ocds_value_cents((tender.get("value") or {}).get("amount"))
    docs = tender.get("documents") or []
    release = {
        "ocid": rel.get("ocid"), "release_id": rel.get("id"), "release_date": parse_date(rel.get("date")),
        "buyer_id": buyer.get("id"), "buyer_name": (buyer.get("name") or "").strip() or None,
        "buyer_key": muni_key(buyer.get("name")),
        "tender_id": tender.get("id"), "tender_title": tender.get("title"),
        "tender_status": tender.get("status"), "procurement_method": tender.get("procurementMethod"),
        "main_category": tender.get("mainProcurementCategory"), "category": tender.get("category"),
        "province": tender.get("province"), "tender_value_cents": tv, "tender_value_note": tnote,
        "doc_url": docs[0].get("url") if docs else None, "source_locator": locator,
    }
    signed = {c.get("awardID"): parse_date(c.get("dateSigned")) for c in rel.get("contracts") or []}
    awards = []
    for a in rel.get("awards") or []:
        cents, note = ocds_value_cents((a.get("value") or {}).get("amount"))
        sups = a.get("suppliers") or []
        for s in sups or [{}]:
            awards.append({
                "ocid": rel.get("ocid"), "award_id": str(a.get("id")), "award_status": a.get("status"),
                "supplier_id": s.get("id"), "supplier_name": (s.get("name") or "").strip() or None,
                "supplier_key": norm_name(s.get("name")), "supplier_person_key": person_key(s.get("name")),
                "n_suppliers": len(sups),
                "value_cents": cents, "value_note": note,
                "date_signed": signed.get(a.get("id")) or signed.get(str(a.get("id"))),
                "release_date": parse_date(rel.get("date")), "source_locator": locator,
            })
    return release, awards


# --------------------------------------------------------------------------------------------- Vulekamali
NT_SENTINEL_RANDS = 1e15  # guard against absurd placeholders; none seen in the 2025 CSV (19 Oct 2026)


def nt_value_cents(raw: str) -> tuple[int | None, str | None]:
    s = (raw or "").strip()
    if not s:
        return None, "missing"
    if "E" in s.upper():
        v = float(s.replace(",", "."))
        if abs(v) >= NT_SENTINEL_RANDS:
            return None, "sentinel"
        return to_cents(v), "scientific_notation_precision_loss"
    return to_cents(s), None


def nt_bva_rows(data: bytes) -> Iterator[dict]:
    text = data.decode("utf-8-sig")
    for i, r in enumerate(csv.DictReader(io.StringIO(text), delimiter=";"), start=2):
        cents, note = nt_value_cents(r.get("Value"))
        yield {
            "government": r.get("Government"), "vote_number": r.get("VoteNumber"),
            "department": (r.get("Department") or "").strip(), "programme": r.get("Programme"),
            "econ1": r.get("EconomicClassification1"), "econ2": r.get("EconomicClassification2"),
            "financial_year": int(r["FinancialYear"]) if (r.get("FinancialYear") or "").isdigit() else None,
            "budget_phase": r.get("BudgetPhase"), "amount_cents": cents, "value_note": note,
            "source_locator": f"line {i}",
        }


# --------------------------------------------------------------------------------------------- PPD
PPD_ALIASES = {
    "department": ["department", "dept", "department name"],
    "supplier": ["supplier", "supplier name", "vendor", "payee"],
    "amount": ["amount", "payment amount", "value", "total amount"],
    "date": ["payment date", "date", "transaction date"],
    "system": ["system", "source system"],
    # CHG-2026-009: fields the unit-price check needs (LOGIS lines carry quantity; see RB-06)
    "financial_year": ["financial year", "fin year", "fiscal year", "year"],
    "quantity": ["quantity", "qty", "quantity issued", "quantity received"],
    "unit": ["unit", "unit of measure", "uom", "unit of issue"],
    "item": ["item description", "item", "description", "miin description", "item name"],
    "commodity_code": ["unspsc code", "commodity code", "unspsc commodity code"],
    "commodity_title": ["unspsc title", "commodity title", "unspsc commodity title", "commodity"],
    "province": ["province"],
}
PPD_REQUIRED = ("department", "supplier", "amount")       # without these a row is not a payment we can attribute


def _ppd_reader(data: bytes) -> tuple[csv.DictReader, dict]:
    text = data.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    lower = {h.lower().strip(): h for h in reader.fieldnames or []}
    return reader, {k: next((lower[a] for a in v if a in lower), None) for k, v in PPD_ALIASES.items()}


def ppd_schema(data: bytes) -> dict:
    """Header check for a dropped PPD export: which known fields were found, which required ones are missing.
    Only header names are reported (never row data)."""
    reader, col = _ppd_reader(data)
    return {"header": list(reader.fieldnames or []), "mapped": {k: v for k, v in col.items() if v},
            "missing_required": [k for k in PPD_REQUIRED if not col[k]]}


def _num(v) -> float | None:
    v = (v or "").strip().replace(" ", "").replace("\u00a0", "")
    if not v:
        return None
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def ppd_rows(data: bytes) -> Iterator[dict]:
    """CSV parser for the Power BI export; column names are matched by alias. Blank cells stay None (unknown)."""
    reader, col = _ppd_reader(data)
    g = lambda r, k: ((r.get(col[k]) or "").strip() or None) if col[k] else None  # noqa: E731
    for i, r in enumerate(reader, start=2):
        yield {
            "department": r.get(col["department"]) if col["department"] else None,
            "supplier_name": r.get(col["supplier"]) if col["supplier"] else None,
            "supplier_key": norm_name(r.get(col["supplier"])) if col["supplier"] else None,
            "amount_cents": to_cents(r.get(col["amount"])) if col["amount"] else None,
            "payment_date": parse_date(r.get(col["date"])) if col["date"] else None,
            "system": r.get(col["system"]) if col["system"] else None,
            "financial_year": g(r, "financial_year"), "quantity": _num(g(r, "quantity")), "unit": g(r, "unit"),
            "item_description": g(r, "item"), "commodity_code": g(r, "commodity_code"),
            "commodity_title": g(r, "commodity_title"), "province": g(r, "province"),
            "source_locator": f"line {i}",
        }


# ------------------------------------------------------------------------------------- price benchmarks
FUEL_GRADES = [("petrol_93_inland", "Petrol 93, inland"), ("petrol_95_coast", "Petrol 95, coast"),
               ("petrol_95_inland", "Petrol 95, inland"), ("diesel_005_inland", "Diesel 0.05% sulphur, inland"),
               ("diesel_005_coast", "Diesel 0.05% sulphur, coast"), ("paraffin_coast", "Illuminating paraffin, coast"),
               ("paraffin_inland", "Illuminating paraffin, inland")]
FUEL_SUBHEADER = ["Inland93", "Coast95", "Inland95", "Inland", "Coast", "Coast", "Inland"]
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                       "dec"], 1)}


def _docx_tables(docx: bytes) -> list[list[list[str]]]:
    import xml.etree.ElementTree as ET
    import zipfile
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml"))
    return [[[re.sub(r"\s+", " ", "".join(t.text or "" for t in tc.iter(w + "t"))).strip()
              for tc in tr.findall(w + "tc")] for tr in tbl.iter(w + "tr")] for tbl in root.iter(w + "tbl")]


def fuel_history_rows(blob: bytes, name: str = "") -> list[dict]:
    """Rows of the DMPR 'South African Fuel Price History' table (RSA cents per litre), from a DOCX or from the
    monthly ZIP that contains it. Blank cells (months not yet published) are skipped, never zeroed. The table layout
    is checked against the expected sub-header; an unexpected layout raises instead of guessing columns."""
    import zipfile
    docs: list[tuple[str, bytes]] = []
    z = zipfile.ZipFile(io.BytesIO(blob))
    if "word/document.xml" in z.namelist():
        docs.append((name, blob))
    else:
        docs += [(n, z.read(n)) for n in z.namelist() if re.search(r"(?i)history of fuel prices.*\.docx$", n)]
    out = []
    for docname, doc in docs:
        for tbl in _docx_tables(doc):
            if not tbl or "Fuel Price History" not in " ".join(tbl[0]):
                continue
            m = re.match(r"(\d{4})", tbl[0][0])
            if not m:
                raise ValueError(f"{docname}: no year in table heading {tbl[0][0]!r}")
            year = int(m.group(1))
            sub = next((i for i, r in enumerate(tbl) if [c.replace(" ", "") for c in r[1:]] == FUEL_SUBHEADER), None)
            if sub is None:
                raise ValueError(f"{docname}: unexpected fuel table layout (sub-header not found)")
            for i, r in enumerate(tbl[sub + 1:], sub + 2):
                mon = _MONTHS.get(r[0][:3].lower()) if r and r[0] else None
                if not mon:
                    continue
                for (grade, label), cell in zip(FUEL_GRADES, r[1:]):
                    if not cell.strip():
                        continue
                    out.append({"year": year, "month": mon, "grade": grade, "grade_label": label,
                                "cents_per_litre": float(cell.replace(",", "")),
                                "source_locator": f"{docname}#table-row{i}"})
    return out


_PDF_MONTH = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|July?|Aug|Sept?|Oct|Nov|Dec)$")


def _decimal_comma(tok: str) -> str:
    return tok.replace(",", ".") if re.fullmatch(r"\d{3,4},\d{2,3}", tok) else tok


def fuel_history_pdf_rows(blob: bytes, name: str = "") -> list[dict]:
    """Rows of a yearly DMPR 'Fuel Price History' PDF (same 7-column table as the DOCX). Each month row must
    yield exactly 7 numbers; rows that don't (PDF text splits some figures) are skipped and stay unknown -
    figures are never guessed or re-joined beyond a thousands gap like '2 112.00'. A decimal comma typed by the
    publisher ('1882,00', '1525,958': 3-4 digits, a comma, then 2-3 decimals) is read as the decimal point it
    stands for (CHG-2026-019). The token rule can also match a thousands-style group such as '152,525' (and a
    value like '123,456' would be read as 123.456); what keeps this harmless in these PDFs is the exactly-7-prices
    gate: a stray extra comma token makes 8 numbers and the row is skipped."""
    import pdfplumber
    out = []
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        text = "\n".join(pg.extract_text() or "" for pg in pdf.pages)
        m = re.search(r"Fuel Price History:\s*(\d{4})", text)
        if not m:
            raise ValueError(f"{name}: not a DMPR 'Fuel Price History' PDF (no year heading)")
        year = int(m.group(1))
        for pg_no, pg in enumerate(pdf.pages, 1):
            words = pg.extract_words(x_tolerance=1.5, y_tolerance=2)
            for mw in (w for w in words if _PDF_MONTH.match(w["text"])):
                cy = (mw["top"] + mw["bottom"]) / 2
                nums = sorted((w for w in words if w["x0"] > mw["x1"] and re.fullmatch(r"[\d.]+|\d{3,4},\d{2,3}", w["text"])
                               and abs((w["top"] + w["bottom"]) / 2 - cy) < 4), key=lambda w: w["x0"])
                joined = re.sub(r"(?<![\d.])(\d) (\d{3}\.\d+)", r"\1\2", " ".join(_decimal_comma(w["text"]) for w in nums))
                vals = re.findall(r"\d+(?:\.\d+)?", joined)
                if len(vals) != 7:
                    continue
                for (grade, label), v in zip(FUEL_GRADES, vals):
                    out.append({"year": year, "month": _MONTHS[mw["text"][:3].lower()], "grade": grade,
                                "grade_label": label, "cents_per_litre": float(v),
                                "source_locator": f"{name}#page{pg_no}-{mw['text']}"})
    return out


def oecd_cpi_rows(data: bytes) -> list[dict]:
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))), 2):
        if r.get("REF_AREA") != "ZAF" or r.get("MEASURE") != "CPI" or not r.get("OBS_VALUE"):
            continue
        y, m = r["TIME_PERIOD"].split("-")
        rows.append({"year": int(y), "month": int(m), "index_value": float(r["OBS_VALUE"]),
                     "base_period": r.get("BASE_PER") or None, "source_locator": f"line {i}"})
    return rows


def imf_cpi_rows(data: bytes) -> list[dict]:
    """IMF.STA:CPI SDMX-ML (structure-specific): South Africa, all-items index, monthly. Values as published."""
    import xml.etree.ElementTree as ET
    rows = []
    for s in ET.fromstring(data).iter():
        if not s.tag.endswith("Series") or s.get("COUNTRY") != "ZAF" or s.get("COICOP_1999") != "_T" \
                or s.get("TYPE_OF_TRANSFORMATION") != "IX" or s.get("FREQUENCY") != "M":
            continue
        for o in s:
            if not o.tag.endswith("Obs") or not o.get("OBS_VALUE"):
                continue
            y, m = o.get("TIME_PERIOD").split("-M")
            ref = o.get("REFERENCE_PERIOD") or s.get("COMMON_REFERENCE_PERIOD")
            base = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(ref[5:]) - 1]} {ref[:4]}" \
                if ref and "M" in ref else ref
            rows.append({"year": int(y), "month": int(m), "index_value": float(o.get("OBS_VALUE")),
                         "base_period": base, "source_locator": f"Obs TIME_PERIOD={o.get('TIME_PERIOD')}"})
    return rows


# --------------------------------------------------------------------------------------------- AGSA annexures
_XNS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _col_index(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def xlsx_first_sheet(blob: bytes) -> list[list]:
    """Cell values of the first worksheet (stdlib only: strings, numbers; blanks -> None)."""
    import zipfile
    from xml.etree import ElementTree as ET
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _XNS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{_XNS['m']}}}t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rid = wb.find("m:sheets/m:sheet", _XNS).get(_RNS)
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = next(r.get("Target") for r in rels if r.get("Id") == rid).lstrip("/")
    sheet = ET.fromstring(z.read(target if target.startswith("xl/") else "xl/" + target))
    rows = []
    for row in sheet.iter(f"{{{_XNS['m']}}}row"):
        vals: dict[int, object] = {}
        for c in row.findall("m:c", _XNS):
            v, t = c.find("m:v", _XNS), c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{_XNS['m']}}}t"))
            elif v is None or v.text is None:
                val = None
            elif t == "s":
                val = shared[int(v.text)]
            elif t in ("str", "e", "b"):
                val = v.text
            else:
                f = float(v.text)
                val = int(f) if f.is_integer() else f
            vals[_col_index(c.get("r"))] = val
        idx = int(row.get("r")) - 1
        while len(rows) < idx:
            rows.append([])
        rows.append([vals.get(i) for i in range(max(vals) + 1)] if vals else [])
    return rows


def _flat(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


_AGSA_YEAR = re.compile(r"^(\d{4})-(\d{2})$")
_AGSA_OUTCOME = re.compile(r"^(unqualified|qualified|adverse|disclaim|audit not finalised)", re.I)
_UIFW = {"unauthorised expenditure amount r": "unauthorised", "irregular expenditure amount r": "irregular",
         "fruitless and wasteful expenditure amount r": "fruitless_wasteful"}


def _agsa_header(rows):
    """(row index of the first 'Number' header row, merged header labels per column)."""
    h = next(i for i, r in enumerate(rows[:10]) if r and _flat(r[0]) == "number")
    top, sub, labels, cur = rows[h], rows[h + 1], [], ""
    for j in range(max(len(top), len(sub))):
        t = _flat(top[j]) if j < len(top) else ""
        cur = t or cur
        s = _flat(sub[j]) if j < len(sub) else ""
        labels.append((cur, s))
    return h, labels


def _agsa_rows(blob: bytes, name: str):
    rows = xlsx_first_sheet(blob)
    title = _flat(rows[0][0] if rows and rows[0] else "")
    if not title.startswith("annexure"):
        raise ValueError(f"{name}: no 'Annexure' title in cell A1")
    h, labels = _agsa_header(rows)
    regime = "MFMA" if name.lower().startswith("mfma") else "PFMA"
    group = section = None
    for i, r in enumerate(rows[h + 2:], start=h + 3):
        if not r or r[0] is None:
            continue
        if not isinstance(r[0], (int, float)):
            head = re.sub(r"\s+", " ", str(r[0])).strip()
            if _AGSA_OUTCOME.match(head):
                section = head                 # outcome heading, e.g. 'Unqualified with no findings'
            else:
                group, section = head, None    # audit group, e.g. 'Consolidated audits (...)', 'Small auditees'
            continue
        cell = {lab: (r[j] if j < len(r) else None) for j, lab in enumerate(labels)}
        base = {"regime": regime, "auditee": str(r[1]).strip() if r[1] is not None else None, "row_number": int(r[0]),
                "audit_group": group, "section": section, "source_locator": f"{name}#row{i}"}
        for (top, sub), v in cell.items():
            if top in ("auditee category",):
                base["auditee_category"] = v
            elif top in ("auditee type", "sphere"):
                base["auditee_type"] = v
            elif top in ("province", "national / province"):
                base["province"] = v
        yield base, cell


def agsa_opinion_rows(blob: bytes, name: str) -> Iterator[dict]:
    """Audit opinions per auditee and year: Annexure 3 (five years) and Annexure 1 (current and prior year)."""
    for base, cell in _agsa_rows(blob, name):
        for (top, sub), v in cell.items():
            y = _AGSA_YEAR.match(sub) or (sub == "audit opinion" and re.match(r"^(\d{4})-(\d{2}) audit outcomes$", top))
            if not y or v in (None, ""):
                continue
            yield {**base, "fy_label": f"{y.group(1)}-{y.group(2)}", "fye": int(y.group(1)) + 1,
                   "audit_opinion": str(v).strip()}


def agsa_uifw_rows(blob: bytes, name: str) -> Iterator[dict]:
    """Annexure 1 unauthorised / irregular / fruitless and wasteful expenditure for the report year, in cents.

    The column header reads 'Amount R' but values are in R million: e.g. City of Cape Town 2023-24 irregular
    expenditure 634.3 matches National Treasury's R634 262 thousand (KE-013). Blank cells stay unknown (None)."""
    title_year = None
    for base, cell in _agsa_rows(blob, name):
        if title_year is None:
            title_year = next((m.group(0)[:7] for (top, _), _v in cell.items()
                               if (m := re.match(r"^\d{4}-\d{2} audit outcomes$", top))), None)
        for (top, sub), v in cell.items():
            kind = _UIFW.get(sub)
            if not kind:
                continue
            cents = None if v in (None, "") else round(float(v) * 100_000_000)
            yield {**base, "fy_label": title_year, "fye": int(title_year[:4]) + 1 if title_year else None,
                   "uifw_type": kind, "amount_r_million": None if v in (None, "") else float(v),
                   "amount_cents": cents}
