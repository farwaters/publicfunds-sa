"""CSI-028 / CHG-2026-017: known unknowns v2 (trend per year, per-municipality ranking) from coverage.json only."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/public-dashboard/index.html"
COV = ROOT / "public-data/v1/coverage.json"


def _view():
    html = APP.read_text()
    return html[html.index("async function vUnknowns()"):html.index("/* ---------------------------------------------------------------- what's new")]


def test_view_has_trend_and_ranking_tables_with_csv():
    v = _view()
    assert "known-unknowns-by-year.csv" in v and "known-unknowns-by-municipality.csv" in v
    assert "Trend over time" in v and "Municipalities with the most missing data" in v
    assert 'href: `#/m/${r.id}`' in v


def test_view_reads_only_coverage_and_municipalities():
    loads = set(re.findall(r'load\("([^"]+)"\)', _view()))
    assert loads == {"coverage.json", "municipalities.json"}       # no flags, no AGSA annexures


def test_ranking_counts_reconcile_with_published_by_type_headline():
    """The page's counting rule (skip '-' and '?', years fye_min..fye_max) reproduces the exporter's by_type totals."""
    cov = json.loads(COV.read_text())
    h = cov["headline"]
    ks = [k for k, y in enumerate(cov["years"]) if h["fye_min"] <= y <= h["fye_max"]]
    for dt in cov["data_types"]:
        c = {"P": 0, "p": 0, "m": 0}
        for e in cov["entities"]:
            for k in ks:
                st = e["c"][dt][k]
                if st not in "-?":
                    c[st] += 1
        bt = h["by_type"][dt]
        assert (c["P"], c["p"], c["m"]) == (bt["present"], bt["partial"], bt["missing"]), dt
