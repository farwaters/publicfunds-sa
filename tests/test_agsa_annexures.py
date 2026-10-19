"""CHG-2026-011: AGSA annexure ingest (Excel, stdlib reader), opinions and UIF&W amounts with lineage."""
import io
import zipfile
from types import SimpleNamespace
from xml.sax.saxutils import escape

from thusa import parsers
from thusa.connectors import agsa
from thusa.http import FetchError
from thusa.raw import RawStore


def _xlsx(rows) -> bytes:
    """Minimal one-sheet workbook (inline strings, numbers), laid out like an AGSA annexure."""
    def cell(r, c, v):
        ref = f"{chr(65 + c)}{r}" if c < 26 else f"A{chr(65 + c - 26)}{r}"
        if v is None:
            return ""
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
    body = "".join(f'<row r="{i}">{"".join(cell(i, j, v) for j, v in enumerate(r))}</row>' for i, r in enumerate(rows, 1))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rns}><sheets><sheet name="Annexure 1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{body}</sheetData></worksheet>")
    return buf.getvalue()


A1 = _xlsx([
    ["Annexure 1: Auditees' audit outcomes"], [],
    ["Number", "Auditee", "Province", "Auditee category", "Auditee type", "Municipal\ndistrict", "2023-24 audit outcomes",
     None, "2022-23 audit outcomes", None, "Unauthorised, irregular as well as\nfruitless and wasteful expenditure", None, None],
    ["Number", None, None, None, None, None, "Audit opinion", "Compliance with legislation", "Audit opinion",
     "Compliance with legislation", "Unauthorised expenditure\nAmount R", "Irregular expenditure\nAmount R",
     "Fruitless and wasteful expenditure\nAmount R"],
    [], ["Financial audits (audit opinion before consolidation of controlled entities, where applicable)"],
    ["Unqualified with no findings "],
    [1, "City of Cape Town Metro", "WC", "MUN", "MET", "Cape Town Metro", "Unqualified with no findings", "",
     "Unqualified with no findings", "", 0, 634.3, 0],
    ["Audit not finalised at legislated date"],
    [2, "Mangaung Metro", "FS", "MUN", "MET", "Mangaung Metro", "Audit not finalised at legislated date", "",
     "Qualified", "R", "", "", ""],
    ["Consolidated audits (audit opinions on financial statements that include more than one auditee)"],
    ["Unqualified with findings "],
    [3, "City of Cape Town Metro", "WC", "MUN", "MET", "Cape Town Metro", "Unqualified with findings", "", "", "", "", "", ""],
])


def test_xlsx_reader_reads_inline_strings_numbers_and_blank_rows():
    rows = parsers.xlsx_first_sheet(A1)
    assert rows[0][0].startswith("Annexure 1") and rows[1] == [] and rows[7][11] == 634.3


def test_opinions_keep_group_section_year_and_lineage():
    op = list(parsers.agsa_opinion_rows(A1, "mfma-2023-24-annexure-1.xlsx"))
    cpt = [r for r in op if r["auditee"] == "City of Cape Town Metro"]
    assert {(r["fy_label"], r["audit_group"][:12], r["audit_opinion"]) for r in cpt} == {
        ("2023-24", "Financial au", "Unqualified with no findings"), ("2022-23", "Financial au", "Unqualified with no findings"),
        ("2023-24", "Consolidated", "Unqualified with findings")}
    assert all(r["regime"] == "MFMA" and r["fye"] == int(r["fy_label"][:4]) + 1 for r in op)
    assert cpt[0]["source_locator"] == "mfma-2023-24-annexure-1.xlsx#row8" and cpt[0]["province"] == "WC"
    assert len([r for r in op if r["auditee"] == "Mangaung Metro"]) == 2          # consolidated row had no prior year


def test_uifw_amounts_r_million_to_cents_and_blanks_unknown():
    u = list(parsers.agsa_uifw_rows(A1, "mfma-2023-24-annexure-1.xlsx"))
    irr = {(r["auditee"], r["audit_group"][:5]): r for r in u if r["uifw_type"] == "irregular"}
    assert irr[("City of Cape Town Metro", "Finan")]["amount_cents"] == 63_430_000_000          # R634.3m
    assert irr[("Mangaung Metro", "Finan")]["amount_cents"] is None                                # blank = unknown
    assert irr[("City of Cape Town Metro", "Conso")]["amount_cents"] is None
    assert {r["fy_label"] for r in u} == {"2023-24"}
    assert next(r for r in u if r["uifw_type"] == "unauthorised")["amount_cents"] == 0           # published 0 stays 0


def test_rejects_files_that_are_not_annexures():
    import pytest
    with pytest.raises(ValueError):
        list(parsers.agsa_opinion_rows(_xlsx([["Something else"]]), "mfma-x-annexure-1.xlsx"))


class _F:
    def __init__(self, fail=()):
        self.fail, self.requests_made = set(fail), 0

    def get(self, url):
        self.requests_made += 1
        if url in self.fail:
            raise FetchError("404")
        return SimpleNamespace(content=A1, url=url, status_code=200, headers={})


def test_connector_fetches_each_official_file_once(tmp_path):
    s = RawStore(tmp_path / "raw")
    first = list(agsa.ANNEXURES.values())[0]
    r = agsa.run(s, _F(fail={first}))
    assert r.status == "partial" and len(r.files) == 3 and r.requests == 4
    r = agsa.run(s, _F())
    assert r.status == "ok" and r.requests == 1 and len(r.notes) == 3
    r = agsa.run(s, _F())
    assert r.status == "unchanged" and r.requests == 0
    assert all(u.startswith(("https://mfma-2024.agsa.co.za/", "https://pfma-2023-24.agsa.co.za/"))
               for u in agsa.ANNEXURES.values())
