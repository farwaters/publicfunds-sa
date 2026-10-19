"""Public snapshot: only confirmed flags are published; named-supplier flags never appear unconfirmed."""
import json

from tests.conftest import flag_of
from thusa.publish import render_public


def _pub(paths, mode="exclude"):
    out = render_public(paths, {"unconfirmed": mode, "show_review_reason": True})
    data = json.loads((paths.dist / "public" / "flags.json").read_text())
    html = (paths.dist / "public" / "index.html").read_text()
    return out, data, html


def test_nothing_published_before_review(paths, svc):
    out, data, html = _pub(paths)
    assert out["confirmed"] == 0 and out["leads"] == 0 and data["flags"] == []
    assert "BADCO" not in html and "No flags have been confirmed" in html


def test_confirmed_flags_published_named_only_after_four_eyes(paths, svc):
    d1, d3 = flag_of(svc, "D1"), flag_of(svc, "D3")
    a, b = svc.store.get_reviewer("alice"), svc.store.get_reviewer("bob")
    svc.decide(d1["flag_id"], a, "confirm", "Overspend confirmed against the AFS", "private note", "web")
    svc.decide(d3["flag_id"], a, "confirm", "Register and award match", None, "web")
    _, data, html = _pub(paths)
    ids = {f["flag_id"] for f in data["flags"]}
    assert d1["flag_id"] in ids and d3["flag_id"] not in ids          # D3 has one of two confirmations
    assert "private note" not in html and "alice" not in html          # notes and reviewer names never published
    svc.decide(d3["flag_id"], b, "confirm", "Second reviewer agrees", None, "web")
    _, data, html = _pub(paths)
    assert d3["flag_id"] in {f["flag_id"] for f in data["flags"]} and "Confirmed by review" in html


def test_label_mode_lists_unnamed_leads_but_never_named_ones(paths, svc):
    d1 = [f for f in svc.wh.flags() if f["detector_id"].startswith("D1")]
    svc.decide(d1[0]["flag_id"], svc.store.get_reviewer("alice"), "reject", "Data error in source", None, "web")
    out, data, html = _pub(paths, "label")
    labels = {f["flag_id"]: f["publication_label"] for f in data["flags"]}
    assert flag_of(svc, "D3")["flag_id"] not in labels and "BADCO" not in html
    assert d1[0]["flag_id"] not in labels                               # rejected -> never a lead
    assert out["leads"] >= 1 and set(labels.values()) == {"unreviewed lead - not a finding"}


def test_stale_confirmation_is_not_published(paths, svc):
    d1 = flag_of(svc, "D1")
    svc.store.decide(dict(d1, score=d1["score"] + 1), svc.store.get_reviewer("alice"), "confirm",
                     "Confirmed on older numbers", None, "web", None)
    _, data, _ = _pub(paths)
    assert data["flags"] == [] and svc.get_flag(d1["flag_id"])["evidence_changed"]
