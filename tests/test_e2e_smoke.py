"""End-to-end smoke test on synthetic raw files: raw -> staging -> curated -> coverage -> flags -> DQ -> report."""
import json
from datetime import date

import duckdb
import pytest

from tests.synth import build_raw
from thusa.build import build
from thusa.report import render
from thusa.settings import get_paths

SMALL = {"curated.gov_body": 3, "curated.muni_fin_line": 10, "curated.award": 100, "curated.restriction": 2,
         "marts.coverage_cell": 10}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("e2e")
    build_raw(root)
    paths = get_paths(root)
    summary = build(paths, as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL,
                    secret=b"test-secret")
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    yield paths, summary, con
    con.close()


def test_dq_all_pass(built):
    _, s, _ = built
    assert s["dq"]["fail"] == [], s["dq"]["fail"]


def test_unknown_stays_null(built):
    _, _, con = built
    assert con.execute("SELECT count(*) FROM curated.muni_fin_line WHERE item_code='3600' AND amount_cents IS NULL").fetchone()[0] > 0
    assert con.execute("SELECT count(*) FROM curated.muni_fin_line WHERE item_code='3600' AND amount_cents = 0").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM curated.award WHERE value_cents = 0").fetchone()[0] == 0
    # sentinel '9,99999E+99' main appropriation -> unknown line, not a number
    assert con.execute("SELECT n_unknown_lines FROM curated.nat_budget_line WHERE budget_phase='Main appropriation'").fetchone()[0] == 1


def test_coverage_states(built):
    _, _, con = built
    st = dict(con.execute("""SELECT data_type || ':' || fye, state FROM marts.coverage_cell
                             WHERE gov_body_id = 'MUN:TST'""").fetchall())
    assert st["budget:2023"] == "present"
    assert st["audit_opinion:2023"] == "present"
    assert st["audit_opinion:2024"] == "partial"           # outstanding
    assert st["actual_audited:2026"] == "n.a."             # audit not yet due on 2026-10-19
    assert st["budget:2025"] == "missing"
    assert st["procurement:2024"] == "present" or st["procurement:2024"] == "partial"
    # disestablished municipality is n.a. throughout
    assert {s for (s,) in con.execute("SELECT DISTINCT state FROM marts.coverage_cell WHERE gov_body_id='MUN:OLD'").fetchall()} == {"n.a."}


def test_detectors_fire_on_planted_cases(built):
    _, s, con = built
    flags = {d: n for d, n in s["flags"].items()}
    assert flags["D1_overspend_vs_budget"] >= 2              # TST 2024 municipal + test department national
    assert flags["D3_restricted_supplier_awarded"] == 1      # BADCO awarded inside restriction window
    assert flags["D8_irregular_expenditure_trend"] >= 1      # 8m -> 20m -> 50m
    d3 = con.execute("SELECT review_status, publish_status, names_supplier FROM marts.flag WHERE detector_id LIKE 'D3%'").fetchone()
    assert d3 == ("pending human review", "not published", True)
    ev = json.loads(con.execute("SELECT evidence_json FROM marts.flag WHERE detector_id LIKE 'D3%'").fetchone()[0])
    assert any(e.get("url") for e in ev)


def test_lineage_on_every_curated_row(built):
    _, _, con = built
    for t in ("muni_fin_line", "muni_total", "uifw_line", "audit_outcome", "award", "restriction", "nat_budget_line"):
        assert con.execute(f"SELECT count(*) FROM curated.{t} WHERE source_sha256 IS NULL OR fetched_at_utc IS NULL "
                           f"OR source_file IS NULL").fetchone()[0] == 0


def test_no_raw_id_numbers_anywhere(built):
    _, _, con = built
    for (t,) in con.execute("SELECT table_schema || '.' || table_name FROM information_schema.tables "
                            "WHERE table_schema IN ('staging','curated','marts')").fetchall():
        cols = [c for (c, ty) in con.execute(f"SELECT column_name, data_type FROM information_schema.columns "
                                             f"WHERE table_schema || '.' || table_name = '{t}'").fetchall() if ty == "VARCHAR"]
        for c in cols:
            assert con.execute(f"SELECT count(*) FROM {t} WHERE {c} LIKE '%8001015009087%'").fetchone()[0] == 0, (t, c)


def test_rebuild_is_idempotent(built):
    paths, s, _ = built
    again = build(paths, as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL, secret=b"test-secret")
    assert again["rows"] == s["rows"] and again["flags"] == s["flags"]


def test_report_renders(built):
    paths, _, _ = built
    out = render(paths, screenshot=False)
    assert (paths.dist / "site" / "index.html").exists()
    assert all((paths.dist / p.split("/")[-1]).exists() for p in out["pngs"])
    html = (paths.dist / "site" / "index.html").read_text()
    assert "unreviewed" in html and "DOE, JANE" not in html
