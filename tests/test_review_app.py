"""Integration tests for the review web app and JSON API (FastAPI TestClient on the synthetic warehouse)."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import PW, csrf_of, flag_of, login
from thusa.review import security as sec


@pytest.fixture
def client(app):
    return TestClient(app)


def decide(client, fid, decision, reason="Checked against the source documents", csrf=None):
    return client.post(f"/flags/{fid}/decide", data={"decision": decision, "reason": reason, "notes": "",
                                                     "csrf_token": csrf or csrf_of(client)}, follow_redirects=False)


def test_pages_require_login(client):
    for path in ("/flags", "/coverage", "/audit", "/export/reviewed.csv", "/entity/MUN:TST", "/flags/0123456789abcdef"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("/login?next="), path


def test_anonymous_writes_refused(client, svc):
    r = client.post(f"/flags/{flag_of(svc, 'D1')['flag_id']}/decide",
                    data={"decision": "confirm", "reason": "anonymous attempt here", "csrf_token": "x"})
    assert r.status_code == 401 and svc.store.decisions() == []


def test_healthz_and_security_headers(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["audit_chain_ok"] is True
    h = client.get("/login").headers
    assert "frame-ancestors 'none'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer" and h["cache-control"] == "no-store"
    assert "server" not in {k.lower() for k in h} or "uvicorn" not in h.get("server", "")


def test_untrusted_host_rejected(client):
    assert client.get("/healthz", headers={"host": "evil.example"}).status_code == 400


def test_login_success_and_wrong_password(client):
    assert login(client, "alice", "wrong-password-x").status_code == 401
    r = login(client, "alice")
    assert r.status_code == 303 and "pf_session" in r.headers["set-cookie"]
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower()
    assert client.get("/flags").status_code == 200


def test_login_requires_csrf(client):
    client.get("/login")
    r = client.post("/login", data={"username": "alice", "password": PW["alice"], "csrf_token": "forged"})
    assert r.status_code == 403


def test_login_rate_limited(client):
    for _ in range(5):
        assert login(client, "bob", "not-the-password").status_code == 401
    r = login(client, "bob")                       # correct password, but locked for 15 minutes
    assert r.status_code == 429 and r.headers["retry-after"] == "900"


def test_disabled_reviewer_cannot_sign_in_and_session_is_revoked(client, svc):
    assert login(client, "bob").status_code == 303
    svc.store.update_reviewer("bob", "disabled", "test", active=0)
    assert client.get("/flags", follow_redirects=False).status_code == 303
    assert login(client, "bob").status_code == 401


def test_logout_revokes_session(client):
    login(client, "alice")
    r = client.post("/logout", data={"csrf_token": csrf_of(client)}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/flags", follow_redirects=False).status_code == 303


def test_open_redirect_blocked(client):
    client.get("/login")
    r = client.get("/login?next=//evil.example/x")
    assert 'value="/flags"' in r.text


def test_queue_filters_and_htmx_partial(client, svc):
    login(client, "alice")
    r = client.get("/flags?detector=D3_restricted_supplier_awarded")
    assert r.status_code == 200 and "BADCO" in r.text and "four-eyes" in r.text
    p = client.get("/flags?severity=high", headers={"HX-Request": "true"})
    assert p.status_code == 200 and "<html" not in p.text
    assert client.get("/flags?severity=nope").status_code == 422
    assert client.get("/flags?status=pending human review").status_code == 200


def test_flag_detail_shows_evidence_and_match(client, svc):
    login(client, "alice")
    f = flag_of(svc, "D3")
    r = client.get(f"/flags/{f['flag_id']}")
    assert r.status_code == 200
    for s in ("Restricted Supplier register entry", "Confidence", "/lineage/", "Four-eyes", "Award(s) on eTenders"):
        assert s in r.text, s
    assert client.get("/flags/not-a-flag-id").status_code == 404


def test_decision_requires_csrf_and_reason(client, svc):
    login(client, "alice")
    fid = flag_of(svc, "D1")["flag_id"]
    assert decide(client, fid, "confirm", csrf="forged").status_code == 403
    r = decide(client, fid, "confirm", reason="short")
    assert r.status_code == 422 and "reason is required" in r.text.lower()
    assert svc.store.decisions() == []
    assert decide(client, fid, "confirm").status_code == 303
    assert svc.store.decisions()[0]["channel"] == "web"


def test_four_eyes_over_the_web(app, svc):
    fid = flag_of(svc, "D3")["flag_id"]
    a, b = TestClient(app), TestClient(app)
    login(a, "alice"), login(b, "bob")
    assert decide(a, fid, "confirm").status_code == 303
    assert svc.get_flag(fid)["status"] == "awaiting second review"
    r = decide(a, fid, "confirm")
    assert r.status_code == 409 and "Four-eyes" in r.text
    assert decide(b, fid, "confirm").status_code == 303
    g = svc.get_flag(fid)
    assert g["status"] == "confirmed" and g["confirmed_by"] == ["alice", "bob"] and g["publishable"]


def test_user_text_is_escaped(client, svc):
    login(client, "alice")
    fid = flag_of(svc, "D1")["flag_id"]
    decide(client, fid, "needs_info", reason="<script>alert(1)</script> please check")
    r = client.get(f"/flags/{fid}")
    assert "<script>alert(1)</script>" not in r.text and "&lt;script&gt;" in r.text


def test_audit_page_and_exports(client, svc):
    login(client, "alice")
    fid = flag_of(svc, "D1")["flag_id"]
    decide(client, fid, "reject", reason="=HYPERLINK(\"http://x\") formula attempt")
    r = client.get("/audit")
    assert "Hash chain intact" in r.text and "reject" in r.text
    csv_text = client.get("/export/reviewed.csv").text
    assert fid in csv_text and "'=HYPERLINK" in csv_text            # formula injection neutralised
    js = client.get("/export/reviewed.json").json()
    assert js[0]["status"] == "rejected" and js[0]["last_reviewer"] == "alice"
    assert len(client.get("/export/reviewed.json?include=all").json()) == len(svc.wh.flags())


def test_coverage_entity_and_lineage(client, svc):
    login(client, "alice")
    r = client.get("/coverage?data_type=budget&province=GT")
    assert r.status_code == 200 and "Testville" in r.text and "Sampleton" not in r.text
    assert client.get("/coverage?data_type=bogus").status_code == 422
    assert client.get("/coverage?province=XX").status_code == 422
    e = client.get("/entity/MUN:TST")
    assert e.status_code == 200 and "/lineage/" in e.text and "unknown" in e.text
    sha = e.text.split("/lineage/")[1][:64]
    assert client.get(f"/lineage/{sha}").status_code == 200
    assert client.get("/lineage/../../etc/passwd").status_code == 404
    assert client.get("/entity/DROP TABLE").status_code == 404


def test_body_size_limit(client):
    login(client, "alice")
    r = client.post("/logout", content=b"x" * 70000, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 413


# ------------------------------------------------------------------ JSON API
def _token(svc, user):
    tok = sec.new_token()
    svc.store.update_reviewer(user, "token_issued", "test", token_hash=sec.sha256_hex(tok))
    return {"Authorization": f"Bearer {tok}"}


def test_api_requires_token(client):
    assert client.get("/api/flags").status_code == 401
    assert client.get("/api/flags", headers={"Authorization": "Bearer pfr_wrong"}).status_code == 401


def test_api_list_show_decide_and_four_eyes(client, svc):
    ha, hb = _token(svc, "alice"), _token(svc, "bob")
    lst = client.get("/api/flags?named=yes", headers=ha).json()
    assert lst["total"] >= 1 and all(f["names_supplier"] for f in lst["flags"])
    fid = flag_of(svc, "D3")["flag_id"]
    show = client.get(f"/api/flags/{fid}", headers=ha).json()
    assert show["four_eyes_required"] and show["match"]["confidence"] and show["matched_records"]
    body = {"decision": "confirm", "reason": "Register row and award checked", "channel": "bot"}
    r = client.post(f"/api/flags/{fid}/decisions", json=body, headers=ha)
    assert r.status_code == 201 and r.json()["new_status"] == "awaiting second review"
    assert client.post(f"/api/flags/{fid}/decisions", json=body, headers=ha).status_code == 409
    assert client.post(f"/api/flags/{fid}/decisions", json=body, headers=hb).json()["new_status"] == "confirmed"
    assert client.post(f"/api/flags/{fid}/decisions", json={"decision": "confirm", "reason": "x"},
                       headers=hb).status_code == 422
    assert [d["channel"] for d in svc.store.decisions()] == ["bot", "bot"]
    assert json.loads(svc.store.decisions()[0]["flag_snapshot"])["names_supplier"] is True
