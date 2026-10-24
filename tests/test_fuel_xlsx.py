"""CHG-2026-027: DMPR '<Month>-<Year>-Fuel-Regulations.xlsx' -> the 7 history grades for one month (cells only).

The workbooks below are small synthetic fixtures with the real sheet layout (headings, header rows, zone rows) and a few
real figures; the DMPR file itself is not committed (raw data is git-ignored). Real-file checks run only when the raw
files are present in this checkout's data/raw."""
import io
import zipfile
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest

from thusa import parsers
from thusa.connectors import prices
from thusa.http import FetchError
from thusa.raw import RawStore
from thusa.settings import get_paths

DEC = {"petrol_93_inland": 2126, "petrol_95_coast": 2058, "petrol_95_inland": 2141, "diesel_005_inland": 1978.83,
       "diesel_005_coast": 1895.53, "paraffin_coast": 1271.598, "paraffin_inland": 1373.098}
# History-table (PDF) rows for November 2025, as parsed from fuel-price-history-2025.pdf (see the RFC cross-check table).
NOV_HISTORY = {"petrol_93_inland": 2097.0, "petrol_95_coast": 2029.0, "petrol_95_inland": 2112.0,
               "diesel_005_inland": 1913.35, "diesel_005_coast": 1830.05, "paraffin_coast": 1197.118,
               "paraffin_inland": 1298.618}


def _cell(r, c, v):
    ref = f"{chr(65 + c)}{r}"
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"><v>{v}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'


def _xlsx(sheets: dict) -> bytes:
    """Workbook with the given {sheet name: rows}; row lists are positional (None = blank cell)."""
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f"<workbook {ns} {rns}><sheets>" + "".join(
            f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(sheets, 1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Type="worksheet" Target="worksheets/sheet{i}.xml"/>'
                             for i in range(1, len(sheets) + 1)) + "</Relationships>")
        for i, rows in enumerate(sheets.values(), 1):
            body = "".join(f'<row r="{n}">{"".join(_cell(n, j, v) for j, v in enumerate(r))}</row>'
                           for n, r in enumerate(rows, 1) if r)
            z.writestr(f"xl/worksheets/sheet{i}.xml", f"<worksheet {ns}><sheetData>{body}</sheetData></worksheet>")
    return buf.getvalue()


def _petrol_section(head, eff, p1a, p9c, drop=()):
    rows = [[None] * 4 + [head, None, None, eff], [None] * 9 + ["(SA c/l)"],
            ["ZONES", "BASIC", "ZONE", "RTL", "DEALER", " NOTIONAL PUMP PRICE", None, None, None, "EFFECTIVE", "  ACTUAL"],
            ["A ", "LIST", "DIFF", "WHOLESALE", "MARGIN", None, None, None, None, "NETT PRICE", "  PUMP"],
            [None, "PRICE", None, "PRICE", None, "ACTUAL", "ROUNDED", "ROUNDED", "PUMP", "AFTER", " PRICE"]]
    for z, v in (("1A", p1a), ("5A", 1111), ("9C", p9c)):
        if z not in drop:
            rows.append([z, "GAUTENG" if z == "9C" else 1700.1, 3.8, 1727.9, 315.1, v, v, v, 0, 1727.9, v])
    return rows + [[]]


def _wholesale_section(col0, head, eff, w1a, w9c, drop=(), hdr="Wholesale"):
    off = col0
    pad = [None] * off
    rows = [pad + [" ", head], [], pad + ["WHOLESALE PRICES IN THE REPUBLIC OF SOUTH AFRICA "], pad + [eff],
            pad + ["ZONES", "Basic", "Zone", "RTL"], pad + ["A & B", "List", "Diff.", hdr], pad + ["C & J", "Price", None, "Price"]]
    for z, v in (("1A", w1a), ("9C", w9c)):
        if z not in drop:
            rows.append(pad + [z, "GAUTENG" if z == "9C" else 1891.73, 3.8, v])
    return rows + [[]]


def workbook(v=DEC, eff="EFFECTIVE 03 DECEMBER 2025", **kw):
    pet = [[], [None, None, None, "PETROL PUMP PRICES BY ZONE IN THE REPUBLIC OF SOUTH AFRICA"], []]
    pet += _petrol_section("93 RON UNLEADED AND LEAD REPLACEMENT", eff, v["petrol_93_coast"] if "petrol_93_coast" in v else 2043,
                           v["petrol_93_inland"])
    pet += _petrol_section("95 RON UNLEADED ", eff, 2058, v["petrol_95_inland"])
    pet += _petrol_section("95 RON LEAD REPLACEMENT", eff, v["petrol_95_coast"], 2141)
    die = _wholesale_section(0, "Diesel 0.05% sulfur", eff, v["diesel_005_coast"], v["diesel_005_inland"])
    die += _wholesale_section(0, "Diesel 0.005% sulfur", eff, 1918.93, 2002.23)
    par = _wholesale_section(1, "Illuminating Paraffin", eff, v["paraffin_coast"], v["paraffin_inland"])
    sheets = {"LPG": [["LPG"]], "Illuminating Paraffin": par, "Diesel": die, "Petrol": pet}
    for k, f in kw.items():
        sheets = f(sheets)
    return _xlsx(sheets)


def parse(blob, name="December-2025-Fuel-Regulations.xlsx"):
    return parsers.fuel_regulations_xlsx_rows(blob, name)


# ---- (b) December 2025 values and shape --------------------------------------------------------------------------
def test_december_2025_values_for_the_seven_history_grades():
    rows = parse(workbook())
    assert {(r["year"], r["month"]) for r in rows} == {(2025, 12)}
    assert {r["grade"]: r["cents_per_litre"] for r in rows} == DEC
    assert [r["grade"] for r in rows] == [g for g, _ in parsers.FUEL_GRADES]          # the 7 grades, in history order
    assert {r["grade"]: r["grade_label"] for r in rows} == dict(parsers.FUEL_GRADES)
    assert all(set(r) == {"year", "month", "grade", "grade_label", "cents_per_litre", "source_locator"} for r in rows)


def test_source_locator_names_file_sheet_zone_and_cell():
    loc = {r["grade"]: r["source_locator"] for r in parse(workbook())}
    assert loc["petrol_93_inland"].startswith("December-2025-Fuel-Regulations.xlsx#Petrol!9C@K")
    assert loc["petrol_95_coast"].startswith("December-2025-Fuel-Regulations.xlsx#Petrol!1A@K")
    assert loc["diesel_005_coast"].startswith("December-2025-Fuel-Regulations.xlsx#Diesel!1A@D")
    assert loc["paraffin_inland"].startswith("December-2025-Fuel-Regulations.xlsx#Illuminating Paraffin!9C@E")
    assert len(set(loc.values())) == 7


def test_diesel_0005_section_is_never_used_for_the_0_05_grades():
    rows = {r["grade"]: r["cents_per_litre"] for r in parse(workbook())}
    assert 2002.23 not in rows.values() and 1918.93 not in rows.values()


def test_document_properties_are_never_read():
    blob = workbook()
    z = zipfile.ZipFile(io.BytesIO(blob))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as out:
        for n in z.namelist():
            out.writestr(n, z.read(n))
        out.writestr("docProps/core.xml", "<not-xml PERSONAL NAME")           # would raise if anything parsed it
    assert {r["grade"] for r in parse(buf.getvalue())} == set(DEC)


# ---- (a) cross-check: November 2025 workbook equals the November 2025 history-table rows --------------------------
def test_november_2025_workbook_figures_equal_the_history_table_rows():
    """Same code path on a November fixture carrying DMPR's November figures: the pump/wholesale cells are directly
    comparable to the history table (the real-file check is the next test and the RFC table)."""
    nov = dict(NOV_HISTORY)
    rows = parse(workbook(nov, eff="EFFECTIVE 05 NOVEMBER 2025"), "November-2025-Fuel-Regulations.xlsx")
    assert {r["grade"]: r["cents_per_litre"] for r in rows} == NOV_HISTORY and {r["month"] for r in rows} == {11}


def _raw_dir():
    return get_paths().raw


def _stored(source_id, name):
    f = RawStore(_raw_dir()).latest(source_id, name) if _raw_dir().exists() else None
    return (_raw_dir() / f.path) if f and (_raw_dir() / f.path).exists() else None


def _xcheck(name):
    p = get_paths().data / "xcheck" / name          # written by scripts/fuel_xlsx_crosscheck.py --fetch (git-ignored)
    return p if p.exists() else None


@pytest.mark.skipif(_xcheck("November-2025-Fuel-Regulations.xlsx") is None
                    or _stored("dmpr_fuel", "fuel-price-history-2025.pdf") is None,
                    reason="real November xlsx / history PDF not in data/ (run scripts/fuel_xlsx_crosscheck.py --fetch)")
def test_real_november_2025_workbook_equals_real_history_pdf():
    x = parse(_xcheck("November-2025-Fuel-Regulations.xlsx").read_bytes(), "November-2025-Fuel-Regulations.xlsx")
    pdf = {r["grade"]: r["cents_per_litre"] for r in parsers.fuel_history_pdf_rows(
        _stored("dmpr_fuel", "fuel-price-history-2025.pdf").read_bytes(), "fuel-price-history-2025.pdf") if r["month"] == 11}
    assert {r["grade"]: r["cents_per_litre"] for r in x} == pdf == NOV_HISTORY


# ---- (c) fail closed -----------------------------------------------------------------------------------------------
def _edit(sheet, fn):
    return lambda sheets: {**sheets, sheet: fn(sheets[sheet])}


def _drop_rows(match):
    return lambda rows: [r for r in rows if not any(isinstance(c, str) and match in c for c in r)]


def _only_first(match):
    def f(rows):
        seen = False
        out = []
        for r in rows:
            if any(c == match for c in r):
                if seen:
                    continue
                seen = True
            out.append(r)
        return out
    return f


@pytest.mark.parametrize("blob, why", [
    (_xlsx({"Diesel": [["x"]]}), "worksheet"),
    (workbook(a=_edit("Petrol", _drop_rows("95 RON LEAD REPLACEMENT"))), "section"),
    (workbook(a=_edit("Diesel", _drop_rows("0.05% sulfur"))), "section"),
    (workbook(a=_edit("Illuminating Paraffin", _drop_rows("Illuminating Paraffin"))), "section"),
    (workbook(a=_edit("Diesel", _drop_rows("0.005% sulfur"))), "section"),
    (workbook(a=_edit("Petrol", lambda rows: [[(None if c == "EFFECTIVE 03 DECEMBER 2025" else c) for c in r] for r in rows])), "EFFECTIVE"),
    (workbook(a=_edit("Petrol", lambda rows: [[(c.replace("DECEMBER", "NOVEMBER") if isinstance(c, str) else c) for c in r]
                                                for r in rows[:5]] + rows[5:])), "disagree"),
    (workbook(a=_edit("Diesel", lambda rows: [[(c.replace("DECEMBER", "JANUARY") if isinstance(c, str) else c) for c in r]
                                               for r in rows])), "disagree"),
    (workbook(a=_edit("Petrol", lambda rows: [[(None if c == "  ACTUAL" else c) for c in r] for r in rows])), "price column"),
    (workbook(a=_edit("Diesel", lambda rows: [[("Price" if c == "RTL" else c) for c in r] for r in rows])), "price column"),
    (workbook(a=_edit("Diesel", lambda rows: [[(None if c == "ZONES" else c) for c in r] for r in rows])), "ZONES"),
], ids=["no-sheet", "no-lrp95", "no-diesel005", "no-paraffin", "no-diesel0005", "no-eff-date-petrol", "date-mismatch",
        "sheets-disagree", "no-actual-col", "no-rtl-col", "no-zones-header"])
def test_fails_closed_on_missing_headings_or_columns(blob, why):
    with pytest.raises(ValueError, match=why):
        parse(blob)


@pytest.mark.parametrize("drop_zone", ["1A", "9C"])
def test_fails_closed_when_a_zone_row_is_missing(drop_zone):
    sheets = lambda s: {**s, "Diesel": _wholesale_section(0, "Diesel 0.05% sulfur", "EFFECTIVE 03 DECEMBER 2025", 1895.53,
                                                          1978.83, drop=(drop_zone,))
                        + _wholesale_section(0, "Diesel 0.005% sulfur", "EFFECTIVE 03 DECEMBER 2025", 1918.93, 2002.23)}
    with pytest.raises(ValueError, match=f"zone {drop_zone}"):
        parse(workbook(a=sheets))


def test_fails_closed_on_duplicate_zone_row():
    def dup(rows):
        i = next(n for n, r in enumerate(rows) if r and r[0] == "9C")
        return rows[:i + 1] + [rows[i]] + rows[i + 1:]
    with pytest.raises(ValueError, match="zone 9C row found 2 times"):
        parse(workbook(a=_edit("Petrol", dup)))


@pytest.mark.parametrize("bad", ["n/a", None, 12.5, 99999])
def test_fails_closed_on_non_numeric_or_implausible_price(bad):
    def poke(rows):
        i = next(n for n, r in enumerate(rows) if r and r[0] == "9C")
        rows = list(rows)
        rows[i] = rows[i][:10] + [bad]
        return rows
    with pytest.raises(ValueError, match="price cell"):
        parse(workbook(a=_edit("Petrol", poke)))


def test_fails_closed_when_file_name_month_disagrees_with_workbook():
    with pytest.raises(ValueError, match="file name says November 2025"):
        parse(workbook(), "November-2025-Fuel-Regulations.xlsx")


def test_a_failed_parse_returns_no_partial_rows():
    with pytest.raises(ValueError):
        parse(workbook(a=_edit("Illuminating Paraffin", _drop_rows("Illuminating Paraffin"))))


# ---- connector: fetched once, wrong content refused, failure noted ---------------------------------------------------
class _F:
    def __init__(self, body):
        self.body, self.urls, self.requests_made = body, [], 0

    def get(self, url):
        self.urls.append(url)
        if self.body is None:
            raise FetchError("HTTP 404")
        return SimpleNamespace(content=self.body, url=url, status_code=200, headers={"content-type": "text/html"})


def test_xlsx_url_is_the_public_portals_path_not_uat1():
    (name, url), = prices.FUEL_REGULATIONS_XLSX.items()
    assert name == "December-2025-Fuel-Regulations.xlsx" and "/uat1/" not in url
    assert url.startswith("https://www.dmpr.gov.za/Portals/0/Resources/Fuel%20Prices%20Adjustments/") and url.endswith(name)


def test_xlsx_fetched_once_with_hash_and_date_recorded(tmp_path):
    s, res = RawStore(tmp_path / "raw"), SimpleNamespace(files=[], notes=[])
    f = _F(workbook())
    prices.run_fuel_regulations_xlsx(s, f, res)
    rf = res.files[0]
    assert rf.name == "December-2025-Fuel-Regulations.xlsx" and len(rf.sha256) == 64 and rf.fetched_at_utc
    f2 = _F(workbook())
    prices.run_fuel_regulations_xlsx(s, f2, SimpleNamespace(files=[], notes=[]))
    assert f2.urls == []                                        # stored once, not fetched again


@pytest.mark.parametrize("body", [b"<html>Not found</html>", None])
def test_xlsx_non_workbook_or_404_is_noted_not_stored(tmp_path, body):
    s, res = RawStore(tmp_path / "raw"), SimpleNamespace(files=[], notes=[])
    prices.run_fuel_regulations_xlsx(s, _F(body), res)
    assert res.files == [] and "December-2025-Fuel-Regulations.xlsx" in res.notes[0]
    assert s.latest("dmpr_fuel", "December-2025-Fuel-Regulations.xlsx") is None


# ---- warehouse: the pipeline loads the new source (raw -> staging -> curated, DQ gate) ---------------------------------
def test_pipeline_loads_december_2025_into_curated_fuel_price_and_dq_passes(tmp_path):
    from datetime import date

    import duckdb

    from tests.synth import build_raw
    from thusa.build import build
    build_raw(tmp_path)
    RawStore(tmp_path / "data" / "raw").save("dmpr_fuel", "December-2025-Fuel-Regulations.xlsx", workbook(),
                                             "https://example.org/December-2025-Fuel-Regulations.xlsx")
    paths = get_paths(tmp_path)
    s = build(paths, as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, secret=b"test-secret",
              min_rows={"curated.gov_body": 3, "curated.muni_fin_line": 10, "curated.award": 100,
                        "curated.restriction": 2, "marts.coverage_cell": 10})
    assert s["dq"]["fail"] == []
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    got = {g: float(c) for g, c in con.execute(
        "SELECT grade, cents_per_litre FROM curated.fuel_price WHERE year = 2025 AND month = 12").fetchall()}
    assert got == DEC
    loc, url = con.execute("SELECT DISTINCT source_locator, source_url FROM curated.fuel_price WHERE year=2025 AND month=12 "
                           "AND grade='petrol_93_inland'").fetchone()
    assert "Petrol!9C@K" in loc and url.endswith("December-2025-Fuel-Regulations.xlsx")
    con.close()
