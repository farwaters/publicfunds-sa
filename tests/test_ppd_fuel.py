"""CHG-2026-009: PPD manual-drop schema check, DMPR yearly fuel history PDFs, D13 fuel unit-price detector."""
import io
from datetime import date
from types import SimpleNamespace

import duckdb
import pytest

from thusa import detectors, parsers
from thusa.connectors import ppd, prices
from thusa.http import FetchError
from thusa.raw import RawStore
from thusa.settings import load_yaml

D13 = load_yaml("detectors.yaml")["detectors"]["D13_fuel_unit_price"]
HEADER = ("Financial Year,Department,Province,Supplier Name,UNSPSC Code,UNSPSC Title,Item Description,"
          "Unit of Measure,Quantity,Amount\n")


def test_ppd_drop_rejects_files_without_required_columns(tmp_path):
    s, drop = RawStore(tmp_path / "raw"), tmp_path / "drop"
    drop.mkdir()
    (drop / "bad.csv").write_text("Department,Amount\nHealth,100\n")
    r = ppd.run(s, drop)
    assert r.status == "schema_mismatch" and not r.files
    assert "supplier" in r.errors[0] and "Health" not in r.errors[0]      # header names only, never row data
    (drop / "good.csv").write_text(HEADER + "2024/25,Health,GP,ACME FUELS,15101505,Diesel fuel,DIESEL 50PPM,L,1000,24 000.00\n")
    r = ppd.run(s, drop)
    assert r.status == "partial" and len(r.files) == 1


def test_ppd_rows_new_fields_cents_and_blanks():
    rows = list(parsers.ppd_rows((HEADER + "2024/25,Health,GP,ACME FUELS,15101505,Diesel fuel,DIESEL,L,1 000,\"24 000,50\"\n"
                                   "2024/25,Health,GP,ACME FUELS,,,,,,\n").encode()))
    a, b = rows
    assert a["amount_cents"] == 2400050 and a["quantity"] == 1000 and a["unit"] == "L"
    assert a["commodity_code"] == "15101505" and a["financial_year"] == "2024/25" and a["province"] == "GP"
    assert b["amount_cents"] is None and b["quantity"] is None and b["unit"] is None   # blanks stay unknown
    assert parsers.ppd_schema(HEADER.encode())["missing_required"] == []


def _history_pdf(year=2024, rows=None) -> bytes:
    """A small PDF laid out like DMPR's yearly 'Fuel Price History' table (text, not an image)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = rows or [("Jan", ["2217.00", "2177.00", "2249.00", "2063.17", "1990.97", "1438.438", "1530.938"]),
                    ("Feb", ["2292.00", "2252.00", "2324.00", "2136.17", "2063.97", "1491.438", "1583.938"]),
                    ("Mar", ["2413.00", "2341.00", "2 445.00", "2241.87", "2169.87", "1555.438", "1647.938"]),
                    ("Apr", ["2478.00", "2433.00", "2512.00", "2245", "09", "2166.09", "1519.738", "1618.938"])]
    fig = plt.figure(figsize=(8.27, 5))
    fig.text(0.05, 0.95, f"Fuel Price History: {year}.", fontsize=10)
    for i, (mon, vals) in enumerate(rows):
        y = 0.8 - i * 0.06
        fig.text(0.05, y, mon, fontsize=9)
        for j, v in enumerate(vals):
            fig.text(0.15 + j * 0.11, y, v, fontsize=9)
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf")
    plt.close(fig)
    return buf.getvalue()


def test_fuel_history_pdf_rows_skip_rows_that_dont_split_cleanly():
    rows = parsers.fuel_history_pdf_rows(_history_pdf(), "fuel-price-history-2024.pdf")
    months = {r["month"] for r in rows}
    assert months == {1, 2, 3}                                  # April has 8 tokens: skipped, stays unknown
    mar = {r["grade"]: r["cents_per_litre"] for r in rows if r["month"] == 3}
    assert mar["petrol_95_inland"] == 2445.0 and mar["diesel_005_inland"] == 2241.87   # '2 445.00' re-joined
    assert all(r["year"] == 2024 and r["source_locator"].startswith("fuel-price-history-2024.pdf#page1") for r in rows)
    with pytest.raises(ValueError):
        parsers.fuel_history_pdf_rows(_history_pdf_without_heading(), "x.pdf")


def test_fuel_history_pdf_rows_read_publisher_decimal_comma():
    """CHG-2026-019: DMPR types some figures with a decimal comma ('1882,00', '1525,958'); read as the decimal point.
    A comma with 1-3 leading digits (thousands-style) is not accepted, so such a row still stays unknown."""
    rows = parsers.fuel_history_pdf_rows(_history_pdf(2023, [
        ("Jan", ["2110.00", "2075.00", "2140.00", "2122,87", "2057.67", "1446.758", "1525,958"]),
        ("Feb", ["2 110.00", "2075.00", "2140.00", "2,122", "2057.67", "1446.758", "1525.958"])]), "h.pdf")
    jan = {r["grade"]: r["cents_per_litre"] for r in rows if r["month"] == 1}
    assert jan["diesel_005_inland"] == 2122.87 and jan["paraffin_inland"] == 1525.958 and len(jan) == 7
    assert {r["month"] for r in rows} == {1}


def test_fuel_history_pdf_rows_skip_row_with_extra_comma_token():
    """A thousands-style '152,525' matches the decimal-comma token rule; the exactly-7-prices gate keeps it harmless:
    the row yields 8 numbers and is skipped, so the month stays unknown rather than taking wrong values."""
    rows = parsers.fuel_history_pdf_rows(_history_pdf(2023, [
        ("Jan", ["2110.00", "2075.00", "2140.00", "2122.87", "2057.67", "1446.758", "1525.958"]),
        ("Feb", ["2110.00", "2075.00", "152,525", "2140.00", "2122.87", "2057.67", "1446.758", "1525.958"])]), "h.pdf")
    assert {r["month"] for r in rows} == {1}

def _history_pdf_without_heading():
    import matplotlib.pyplot as plt
    fig = plt.figure()
    fig.text(0.1, 0.5, "Something else")
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf")
    plt.close(fig)
    return buf.getvalue()


class _Fetcher:
    def __init__(self, bodies):
        self.bodies, self.requests_made, self.urls = bodies, 0, []

    def get(self, url):
        self.requests_made += 1
        self.urls.append(url)
        body = self.bodies.get(url, b"<html>")
        if body is None:
            raise FetchError("HTTP 404")
        return SimpleNamespace(content=body, url=url, status_code=200, headers={"content-type": "application/pdf"})


def test_fuel_history_fetched_once_and_failures_noted(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "FUEL_HISTORY_PDFS", {2023: "https://x/2023.pdf", 2024: "https://x/2024.pdf"})
    s, res = RawStore(tmp_path / "raw"), SimpleNamespace(files=[], notes=[])
    f = _Fetcher({"https://x/2024.pdf": _history_pdf(), "https://x/2023.pdf": None})
    prices.run_fuel_history(s, f, res)
    assert [x.name for x in res.files] == ["fuel-price-history-2024.pdf"] and "2023" in res.notes[0]
    f2 = _Fetcher({"https://x/2024.pdf": _history_pdf(), "https://x/2023.pdf": None})
    prices.run_fuel_history(s, f2, SimpleNamespace(files=[], notes=[]))
    assert f2.urls == ["https://x/2023.pdf"]                    # stored years are not fetched again


def _wh(payments):
    con = duckdb.connect()
    con.execute("CREATE SCHEMA curated")
    con.execute("CREATE TABLE curated.fuel_price (year INT, month INT, grade VARCHAR, cents_per_litre DOUBLE, "
                "source_url VARCHAR, source_locator VARCHAR)")
    for y, months in ((2024, range(4, 13)), (2025, range(1, 4))):
        for mo in months:
            for g, c in (("diesel_005_inland", 2400.0), ("diesel_005_coast", 2320.0), ("petrol_95_inland", 2500.0)):
                con.execute("INSERT INTO curated.fuel_price VALUES (?,?,?,?,?,?)", [y, mo, g, c, "https://dmpr/x.pdf", f"{y}-{mo}"])
    con.execute("""CREATE TABLE curated.payment (department VARCHAR, supplier_name VARCHAR, supplier_key VARCHAR,
        amount_cents BIGINT, quantity DOUBLE, unit VARCHAR, payment_date DATE, financial_year VARCHAR,
        item_description VARCHAR, commodity_code VARCHAR, commodity_title VARCHAR, source_file VARCHAR,
        source_sha256 VARCHAR, source_locator VARCHAR)""")
    for p in payments:
        row = {"department": "Health", "supplier_name": "ACME FUELS", "supplier_key": "ACME FUELS", "amount_cents": None,
               "quantity": None, "unit": "L", "payment_date": None, "financial_year": "2024/25",
               "item_description": "DIESEL 50PPM", "commodity_code": "15101505", "commodity_title": "Diesel fuel",
               "source_file": "ppd/x.csv", "source_sha256": "ab" * 32, "source_locator": "x.csv:line 2"} | p
        con.execute(f"INSERT INTO curated.payment VALUES ({','.join('?' * 14)})", list(row.values()))
    return con


def test_d13_flags_r123_diesel_but_not_normal_prices_or_unassessable_lines():
    con = _wh([
        {"amount_cents": 12_300_000, "quantity": 1000},                               # R123/l: flag, high
        {"amount_cents": 2_600_000, "quantity": 1000, "supplier_key": "B"},          # R26/l: within 20%
        {"amount_cents": 12_300_000, "quantity": 1000, "unit": None, "supplier_key": "C"},       # no unit: unknown
        {"amount_cents": 12_300_000, "quantity": 1000, "financial_year": "2019/20", "supplier_key": "D"},  # no benchmark
        {"amount_cents": None, "quantity": 1000, "supplier_key": "E"},               # no amount: unknown
        {"amount_cents": 3_100_000, "quantity": 1000, "payment_date": date(2024, 6, 3), "financial_year": None,
         "item_description": "Unleaded petrol 95", "commodity_code": None, "commodity_title": None, "supplier_key": "F"},
    ])
    flags = detectors.d13_fuel_unit_price(con, D13)
    assert len(flags) == 2
    hi = next(f for f in flags if f["severity"] == "high")
    assert hi["names_supplier"] and hi["review_status"] == "pending human review" and hi["publish_status"] == "not published"
    assert "R123.00/litre" in hi["title"] and "R24.00/litre" in hi["title"] and hi["score"] == pytest.approx(5.12, 0.01)
    petrol = next(f for f in flags if f["period_label"] == "2024-06")
    assert petrol["severity"] == "med" and "petrol" in petrol["title"]


def test_d13_is_never_published_even_when_confirmed(paths, svc, monkeypatch):
    from thusa import publish
    from tests.conftest import flag_of
    d1 = flag_of(svc, "D1")
    svc.decide(d1["flag_id"], svc.store.get_reviewer("alice"), "confirm", "Confirmed against the AFS", None, "web")
    confirmed, _, _ = publish.public_flags(paths, {"unconfirmed": "exclude", "never_publish": [d1["detector_id"]]})
    assert d1["flag_id"] not in {f["flag_id"] for f in confirmed}
    assert "D13_fuel_unit_price" in load_yaml("publication.yaml")["flags"]["never_publish"]
    assert D13["never_publish"] is True and D13["publish_requires_review"] is True
