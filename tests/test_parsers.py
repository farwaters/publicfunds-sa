import gzip
import json

import pdfplumber

from tests.synth import RSR_LINES, minimal_pdf
from thusa import parsers


def _words(lines):
    return [{"text": t, "x0": x, "top": top} for x, top, txt in lines for t in [txt] for _ in [0]]


def test_rsr_rows_from_synthetic_pdf(tmp_path):
    p = tmp_path / "rsr.pdf"
    p.write_bytes(minimal_pdf(RSR_LINES))
    with pdfplumber.open(p) as pdf:
        rows = parsers.rsr_rows_from_words([pg.extract_words() for pg in pdf.pages])
    assert [r["row_no"] for r in rows] == [1, 2]
    assert rows[0]["name"] == "BADCO TRADING"
    assert rows[0]["authorised_by"] == "Testville Local Municipality"  # continuation line joined
    assert rows[1]["reason"] == "Non - Declaration of Interest"
    assert "Page:" not in json.dumps(rows)  # footer skipped


def test_rsr_records_never_emit_raw_id():
    rows = [{"row_no": 1, "page": 1, "name": "DOE, JANE", "identifier": "8001015009087",
             "restriction_type": "Restricted Supplier", "reason": "x", "period_from": "2023-06-01",
             "period_to": "2028-06-01", "authorised_by": "Eskom"},
            {"row_no": 2, "page": 1, "name": "Ramoo Test", "identifier": "123",
             "restriction_type": "Restricted Supplier", "reason": "x", "period_from": "2023-06-01",
             "period_to": "2028-06-01", "authorised_by": "Eskom"}]
    recs = parsers.rsr_records(rows, b"secret")
    blob = json.dumps(recs, default=str)
    assert "8001015009087" not in blob and '"123"' not in blob
    assert recs[0]["is_person"] and recs[0]["name_key"] == "doe jane"
    assert recs[1]["is_person"] and recs[1]["person_id_hmac"]  # malformed IDs treated as personal


def test_ocds_release_rows_drops_contacts_and_zero_values():
    rel = {"ocid": "o1", "id": "r1", "date": "2024-02-10T00:00:00Z",
           "buyer": {"id": "B", "name": " Stellenbosch Municipality "},
           "tender": {"id": "1", "value": {"amount": 0}, "contactPerson": {"name": "Private Person"}},
           "awards": [{"id": "a1", "value": {"amount": 0}, "suppliers": [{"id": "s", "name": "X (Pty) Ltd"}]}],
           "contracts": [{"awardID": "a1", "dateSigned": "2024-02-11T00:00:00Z"}]}
    r, a = parsers.ocds_release_rows(rel, "line 1")
    assert r["tender_value_cents"] is None and r["tender_value_note"] == "zero_placeholder"
    assert r["buyer_key"] == "stellenbosch"
    assert "Private Person" not in json.dumps(r, default=str)
    assert a[0]["value_cents"] is None and a[0]["supplier_key"] == "x" and str(a[0]["date_signed"]) == "2024-02-11"


def test_iter_jsonl_gz():
    data = gzip.compress(b'{"a": 1}\n\n{"a": 2}\n')
    assert [r["a"] for _, r in parsers.iter_jsonl_gz(data)] == [1, 2]


def test_nt_value_cents():
    assert parsers.nt_value_cents("450000") == (45000000, None)
    assert parsers.nt_value_cents("9,99999E+99") == (None, "sentinel")
    assert parsers.nt_value_cents("1,06087E+11") == (10608700000000, "scientific_notation_precision_loss")
    assert parsers.nt_value_cents("") == (None, "missing")


def test_ppd_rows_aliases_and_semicolons():
    csv = "Department;Supplier Name;Payment Amount;Payment Date\nHealth;Acme (Pty) Ltd;1 234,50;2026-01-31\nHealth;Blank;;\n"
    rows = list(parsers.ppd_rows(csv.encode()))
    assert rows[0]["amount_cents"] == 123450 and rows[0]["supplier_key"] == "acme"
    assert rows[1]["amount_cents"] is None  # blank stays unknown
