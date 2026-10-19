"""Review store: append-only audit trail, hash chain, SAST timestamps, survival across warehouse rebuilds."""
import sqlite3
from datetime import date

import duckdb
import pytest

from tests.conftest import SMALL, flag_of
from thusa.build import build
from thusa.review import workflow as wf


def test_decision_record_fields(svc):
    f = flag_of(svc, "D3")
    alice = svc.store.get_reviewer("alice")
    rec = svc.decide(f["flag_id"], alice, "confirm", "Award date inside window; names match", None, "web")
    assert rec["prev_status"] == "pending human review" and rec["new_status"] == wf.AWAITING
    assert rec["decided_at_sast"].endswith("+02:00") and rec["decided_at_utc"].endswith("Z")
    assert rec["reviewer_username"] == "alice" and rec["evidence_hash"] == wf.evidence_hash(f)
    assert svc.store.verify_chain() == {"ok": True, "n": 1, "head": rec["record_hash"]}


@pytest.mark.parametrize("sql", ["UPDATE decision SET reason = 'changed afterwards'", "DELETE FROM decision",
                                 "UPDATE reviewer_event SET actor = 'x'", "DELETE FROM reviewer_event"])
def test_audit_tables_are_append_only(svc, sql):
    f = flag_of(svc, "D1")
    svc.decide(f["flag_id"], svc.store.get_reviewer("alice"), "reject", "Classification difference only", None, "cli")
    con = sqlite3.connect(svc.store.path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute(sql)
    con.close()
    assert len(svc.store.decisions()) == 1


def test_tampering_breaks_the_hash_chain(svc):
    f = flag_of(svc, "D1")
    for who in ("alice", "bob"):
        svc.decide(f["flag_id"], svc.store.get_reviewer(who), "needs_info", f"{who} needs the AFS note", None, "web")
    con = sqlite3.connect(svc.store.path)
    con.execute("DROP TRIGGER decision_no_update")
    con.execute("UPDATE decision SET new_status = 'confirmed' WHERE decision_id = 1")
    con.commit()
    con.close()
    res = svc.store.verify_chain()
    assert res["ok"] is False and res["broken_at_decision_id"] == 1


def test_reviews_survive_a_pipeline_rebuild(svc, paths):
    f = flag_of(svc, "D3")
    svc.decide(f["flag_id"], svc.store.get_reviewer("alice"), "confirm", "Checked the register PDF row", None, "web")
    before = {x["flag_id"] for x in svc.wh.flags()}
    build(paths, as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL, secret=b"test-secret")
    assert {x["flag_id"] for x in svc.wh.flags()} == before           # deterministic flag ids
    g = svc.get_flag(f["flag_id"])
    assert g["status"] == wf.AWAITING and not g["evidence_changed"] and g["confirmed_by"] == ["alice"]


def test_decisions_on_flags_missing_from_the_build_are_kept(svc):
    ghost = {"flag_id": "f" * 16, "detector_id": "D1_x", "detector_version": "1", "severity": "med", "score": 1,
             "title": "gone", "explanation": "e", "evidence_json": "[]", "names_supplier": False}
    svc.store.decide(ghost, svc.store.get_reviewer("bob"), "reject", "Data error in the source", None, "cli", None)
    rows = {r["flag_id"]: r for r in svc.reviewed()}
    assert rows["f" * 16]["in_current_build"] is False and rows["f" * 16]["status"] == "rejected"


def test_inactive_reviewer_cannot_decide(svc):
    svc.store.update_reviewer("bob", "disabled", "test", active=0)
    with pytest.raises(wf.ReviewError):
        svc.decide(flag_of(svc, "D1")["flag_id"], svc.store.get_reviewer("bob"), "reject", "a valid reason", None, "web")


def test_reviewer_events_logged(svc):
    svc.store.update_reviewer("bob", "token_issued", "root", token_hash="0" * 64)
    ev = [(e["username"], e["event"]) for e in svc.store.reviewer_events()]
    assert ("alice", "created") in ev and ("bob", "token_issued") in ev


def test_province_codes_normalised(paths):
    # regression KE-011: the API mixes KZ/KZN and LP/LIM
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    assert con.execute("SELECT province FROM curated.gov_body WHERE demarcation_code = 'OLD'").fetchone()[0] == "KZN"
    con.close()
