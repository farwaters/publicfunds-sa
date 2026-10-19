"""Data-quality suite against the REAL warehouse built by `thusa run` (skipped if it has not been built)."""
import duckdb
import pytest

from thusa import dq
from thusa.settings import get_paths

P = get_paths()
pytestmark = pytest.mark.skipif(not P.warehouse.exists(), reason="warehouse not built; run `uv run thusa run`")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(P.warehouse), read_only=True)
    yield c
    c.close()


@pytest.mark.parametrize("name,severity,sql", dq.checks(), ids=[c[0] for c in dq.checks()])
def test_dq_check(con, name, severity, sql):
    failures = con.execute(sql).fetchone()[0]
    if severity == "error":
        assert failures == 0, f"{name}: {failures} failing rows"


def test_raw_checksums_match(con):
    from thusa.raw import sha256_file
    for path, sha in con.execute("SELECT path, sha256 FROM ops.raw_file").fetchall():
        assert sha256_file(P.root / path) == sha, path


def test_every_source_has_a_run_record(con):
    got = {s for (s,) in con.execute("SELECT DISTINCT source_id FROM ops.ingest_run").fetchall()}
    assert {"muni_api", "etenders_ocds", "rsr", "ppd_payments", "nt_budget"} <= got


def test_all_munis_in_grid(con):
    assert con.execute("SELECT count(DISTINCT gov_body_id) FROM marts.coverage_entity_year WHERE core_state <> 'n.a.'").fetchone()[0] == 257
