"""Unit tests: review decision rules and the four-eyes rule (pure functions, no I/O)."""
import pytest

from thusa.review import workflow as wf


def dec(user, decision, new_status, h="h1"):
    return {"reviewer_username": user, "decision": decision, "new_status": new_status, "evidence_hash": h}


def step(log, user, decision, named=True, h="h1", role="reviewer"):
    st = wf.replay(log, named)
    new = wf.next_status(st, decision, user, role, named, h)
    log.append(dec(user, decision, new, h))
    return new


def test_initial_status_depends_on_naming():
    assert wf.replay([], True).status == "pending human review"
    assert wf.replay([], False).status == "unreviewed"


def test_unnamed_flag_needs_one_confirmation():
    assert step([], "alice", "confirm", named=False) == "confirmed"


def test_named_flag_needs_two_different_reviewers():
    log = []
    assert step(log, "alice", "confirm") == wf.AWAITING
    with pytest.raises(wf.FourEyesError):
        step(log, "alice", "confirm")
    assert step(log, "bob", "confirm") == "confirmed"
    assert wf.replay(log, True).confirmers_on("h1") == ["alice", "bob"]


def test_non_confirm_decision_restarts_the_round():
    log = []
    step(log, "alice", "confirm")
    assert step(log, "bob", "needs_info") == "needs more info"
    assert step(log, "bob", "confirm") == wf.AWAITING        # alice's earlier confirm no longer counts
    assert step(log, "alice", "confirm") == "confirmed"


def test_confirmations_must_be_on_the_same_evidence():
    log = []
    step(log, "alice", "confirm", h="h1")
    assert step(log, "bob", "confirm", h="h2") == wf.AWAITING  # evidence changed between the two reviews
    assert wf.is_stale(wf.replay(log, True), "h3")


def test_already_confirmed_cannot_be_confirmed_again_unless_evidence_changed():
    log = []
    step(log, "alice", "confirm", named=False)
    with pytest.raises(wf.FourEyesError):
        step(log, "bob", "confirm", named=False)
    assert step(log, "bob", "confirm", named=False, h="h2") == "confirmed"


def test_escalated_flag_only_admin_may_confirm_or_reject():
    log = []
    assert step(log, "alice", "escalate") == "escalated"
    with pytest.raises(wf.FourEyesError):
        step(log, "bob", "confirm")
    with pytest.raises(wf.FourEyesError):
        step(log, "bob", "reject")
    assert step(log, "bob", "needs_info") == "needs more info"
    step(log, "alice", "escalate")
    assert step(log, "root", "confirm", role="admin") == wf.AWAITING   # admin still counts as ONE reviewer


def test_reject_is_allowed_by_one_reviewer():
    assert step([], "alice", "reject") == "rejected"


def test_unknown_decision_rejected():
    with pytest.raises(wf.ReviewError):
        wf.next_status(wf.replay([], True), "approve", "alice", "reviewer", True, "h")


@pytest.mark.parametrize("reason,notes", [("", None), ("too short", None), ("x" * 2001, None),
                                          ("long enough reason", "n" * 4001), ("bad \x00 control char", None)])
def test_reason_and_notes_validation(reason, notes):
    with pytest.raises(wf.ReviewError):
        wf.validate_text(reason, notes)


def test_reason_trimmed_and_empty_notes_become_null():
    assert wf.validate_text("  a valid reason  ", "   ") == ("a valid reason", None)


def test_evidence_hash_is_deterministic_and_sensitive():
    f = {"flag_id": "a" * 16, "detector_id": "D1", "detector_version": "1", "severity": "high", "score": 1.0,
         "title": "t", "explanation": "e", "names_supplier": False, "evidence_json": '[{"url": "https://x"}]'}
    assert wf.evidence_hash(f) == wf.evidence_hash(dict(f, evidence_json=[{"url": "https://x"}]))
    assert wf.evidence_hash(f) != wf.evidence_hash(dict(f, score=1.01))
