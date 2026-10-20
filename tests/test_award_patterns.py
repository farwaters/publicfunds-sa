"""CHG-2026-010: award-pattern detectors D16 (repeat awards), D17 (just below threshold), D6 (splitting)."""
from datetime import date, timedelta

import duckdb

from thusa import detectors
from thusa.settings import load_yaml

Y = load_yaml("detectors.yaml")
CFG, TH = Y["detectors"], Y["procurement_thresholds"]


def _wh(awards, bodies=(("MUN1", "local"), ("MET1", "metro"), ("DEP1", "department"))):
    con = duckdb.connect()
    con.execute("CREATE SCHEMA curated")
    con.execute("CREATE TABLE curated.gov_body (gov_body_id VARCHAR, body_type VARCHAR)")
    con.executemany("INSERT INTO curated.gov_body VALUES (?, ?)", list(bodies))
    con.execute("""CREATE TABLE curated.award (ocid VARCHAR, award_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR,
        buyer_gov_body_id VARCHAR, supplier_key VARCHAR, supplier_name VARCHAR, n_suppliers INTEGER,
        value_cents BIGINT, value_note VARCHAR, award_date DATE, award_date_basis VARCHAR)""")
    for i, a in enumerate(awards):
        r = {"ocid": f"ocds-{i}", "award_id": "1", "buyer_id": "B1", "buyer_name": "Test LM", "buyer_gov_body_id": "MUN1",
             "supplier_key": "ACME", "supplier_name": "ACME (PTY) LTD", "n_suppliers": 1, "value_cents": None,
             "value_note": None, "award_date": date(2024, 6, 1), "award_date_basis": "contract.dateSigned", **a}
        con.execute("INSERT INTO curated.award VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", list(r.values()))
    return con


def _d(n):
    return date(2024, 6, 1) + timedelta(days=n)


def test_thresholds_match_cited_regulations():
    assert TH["mfma"]["rand"] == {"metro": 750000, "local": 300000, "district": 200000}
    assert str(TH["mfma"]["from"]) == "2023-12-14" and TH["pfma"]["rand"] == {"department": 1000000}
    assert str(TH["pfma"]["from"]) == "2021-08-01"
    for d in ("D6_threshold_splitting", "D16_repeat_awards", "D17_just_below_threshold"):
        assert CFG[d]["never_publish"] and CFG[d]["publish_requires_review"]
        assert d in load_yaml("publication.yaml")["flags"]["never_publish"]


def test_d16_repeat_awards_within_window_only():
    con = _wh([{"value_cents": 10_000_000, "award_date": _d(i * 60)} for i in range(5)]           # 5 in 240 days
              + [{"value_cents": 10_000_000, "award_date": _d(i * 200), "supplier_key": "B"} for i in range(5)]
              + [{"value_cents": None, "award_date": _d(i), "supplier_key": "C"} for i in range(6)])  # unknown values
    f = detectors.d16_repeat_awards(con, CFG["D16_repeat_awards"])
    assert len(f) == 1 and f[0]["subject_id"] == "MUN1|ACME" and f[0]["score"] == 5
    assert f[0]["names_supplier"] and f[0]["review_status"] == "pending human review"
    assert f[0]["publish_status"] == "not published" and len(f[0]["evidence_json"]) > 0


def test_d17_just_below_threshold_by_regime_and_date():
    con = _wh([{"value_cents": 29_500_000, "award_date": _d(0)}, {"value_cents": 29_900_000, "award_date": _d(40)},
               {"value_cents": 30_000_000, "award_date": _d(80)},                       # exactly at R300k: counts
               {"value_cents": 30_000_100, "award_date": _d(90)},                       # above: bid needed, not "under"
               {"value_cents": 29_500_000, "award_date": date(2023, 6, 1), "supplier_key": "OLD"},
               {"value_cents": 29_500_000, "award_date": date(2023, 7, 1), "supplier_key": "OLD"},   # before regs
               {"value_cents": 29_500_000, "buyer_id": "B2", "buyer_gov_body_id": None, "supplier_key": "X"},
               {"value_cents": 29_500_000, "buyer_id": "B2", "buyer_gov_body_id": None, "supplier_key": "X"},  # unknown
               {"value_cents": 74_000_000, "buyer_id": "B3", "buyer_gov_body_id": "MET1", "supplier_key": "M"},
               {"value_cents": 29_500_000, "buyer_id": "B3", "buyer_gov_body_id": "MET1", "supplier_key": "M"}])
    f = detectors.d17_just_below_threshold(con, CFG["D17_just_below_threshold"], TH)
    assert [x["subject_id"] for x in f] == ["MUN1|ACME"]
    assert f[0]["severity"] == "med" and f[0]["score"] == 3 and "R300,000" in f[0]["title"]


def test_d6_splitting_needs_sum_above_threshold_within_window():
    con = _wh([{"value_cents": 20_000_000, "award_date": _d(0)}, {"value_cents": 15_000_000, "award_date": _d(20)},
               {"value_cents": 20_000_000, "award_date": _d(0), "supplier_key": "FAR"},
               {"value_cents": 15_000_000, "award_date": _d(45), "supplier_key": "FAR"},      # outside 30 days
               {"value_cents": 10_000_000, "award_date": _d(0), "supplier_key": "SMALL"},
               {"value_cents": 10_000_000, "award_date": _d(5), "supplier_key": "SMALL"},     # sum R200k < R300k
               {"value_cents": 60_000_000, "award_date": _d(0), "buyer_gov_body_id": "DEP1", "buyer_id": "D",
                "supplier_key": "P"},
               {"value_cents": 50_000_000, "award_date": _d(9), "buyer_gov_body_id": "DEP1", "buyer_id": "D",
                "supplier_key": "P"}])                                                      # PFMA R1m: R1.1m
    f = detectors.d6_threshold_splitting(con, CFG["D6_threshold_splitting"], TH)
    assert sorted(x["subject_id"] for x in f) == ["DEP1|P", "MUN1|ACME"]
    assert all(x["names_supplier"] and x["severity"] == "med" for x in f)
    assert next(x for x in f if x["subject_id"] == "DEP1|P")["score"] == 1.1


def test_never_publish_detectors_are_skipped_even_when_confirmed(paths, svc):
    from thusa import publish
    from tests.conftest import flag_of
    d1 = flag_of(svc, "D1")
    svc.decide(d1["flag_id"], svc.store.get_reviewer("alice"), "confirm", "Confirmed against the AFS", None, "web")
    confirmed, _, _ = publish.public_flags(paths, {"unconfirmed": "exclude", "never_publish": [d1["detector_id"]]})
    assert d1["flag_id"] not in {f["flag_id"] for f in confirmed}
