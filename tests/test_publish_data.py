"""Public data export (pf publish-data): only confirmed flags, no PII, schema, money, size budget (CHG-2026-006)."""
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from tests.conftest import flag_of
from tests.synth import fuel_docx, oecd_cpi_csv
from thusa import parsers
from thusa import publish_data as pdx
from thusa.settings import REPO_ROOT, load_yaml

REQUIRED = {
    "manifest.json": {"schema", "schema_version", "generated_at_sast", "build", "files", "counts", "coverage",
                      "sources", "known_gaps", "known_errors", "population", "disclaimers", "freshness_slo"},
    "municipalities.json": {"schema", "money_unit", "sources", "municipalities", "audit_opinions", "report_prefix"},
    "departments.json": {"schema", "money_unit", "sources", "departments"},
    "coverage.json": {"schema", "years", "data_types", "states", "reasons", "headline", "entities"},
    "tenders-summary.json": {"schema", "money_unit", "award_files", "all_years", "buyers", "sources"},
    "flags.json": {"schema", "policy", "disclaimer", "detectors", "confirmed", "hidden_leads"},
    "prices.json": {"schema", "fuel", "cpi", "sources"},
}


def _export(paths, tmp_path):
    out = tmp_path / "pd"
    res = pdx.export(paths, out)
    files = {p.name: json.loads(p.read_text()) for p in out.glob("*.json")}
    blob = "\n".join(p.read_text() for p in out.glob("*.json"))
    return res, files, blob, out


def _schema_ok(files: dict) -> None:
    for name, keys in REQUIRED.items():
        assert name in files, name
        assert keys <= set(files[name]), (name, keys - set(files[name]))
        assert files[name]["schema"] == pdx.SCHEMA
    awards = [n for n in files if n.startswith("awards-")]
    assert set(files["tenders-summary.json"]["award_files"].values()) == set(awards)
    for n in awards:
        cols = files[n]["columns"]
        assert all(len(r) == len(cols) for r in files[n]["rows"])
        for r in files[n]["rows"]:
            assert r[-1] in files[n]["sources"]                        # every award row points at its source file


def _money_values(files):
    for m in files["municipalities.json"]["municipalities"]:
        for y in m["years"].values():
            for k in ("budget", "adjusted", "audited"):
                if k in y:
                    yield y[k]["rev"]; yield y[k]["exp"]
            for k, v in y.get("uifw", {}).items():
                if k != "src":
                    yield v
    for d in files["departments.json"]["departments"]:
        for y in d["years"].values():
            for k, v in y.items():
                if isinstance(v, dict):
                    yield v["amount"]
    for b in files["tenders-summary.json"]["buyers"]:
        for v in b["years"].values():
            yield v["known_value"]


def test_schema_manifest_and_checksums(paths, svc, tmp_path):
    res, files, _, out = _export(paths, tmp_path)
    _schema_ok(files)
    man = files["manifest.json"]
    listed = {f["name"]: f for f in man["files"]}
    assert set(listed) == set(files) - {"manifest.json"}
    for name, f in listed.items():
        b = (out / name).read_bytes()
        assert f["bytes"] == len(b) and f["sha256"] == hashlib.sha256(b).hexdigest()
    assert man["population"]["status"] == "unknown"
    assert files["prices.json"]["fuel"]["rows"] and files["prices.json"]["cpi"]["rows"]
    assert files["prices.json"]["cpi"]["last_period"] == "2024-12"     # blank 2025-01 value skipped, not zeroed


def test_money_is_integer_cents_or_unknown(paths, svc, tmp_path):
    _, files, _, _ = _export(paths, tmp_path)
    vals = list(_money_values(files))
    assert vals and all(v is None or (isinstance(v, int) and not isinstance(v, bool)) for v in vals)


def test_no_unconfirmed_flag_leaks(paths, svc, tmp_path):
    d1, d3 = flag_of(svc, "D1"), flag_of(svc, "D3")
    a = svc.store.get_reviewer("alice")
    svc.decide(d3["flag_id"], a, "confirm", "Register and award match", "secret reviewer note", "web")
    _, files, blob, _ = _export(paths, tmp_path)
    assert files["flags.json"]["confirmed"] == []                       # D3 names a supplier: needs four eyes
    for f in svc.wh.flags():
        assert f["flag_id"] not in blob and f["title"] not in blob
    hidden = files["flags.json"]["hidden_leads"]
    assert hidden["total"] == len(svc.wh.flags())
    assert hidden["by_detector"][d3["detector_id"]]["awaiting_second_review"] == 1
    svc.decide(d1["flag_id"], a, "confirm", "Overspend confirmed against the AFS", "another private note", "web")
    _, files, blob, _ = _export(paths, tmp_path)
    assert [f["flag_id"] for f in files["flags.json"]["confirmed"]] == [d1["flag_id"]]
    assert files["flags.json"]["hidden_leads"]["total"] == len(svc.wh.flags()) - 1
    assert d3["flag_id"] not in blob


def test_no_pii_or_review_secrets(paths, svc, tmp_path):
    d1 = flag_of(svc, "D1")
    svc.decide(d1["flag_id"], svc.store.get_reviewer("alice"), "confirm", "Overspend confirmed against the AFS",
               "private note xyz", "web")
    _, files, blob, _ = _export(paths, tmp_path)
    low = blob.lower()
    for s in ("alice", "bob", "root admin", "private note xyz", "password", "token", "8001015009087", "doe, jane",
              "jane doe"):
        assert s not in low, s
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    hashes = [r[0] for r in con.execute("SELECT person_id_hmac FROM curated.restriction WHERE person_id_hmac IS NOT NULL").fetchall()]
    con.close()
    assert hashes and not any(h in blob for h in hashes)
    assert not pdx.looks_like_sa_id(blob)


def test_restricted_person_supplier_names_are_withheld(paths):
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    refs = pdx.SourceRefs(con)
    _, files = pdx.tenders(con, refs, {"acme builders"})
    con.close()
    rows = [r for f in files.values() for r in f["rows"]]
    assert any(r[5] == "(name withheld)" for r in rows) and not any(r[5] == "Acme Builders" for r in rows)


def test_safety_scan_refuses_unsafe_payloads():
    with pytest.raises(pdx.UnsafeExport):
        pdx.assert_public_safe({"x": [{"reviewer": "alice"}]})
    with pytest.raises(pdx.UnsafeExport):
        pdx.assert_public_safe({"t": "Supplier 8001015009087 awarded"})
    with pytest.raises(pdx.UnsafeExport):
        pdx.assert_public_safe({"h": "a" * 64})
    with pytest.raises(pdx.UnsafeExport):
        pdx.assert_public_safe({"s": "Jane Doe"}, {"jane doe"})
    pdx.assert_public_safe({"sha256": "a" * 64, "ref": "2023022107011", "n": 1234567890123})
    assert pdx.scrub("ID 8001015009087 here") == "ID [number removed] here"
    assert pdx.scrub("ref 2023022107011") == "ref 2023022107011"         # not a valid SA ID (Luhn) -> kept


def test_quality_gate_and_size_budget(paths, svc, tmp_path, monkeypatch):
    orig = pdx.load_yaml
    monkeypatch.setattr(pdx, "load_yaml", lambda n: {**orig(n), "size_budget_bytes": 1000} if n == "public-data.yaml" else orig(n))
    with pytest.raises(pdx.UnsafeExport, match="size budget"):
        pdx.export(paths, tmp_path / "small")
    assert not (tmp_path / "small").exists()                            # nothing written on refusal
    monkeypatch.setattr(pdx, "load_yaml", orig)
    con = duckdb.connect(str(paths.warehouse))
    summary = json.loads(con.execute("SELECT summary FROM ops.build").fetchone()[0])
    bad = {**summary, "dq": {**summary["dq"], "fail": [{"test_name": "x"}]}}
    con.execute("UPDATE ops.build SET summary = ?::JSON", [json.dumps(bad)])
    con.close()
    try:
        with pytest.raises(pdx.UnsafeExport, match="quality gate"):
            pdx.export(paths, tmp_path / "gate")
    finally:
        con = duckdb.connect(str(paths.warehouse))
        con.execute("UPDATE ops.build SET summary = ?::JSON", [json.dumps(summary)])
        con.close()


def test_fuel_and_cpi_parsers():
    rows = parsers.fuel_history_rows(fuel_docx(), "t.docx")
    assert len(rows) == 14 and {r["month"] for r in rows} == {1, 2}      # blank March skipped, never zeroed
    assert rows[0] == {"year": 2026, "month": 1, "grade": "petrol_93_inland", "grade_label": "Petrol 93, inland",
                       "cents_per_litre": 2064.0, "source_locator": "t.docx#table-row5"}
    with pytest.raises(ValueError, match="layout"):
        parsers.fuel_history_rows(fuel_docx(first_grade="Inland91"), "bad.docx")
    cpi = parsers.oecd_cpi_rows(oecd_cpi_csv())
    assert len(cpi) == 12 and cpi[0]["index_value"] == 150.1


def test_fuel_page_parser():
    from thusa.connectors.prices import fuel_documents
    html = ('<h4>Fuel Price Adjustment Documents – October 2026 (ZIP)</h4><a href="https://bit.ly/x">View</a>'
            '<h4>Basic Fuel Price July 2026</h4><a href="/a?b=1">View</a>'
            '<h4>History of Fuel Prices July 2026</h4><a href="/API/DownloadFile?ItemId=3450&amp;x=1">View</a>')
    assert fuel_documents(html) == [("Fuel Price Adjustment Documents – October 2026 (ZIP)", "https://bit.ly/x"),
                                    ("History of Fuel Prices July 2026",
                                     "https://www.dmpr.gov.za/API/DownloadFile?ItemId=3450&x=1")]


COMMITTED = REPO_ROOT / "public-data" / "v1"


@pytest.mark.skipif(not (COMMITTED / "manifest.json").exists(), reason="no committed public data")
def test_committed_public_data_is_consistent_safe_and_within_budget():
    cfg = load_yaml("public-data.yaml")
    files = {p.name: json.loads(p.read_text()) for p in COMMITTED.glob("*.json")}
    _schema_ok(files)
    total = sum(p.stat().st_size for p in COMMITTED.glob("*.json"))
    assert total <= cfg["size_budget_bytes"]
    assert all(p.stat().st_size <= cfg["file_budget_bytes"] for p in COMMITTED.glob("*.json"))
    for f in files["manifest.json"]["files"]:
        assert hashlib.sha256((COMMITTED / f["name"]).read_bytes()).hexdigest() == f["sha256"], f["name"]
    for name, obj in files.items():
        pdx.assert_public_safe(obj, path=name)
    fl = files["flags.json"]
    assert fl["policy"]["unconfirmed"].startswith("never exported")
    assert all(set(f) <= {"flag_id", "detector_id", "detector_version", "severity", "title", "explanation",
                          "gov_body_id", "body_name", "period_label", "confirmed_at_sast", "review_reason",
                          "evidence_urls"} for f in fl["confirmed"])
    assert not list(Path(COMMITTED).glob("*.part"))
