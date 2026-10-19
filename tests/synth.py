"""Synthetic raw inputs for offline tests. All names, IDs and amounts are invented test data."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from thusa.raw import RawStore

MUNI_URL = "https://municipaldata.treasury.gov.za/api/cubes"


def minimal_pdf(lines: list[tuple[float, float, str]], width: float = 907, height: float = 640) -> bytes:
    """Tiny valid PDF with Helvetica text at (x, top) positions (top measured from the page top)."""
    ops = []
    for x, top, text in lines:
        y = height - top - 7
        esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"BT /F1 7 Tf {x:.1f} {y:.1f} Td ({esc}) Tj ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >> >>".encode(),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


RSR_LINES = [
    (19, 23, "Restricted Supplier and Tender Defaulter Report"),
    (57, 131, "Name of Supplier/"), (208, 131, "Registration Number/"), (345, 131, "Restriction Type"),
    (57, 143, "Name of Person"), (208, 143, "Identification Number"),
    (48, 158, "1"), (57, 158, "BADCO TRADING"), (208, 158, "2015/123456/07"), (345, 158, "Restricted Supplier"),
    (452, 158, "Fraud"), (643, 158, "2022-01-01"), (748, 158, "2032-01-01"), (803, 158, "Testville Local"),
    (803, 169, "Municipality"),
    (48, 190, "2"), (57, 190, "DOE, JANE"), (208, 190, "8001015009087"), (345, 190, "Restricted Supplier"),
    (452, 190, "Non - Declaration of"), (452, 201, "Interest"), (643, 190, "2023-06-01"), (748, 190, "2028-06-01"),
    (803, 190, "Eskom"),
    (48, 600, "Page: 1 of 1"), (700, 600, "Generated on: 2026-09-15"),
]


def _muni_payloads():
    munis = [("TST", "Testville", "A", "GT"), ("TS1", "Sampleton", "B", "WC"), ("OLD", "Oldtown", "B", "KZ")]
    ent = {"total_fact_count": 3, "page_size": 10000, "page": 1, "data": [
        {"municipality.demarcation_code": c, "municipality.name": n, "municipality.long_name": f"{n}, {p}",
         "municipality.province_code": p, "municipality.province_name": p, "municipality.category": cat,
         "municipality.miif_category": cat} for c, n, cat, p in munis]}
    dem = {"total_fact_count": 1, "page_size": 10000, "page": 1, "data": [
        {"old_demarcation.code": "OLD", "new_demarcation.code": "TS1", "old_code_transition.code": "disestablished",
         "new_code_transition.code": "continue", "date.date": "2016-08-03"}]}
    items = {"data": [{"item.code": "0200", "item.label": "Property rates"},
                      {"item.code": "3100", "item.label": "Employee related costs"},
                      {"item.code": "3600", "item.label": "Depreciation, Amortisation and Impairment"},
                      {"item.code": "3800", "item.label": "Contracted services"}]}
    cells = []
    for fye in (2023, 2024):
        for code, budget in (("TST", 100_000_000.0), ("TS1", 50_000_000.0)):
            for at in ("ORGB", "ADJB", "AUDA"):
                over = 1.6 if (code == "TST" and fye == 2024 and at == "AUDA") else 1.0
                cells += [
                    {"demarcation.code": code, "financial_year_end.year": fye, "amount_type.code": at,
                     "item.code": "0200", "amount.sum": budget * 1.1},
                    {"demarcation.code": code, "financial_year_end.year": fye, "amount_type.code": at,
                     "item.code": "3100", "amount.sum": budget * 0.6 * over},
                    {"demarcation.code": code, "financial_year_end.year": fye, "amount_type.code": at,
                     "item.code": "3800", "amount.sum": budget * 0.4 * over},
                    {"demarcation.code": code, "financial_year_end.year": fye, "amount_type.code": at,
                     "item.code": "3600", "amount.sum": None},  # unknown, must stay NULL
                ]
    incexp = {"total_cell_count": len(cells), "page_size": 20000, "page": 1, "cells": cells}
    uifw_cells = []
    for fye, amt in ((2021, 5e6), (2022, 8e6), (2023, 20e6), (2024, 50e6)):
        for item in ("irregular", "unauthorised", "fruitless"):
            uifw_cells.append({"demarcation.code": "TST", "financial_year_end.year": fye, "item.code": item,
                               "amount.sum": amt if item == "irregular" else 0.0})
    uifw = {"total_cell_count": len(uifw_cells), "page_size": 20000, "page": 1, "cells": uifw_cells}
    audit = {"total_fact_count": 2, "page_size": 10000, "page": 1, "data": [
        {"demarcation.code": "TST", "financial_year_end.year": 2023, "opinion.code": "qualified",
         "opinion.label": "Qualified", "opinion.report_url": "https://example.org/tst-2023.pdf"},
        {"demarcation.code": "TST", "financial_year_end.year": 2024, "opinion.code": "outstanding",
         "opinion.label": "Outstanding", "opinion.report_url": None}]}
    return {"municipalities_p1.json": ent, "demarcation_changes_p1.json": dem,
            "incexp_v2_members_item.json": items, "incexp_v2_fye2023_p1.json": incexp,
            "uifwexp_p1.json": uifw, "audit_opinions_p1.json": audit}


def _ocds_gz() -> bytes:
    rels = []
    for i in range(1, 1201):  # >= 1,000 releases in FYE 2024 so the source counts as 'live'
        sup = "BADCO TRADING (PTY) LTD" if i == 1 else ("Acme Builders" if i % 2 else f"Supplier {i % 7}")
        rels.append({
            "ocid": f"ocds-test-{i}", "id": f"r{i}", "date": "2024-02-10T00:00:00Z", "tag": ["compiled"],
            "buyer": {"id": "B1", "name": "Testville Metropolitan Municipality"},
            "tender": {"id": str(i), "title": f"Tender {i}", "value": {"amount": 0, "currency": "ZAR"},
                       "procurementMethod": "open", "contactPerson": {"name": "Private Person", "email": "x@y.z"},
                       "documents": [{"url": f"https://example.org/doc{i}.pdf"}]},
            "awards": [{"id": f"a{i}", "status": "active",
                        "value": {"amount": (10.0 if i % 10 == 0 else 1_000_000.0 + i)},
                        "suppliers": [{"id": f"s{i}", "name": sup}]}],
            "contracts": [{"awardID": f"a{i}", "dateSigned": "2024-02-15T00:00:00Z"}],
        })
    return gzip.compress("\n".join(json.dumps(r) for r in rels).encode())


def _nt_csv() -> bytes:
    head = ("Government;VoteNumber;Department;ProgNumber;Programme;SubprogNumber;Subprogramme;EconomicClassification1;"
            "EconomicClassification2;EconomicClassification3;EconomicClassification4;EconomicClassification5;"
            "FunctionGroup1;FinancialYear;BudgetPhase;AmountKind;Value")
    rows = [head]
    for phase, v in (("Final Appropriation", "100000000"), ("Audit Outcome", "110000000"),
                     ("Main appropriation", "9,99999E+99")):
        rows.append(f"South Africa;99;Test Department;1;Admin;1;Office;Current;Current payments;C;C;C;G;2023;{phase};Total;{v}")
    return ("\n".join(rows) + "\n").encode("utf-8-sig")


def build_raw(root: Path) -> RawStore:
    store = RawStore(root / "data" / "raw")
    for name, payload in _muni_payloads().items():
        store.save("muni_api", name, json.dumps(payload).encode(), f"{MUNI_URL}/{name}")
    store.save("etenders_ocds", "full.jsonl.gz", _ocds_gz(), "https://example.org/full.jsonl.gz")
    store.save("rsr", "RestrictedSuppliersReport.pdf", minimal_pdf(RSR_LINES), "https://example.org/rsr.pdf")
    store.save("nt_budget", "Budget_vs_Actual_test.csv", _nt_csv(), "https://example.org/bva.csv")
    return store
