"""CHG-2026-035: read-only month-continuity check of the fuel price history (pure function, DQ warn check, CLI report)."""
import importlib.util
from pathlib import Path

import duckdb
import pytest

from thusa import dq

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fuel_continuity.py"


def _cli():
    spec = importlib.util.spec_from_file_location("fuel_continuity_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _months(first, last, skip=()):
    y, m = first
    while (y, m) <= last:
        if (y, m) not in skip:
            yield (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _con(months):
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA ops")
    con.execute("CREATE SCHEMA curated")
    con.execute("CREATE TABLE curated.fuel_price (year INTEGER, month INTEGER, grade VARCHAR)")
    for y, m in months:
        for g in ("a", "b"):  # several grades per month: the month counts once
            con.execute("INSERT INTO curated.fuel_price VALUES (?,?,?)", [y, m, g])
    return con


# --- pure function -----------------------------------------------------------------------------------------------
def test_no_gap_when_months_are_contiguous():
    r = dq.month_gaps(_months((2019, 1), (2026, 10)), {})
    assert r["missing"] == [] and r["new"] == [] and r["expected"] == []
    assert r["first"] == (2019, 1) and r["last"] == (2026, 10) and r["present"] == 94


def test_one_missing_month_is_found_and_is_new():
    r = dq.month_gaps(_months((2019, 1), (2026, 10), skip={(2025, 12)}), {})
    assert r["missing"] == [(2025, 12)] and r["new"] == [(2025, 12)] and r["expected"] == []
    assert r["present"] == 93


def test_gap_across_a_year_boundary():
    r = dq.month_gaps([(2025, 11), (2026, 2)], {})
    assert r["missing"] == [(2025, 12), (2026, 1)]


def test_gap_in_january_and_december_only():
    r = dq.month_gaps(_months((2020, 1), (2022, 12), skip={(2021, 1), (2021, 12)}), {})
    assert r["missing"] == [(2021, 1), (2021, 12)]


def test_known_gap_is_expected_not_new():
    known = {(2024, 5): "KE-000: test reason"}
    r = dq.month_gaps(_months((2024, 1), (2024, 9), skip={(2024, 5), (2024, 7)}), known)
    assert r["expected"] == [(2024, 5)] and r["new"] == [(2024, 7)] and r["missing"] == [(2024, 5), (2024, 7)]


def test_known_gap_list_is_the_argument_not_a_constant():
    for month in ((2019, 3), (2022, 8), (2025, 12)):
        r = dq.month_gaps(_months((2019, 1), (2026, 1), skip={month}), {month: "KE-000: test"})
        assert r["expected"] == [month] and r["new"] == []
        r = dq.month_gaps(_months((2019, 1), (2026, 1), skip={month}), {})
        assert r["new"] == [month] and r["expected"] == []


def test_known_month_that_is_present_is_reported_stale():
    r = dq.month_gaps(_months((2024, 1), (2024, 4)), {(2024, 2): "KE-000: test"})
    assert r["stale_known"] == [(2024, 2)] and r["missing"] == [] and r["expected"] == []


def test_known_month_outside_the_range_is_neither_gap_nor_stale():
    r = dq.month_gaps(_months((2019, 1), (2019, 6)), {(2018, 5): "KE-000: before history", (2020, 1): "KE-000: after"})
    assert r["missing"] == [] and r["stale_known"] == [] and r["new"] == [] and r["expected"] == []


def test_the_range_ends_are_the_data_not_a_fixed_window():
    r = dq.month_gaps([(2023, 3), (2023, 5)], {})
    assert r["first"] == (2023, 3) and r["last"] == (2023, 5) and r["missing"] == [(2023, 4)]


def test_empty_and_single_month():
    assert dq.month_gaps([], {})["first"] is None and dq.month_gaps([], {})["new"] == []
    r = dq.month_gaps([(2024, 6)], {})
    assert r["first"] == r["last"] == (2024, 6) and r["missing"] == [] and r["present"] == 1


def test_duplicates_and_order_do_not_matter():
    r = dq.month_gaps([(2024, 3), (2024, 1), (2024, 1), (2024, 4)], {})
    assert r["missing"] == [(2024, 2)] and r["present"] == 3


@pytest.mark.parametrize("bad", [(2024, 0), (2024, 13), (2024, None), (None, 5)])
def test_invalid_month_raises_instead_of_passing(bad):
    with pytest.raises(ValueError):
        dq.month_gaps([(2024, 1), bad], {})


def test_repository_allow_list_is_pinned_empty():
    """No fuel month is a known gap (KE-012). Adding one is a deliberate change that needs an RFC row and this test edited."""
    assert dq.FUEL_KNOWN_GAPS == {}
    for ym, reason in dq.FUEL_KNOWN_GAPS.items():
        assert reason.startswith("KE-")


# --- warehouse check ---------------------------------------------------------------------------------------------
def test_fuel_continuity_reads_distinct_months_from_the_warehouse():
    con = _con(_months((2019, 1), (2019, 12), skip={(2019, 7)}))
    r = dq.fuel_continuity(con)
    assert r["new"] == [(2019, 7)] and r["present"] == 11


def test_fuel_continuity_uses_the_module_allow_list(monkeypatch):
    con = _con(_months((2019, 1), (2019, 12), skip={(2019, 7)}))
    monkeypatch.setattr(dq, "FUEL_KNOWN_GAPS", {(2019, 7): "KE-000: test"})
    r = dq.fuel_continuity(con)
    assert r["expected"] == [(2019, 7)] and r["new"] == []


def _result(con):
    return next(r for r in dq.run(con, "t") if r["test_name"] == "fuel_month_continuity_info")


def test_dq_run_warns_on_a_new_gap_and_never_fails():
    r = _result(_con(_months((2019, 1), (2019, 12), skip={(2019, 7)})))
    assert r["severity"] == "warn" and r["status"] == "warn" and r["failures"] == 1


def test_dq_run_passes_when_contiguous():
    r = _result(_con(_months((2019, 1), (2019, 12))))
    assert r["status"] == "pass" and r["failures"] == 0 and r["severity"] == "warn"


def test_dq_run_passes_when_the_gap_is_a_known_one(monkeypatch):
    monkeypatch.setattr(dq, "FUEL_KNOWN_GAPS", {(2019, 7): "KE-000: test"})
    assert _result(_con(_months((2019, 1), (2019, 12), skip={(2019, 7)})))["status"] == "pass"


def test_dq_run_warns_on_a_stale_allow_list_entry(monkeypatch):
    monkeypatch.setattr(dq, "FUEL_KNOWN_GAPS", {(2019, 7): "KE-000: test"})
    assert _result(_con(_months((2019, 1), (2019, 12))))["status"] == "warn"


def test_dq_run_error_status_when_the_table_is_unreadable():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA ops")
    assert _result(con)["status"].startswith("error")


def test_the_check_is_not_among_the_sql_error_checks():
    assert "fuel_month_continuity_info" not in [c[0] for c in dq.checks()]


def test_synthetic_build_has_the_check_and_it_does_not_fail_the_build(synth_root):
    con = duckdb.connect(str(synth_root / "data" / "thusa.duckdb"), read_only=True)
    try:
        sev, st = con.execute("SELECT severity, status FROM ops.dq_result WHERE test_name = 'fuel_month_continuity_info'").fetchone()
    finally:
        con.close()
    assert sev == "warn" and st in ("pass", "warn")


def test_dq_run_malformed_months_become_error_status():
    # NULL month: int(None) raises TypeError; month 13: month_gaps raises ValueError. Both fail closed (status "error").
    for bad in (None, 13):
        con = _con([])
        con.execute("INSERT INTO curated.fuel_price VALUES (2019, ?, 'a')", [bad])
        r = _result(con)
        assert r["severity"] == "warn" and r["status"].startswith("error") and r["failures"] == -1, bad


def test_dq_run_empty_fuel_table_passes_silently():
    # 0 months is not a gap here; only the existing min-rows checks guard an empty table.
    r = _result(_con([]))
    assert r["status"] == "pass" and r["failures"] == 0


def test_a_crash_in_the_check_lands_in_the_build_fail_list_and_blocks_the_publish(tmp_path, monkeypatch):
    # fail-closed by design: a broken check is a failure like every other broken check (build.py takes any status
    # that is not pass or warn), the build is not releasable, and the publish export refuses to run
    from datetime import date

    from tests.conftest import SMALL
    from tests.synth import build_raw
    from thusa import publish_data as pdx
    from thusa.build import build
    from thusa.settings import get_paths

    def boom(con, known=None):
        raise RuntimeError("simulated crash in the fuel check")

    monkeypatch.setattr(dq, "fuel_continuity", boom)
    build_raw(tmp_path)
    summary = build(get_paths(tmp_path), as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL,
                    secret=b"test-secret")
    fails = [r["test_name"] for r in summary["dq"]["fail"]]
    assert fails == ["fuel_month_continuity_info"]
    assert summary["dq"]["fail"][0]["status"].startswith("error")
    with pytest.raises(pdx.UnsafeExport, match="quality gate"):
        pdx.export(get_paths(tmp_path), tmp_path / "out")


# --- CLI report --------------------------------------------------------------------------------------------------
def _wh(tmp_path, months):
    p = tmp_path / "wh.duckdb"
    con = duckdb.connect(str(p))
    con.execute("CREATE SCHEMA curated")
    con.execute("CREATE TABLE curated.fuel_price (year INTEGER, month INTEGER, grade VARCHAR)")
    for y, m in months:
        con.execute("INSERT INTO curated.fuel_price VALUES (?,?,'a')", [y, m])
    con.close()
    return str(p)


def test_cli_reports_a_new_gap_and_exits_1(tmp_path, capsys):
    rc = _cli().main(["--warehouse", _wh(tmp_path, _months((2025, 10), (2026, 2), skip={(2025, 12)}))])
    out = capsys.readouterr().out
    assert rc == 1 and "NEW gap: 2025-12" in out and "fuel months: 2025-10 to 2026-02, 4 present, 1 missing" in out


def test_cli_ok_when_contiguous(tmp_path, capsys):
    rc = _cli().main(["--warehouse", _wh(tmp_path, _months((2019, 1), (2019, 12)))])
    out = capsys.readouterr().out
    assert rc == 0 and "fuel continuity: OK" in out and "NEW" not in out


def test_cli_separates_expected_from_new(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(dq, "FUEL_KNOWN_GAPS", {(2019, 3): "KE-000: test reason"})
    rc = _cli().main(["--warehouse", _wh(tmp_path, _months((2019, 1), (2019, 8), skip={(2019, 3), (2019, 6)}))])
    out = capsys.readouterr().out
    assert rc == 1 and "expected known gap: 2019-03 (KE-000: test reason)" in out and "NEW gap: 2019-06" in out
    assert "NEW gap: 2019-03" not in out


def test_cli_opens_the_warehouse_read_only(tmp_path, monkeypatch):
    p = _wh(tmp_path, _months((2019, 1), (2019, 3)))
    cli, real, seen = _cli(), duckdb.connect, []

    def spy(*a, **kw):
        seen.append(kw.get("read_only"))
        return real(*a, **kw)

    monkeypatch.setattr(cli.duckdb, "connect", spy)
    cli.main(["--warehouse", p])
    assert seen == [True]
