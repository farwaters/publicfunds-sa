"""`pf` CLI: reviewer admin, JSON review interface for bots, exit codes, secret handling."""
import json
import stat

from tests.conftest import flag_of
from thusa.review.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    o = capsys.readouterr()
    return code, o.out, o.err


def test_reviewer_add_writes_0600_file_and_never_prints_password(paths, tmp_path, capsys):
    cred = tmp_path / "creds" / "carol"
    code, out, _ = run(capsys, "reviewer", "add", "carol", "--display-name", "Carol", "--admin",
                       "--credentials-file", str(cred))
    assert code == 0 and json.loads(out)["role"] == "admin"
    assert stat.S_IMODE(cred.stat().st_mode) == 0o600
    pw = [ln.split("=", 1)[1] for ln in cred.read_text().splitlines() if ln.startswith("password=")][0]
    assert len(pw) >= 20 and pw not in out
    assert run(capsys, "reviewer", "add", "carol", "--credentials-file", str(tmp_path / "x"))[0] == 2
    assert run(capsys, "reviewer", "add", "Bad Name!", "--credentials-file", str(tmp_path / "y"))[0] == 2
    assert run(capsys, "reviewer", "add", "dave")[0] == 2               # no file -> refuse (never print)
    code, out, _ = run(capsys, "reviewer", "list")
    assert [r["username"] for r in json.loads(out)] == ["carol"] and "password" not in out


def test_bot_flow_list_show_decide_four_eyes(svc, tmp_path, capsys, monkeypatch):
    ta, tb = tmp_path / "a.token", tmp_path / "b.token"
    assert run(capsys, "reviewer", "token", "alice", "--out", str(ta))[0] == 0
    assert run(capsys, "reviewer", "token", "bob", "--out", str(tb))[0] == 0
    assert stat.S_IMODE(ta.stat().st_mode) == 0o600
    code, out, _ = run(capsys, "review", "list", "--named", "yes")
    lst = json.loads(out)
    assert code == 0 and lst["total"] >= 1
    fid = flag_of(svc, "D3")["flag_id"]
    show = json.loads(run(capsys, "review", "show", fid)[1])
    assert show["four_eyes_required"] is True and show["evidence"]
    args = ["review", "decide", fid, "--decision", "confirm", "--reason", "Award and register row match", "--via", "bot"]
    code, out, _ = run(capsys, *args, "--token-file", str(ta))
    assert code == 0 and json.loads(out)["new_status"] == "awaiting second review"
    code, _, err = run(capsys, *args, "--token-file", str(ta))
    assert code == 3 and "Four-eyes" in json.loads(err)["error"]
    monkeypatch.setenv("PF_REVIEW_TOKEN", tb.read_text().strip())
    code, out, _ = run(capsys, *args)
    assert code == 0 and json.loads(out)["new_status"] == "confirmed"
    hist = json.loads(run(capsys, "review", "history", fid)[1])
    assert [h["reviewer_username"] for h in hist] == ["alice", "bob"] and hist[0]["decided_at_sast"].endswith("+02:00")
    assert json.loads(run(capsys, "review", "verify")[1])["ok"] is True
    code, out, _ = run(capsys, "review", "export", "--format", "csv")
    assert fid in out and "confirmed" in out


def test_decide_auth_failures(svc, tmp_path, capsys, monkeypatch):
    fid = flag_of(svc, "D1")["flag_id"]
    args = ["review", "decide", fid, "--decision", "reject", "--reason", "Not a real overspend here"]
    bad = tmp_path / "bad.token"
    bad.write_text("pfr_not-a-real-token")
    bad.chmod(0o600)
    assert run(capsys, *args, "--token-file", str(bad))[0] == 4
    bad.chmod(0o644)
    assert run(capsys, *args, "--token-file", str(bad))[0] == 4        # world-readable token file refused
    assert run(capsys, *args, "--token-file", str(tmp_path / "missing"))[0] == 4
    assert svc.store.decisions() == []


def test_revoked_token_stops_working(svc, tmp_path, capsys):
    t = tmp_path / "t"
    run(capsys, "reviewer", "token", "alice", "--out", str(t))
    run(capsys, "reviewer", "revoke-token", "alice")
    fid = flag_of(svc, "D1")["flag_id"]
    assert run(capsys, "review", "decide", fid, "--decision", "reject", "--reason", "valid reason text",
               "--token-file", str(t))[0] == 4


def test_serve_refuses_public_bind(paths, capsys):
    code, _, err = run(capsys, "serve", "--host", "0.0.0.0")
    assert code == 2 and "allow-remote" in err
