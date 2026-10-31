"""CHG-2026-044: backup and restore check on temp fixtures only (no real data)."""
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
from pathlib import Path

import hashlib

import duckdb
import pytest

from thusa import backup as bk

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def state(tmp_path):
    wh = tmp_path / "data" / "thusa.duckdb"
    wh.parent.mkdir(parents=True)
    con = duckdb.connect(str(wh))
    con.execute("CREATE SCHEMA curated")
    con.execute("CREATE TABLE curated.award AS SELECT range AS id, 'x' || range AS name FROM range(25)")
    con.execute("CREATE TABLE main.t2 (a INTEGER)")
    con.execute("CREATE VIEW curated.v AS SELECT * FROM curated.award")
    con.close()
    rv = tmp_path / "data" / "review" / "review.sqlite"
    rv.parent.mkdir()
    s = sqlite3.connect(rv)
    s.execute("CREATE TABLE decision (id INTEGER PRIMARY KEY, flag TEXT, verdict TEXT)")
    s.executemany("INSERT INTO decision (flag, verdict) VALUES (?, ?)", [("F1", "ok"), ("F2", "reject")])
    s.commit()
    s.close()
    return wh, rv, tmp_path / "backups"


def run_backup(state, **kw):
    wh, rv, dest = state
    return bk.backup(wh, rv, dest, ps_output="", **kw)


def test_backup_writes_manifest_counts_and_hashes(state):
    out = run_backup(state, day="2026-10-31")
    m = json.loads((out / "manifest.json").read_text())
    assert m["duckdb_tables"] == {"curated.award": 25, "main.t2": 0}
    assert m["sqlite_tables"] == {"decision": 2}
    assert "review.sqlite" in m["files"] and any(k.startswith("duckdb/") for k in m["files"])
    for rel, h in m["files"].items():
        assert bk.sha256(out / rel) == h


def test_modes_are_private(state):
    out = run_backup(state, day="2026-10-31")
    assert stat.S_IMODE(os.stat(state[2]).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(out).st_mode) == 0o700
    for p in out.rglob("*"):
        assert stat.S_IMODE(os.stat(p).st_mode) == (0o700 if p.is_dir() else 0o600)


def test_restore_check_pass(state):
    run_backup(state, day="2026-10-31")
    log = state[2] / "restore-check.log"
    assert bk.restore_check(state[2], log)
    assert " PASS backup=2026-10-31" in log.read_text()
    assert stat.S_IMODE(os.stat(log).st_mode) == 0o600


def test_restore_check_fails_on_tampered_file(state):
    out = run_backup(state, day="2026-10-31")
    with open(out / "review.sqlite", "ab") as f:
        f.write(b"\0")
    log = state[2] / "r.log"
    assert not bk.restore_check(state[2], log)
    assert "FAIL" in log.read_text() and "sha256 mismatch: review.sqlite" in log.read_text()


def test_restore_check_fails_on_count_mismatch(state):
    out = run_backup(state, day="2026-10-31")
    mp = out / "manifest.json"
    m = json.loads(mp.read_text())
    m["duckdb_tables"]["curated.award"] = 24
    os.chmod(mp, 0o600)
    mp.write_text(json.dumps(m))
    assert not bk.restore_check(state[2], state[2] / "r.log")
    assert "duckdb row counts differ" in (state[2] / "r.log").read_text()


def test_restore_check_fails_with_no_backup(tmp_path):
    log = tmp_path / "r.log"
    assert not bk.restore_check(tmp_path / "none", log)
    assert "FAIL backup=none" in log.read_text()


def test_retention_keeps_newest(state):
    for d in range(1, 6):
        run_backup(state, day=f"2026-10-0{d}", keep=3)
    assert [p.name for p in bk.daily_dirs(state[2])] == ["2026-10-03", "2026-10-04", "2026-10-05"]


def test_same_day_rerun_replaces(state):
    run_backup(state, day="2026-10-31")
    run_backup(state, day="2026-10-31")
    assert [p.name for p in state[2].iterdir()] == ["2026-10-31"]


def test_refuses_when_thusa_run_is_active(state):
    wh, rv, dest = state
    with pytest.raises(bk.BackupError, match="writer active"):
        bk.backup(wh, rv, dest, ps_output="123 /x/.venv/bin/python /x/.venv/bin/thusa run\n")
    assert not dest.exists() or not list(dest.iterdir())


def test_refuses_when_build_file_exists(state):
    wh, rv, dest = state
    wh.with_suffix(".building.duckdb").write_bytes(b"")
    with pytest.raises(bk.BackupError, match="build in progress"):
        bk.backup(wh, rv, dest, ps_output="")


def test_refuses_while_writer_lock_is_held(state):
    wh, rv, dest = state
    holder = subprocess.Popen([sys.executable, "-c",
                               "import duckdb,sys,time; c=duckdb.connect(sys.argv[1]); print('locked',flush=True); time.sleep(60)",
                               str(wh)], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "locked"
        with pytest.raises(bk.BackupError, match="writer lock"):
            bk.backup(wh, rv, dest, ps_output="")
        assert not bk.daily_dirs(dest)
        assert not [p for p in dest.iterdir()] if dest.exists() else True
    finally:
        holder.kill()
        holder.wait()


def test_missing_source_fails(state):
    wh, rv, dest = state
    rv.unlink()
    with pytest.raises(bk.BackupError, match="missing"):
        bk.backup(wh, rv, dest, ps_output="")


def test_writer_regex():
    assert bk.active_writers(Path("/nonexistent/x.duckdb"), "1 thusa build\n2 /v/bin/thusa ingest --all\n")
    assert not bk.active_writers(Path("/nonexistent/x.duckdb"), "1 python -m thusa.backup backup\n2 thusa report\n")


def test_cli_exit_codes(state, tmp_path):
    wh, rv, dest = state
    env = {**os.environ, "THUSA_ROOT": str(tmp_path), "PF_BACKUP_DIR": str(dest),
           "PF_RESTORE_LOG": str(tmp_path / "rc.log")}
    env.pop("THUSA_REVIEW_DB", None)
    r = subprocess.run([sys.executable, "-m", "thusa.backup", "backup"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, "-m", "thusa.backup", "restore-check"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and "PASS" in r.stdout
    rv.unlink()
    r = subprocess.run([sys.executable, "-m", "thusa.backup", "backup"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 1 and "FAILED" in r.stderr


def test_backup_dir_is_gitignored():
    r = subprocess.run(["git", "check-ignore", "-q", "publicfunds-backups/2026-10-31/manifest.json"], cwd=ROOT)
    assert r.returncode == 0


def folder_state(*dirs):
    """Every file in the folders (recursive): name, size, mode and sha256. mtimes are left out on purpose:
    a byte-for-byte check plus the file list is the claim."""
    out = {}
    for d in dirs:
        for p in sorted(Path(d).rglob("*")):
            st = os.stat(p)
            out[str(p)] = (st.st_mode, st.st_size, hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
    return out


@pytest.mark.parametrize("wal_mode", [False, True])
def test_source_folders_unchanged(state, wal_mode):
    """The live case: a WAL-mode db with no -wal/-shm on disk. A read-only open of it creates both files."""
    wh, rv, dest = state
    if wal_mode:
        c = sqlite3.connect(rv)
        c.execute("PRAGMA journal_mode=WAL")
        c.close()
        assert sorted(p.name for p in rv.parent.iterdir()) == ["review.sqlite"]
    before = folder_state(wh.parent, rv.parent)
    run_backup(state, day="2026-10-31")
    assert folder_state(wh.parent, rv.parent) == before


def test_wal_mode_uncheckpointed_writes_are_backed_up_and_source_unchanged(state):
    """A writer keeps the db in WAL mode with un-checkpointed commits (like pf serve). The backup must include
    them and must not create, change or remove any file next to the db (no new -wal/-shm, no checkpoint)."""
    wh, rv, dest = state
    holder = subprocess.Popen([sys.executable, "-c", (
        "import sqlite3,sys,time\n"
        "c=sqlite3.connect(sys.argv[1]); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA wal_autocheckpoint=0')\n"
        "c.executemany('INSERT INTO decision (flag, verdict) VALUES (?, ?)', [('W%d' % i, 'ok') for i in range(5)])\n"
        "c.commit(); print('ready', flush=True); time.sleep(60)"), str(rv)], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "ready"
        wal = rv.with_name(rv.name + "-wal")
        assert wal.exists() and wal.stat().st_size > 0
        before = folder_state(wh.parent, rv.parent)
        out = run_backup(state, day="2026-10-31")
        assert folder_state(wh.parent, rv.parent) == before
        m = json.loads((out / "manifest.json").read_text())
        assert m["sqlite_tables"]["decision"] == 7
        c = sqlite3.connect(out / "review.sqlite")
        assert c.execute("SELECT count(*) FROM decision WHERE flag LIKE 'W%'").fetchone()[0] == 5
        c.close()
        assert not list(out.glob("review.sqlite-*"))
    finally:
        holder.kill()
        holder.wait()


def test_reader_does_not_block_backup(state):
    """pf serve may hold a read-only DuckDB connection; that is not a writer."""
    wh, rv, dest = state
    holder = subprocess.Popen([sys.executable, "-c",
                               "import duckdb,sys,time; c=duckdb.connect(sys.argv[1], read_only=True); print('r',flush=True); time.sleep(60)",
                               str(wh)], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "r"
        before = folder_state(wh.parent, rv.parent)
        run_backup(state, day="2026-10-31")
        assert folder_state(wh.parent, rv.parent) == before
    finally:
        holder.kill()
        holder.wait()


def test_snapshot_refuses_a_file_that_keeps_changing(tmp_path, monkeypatch):
    db = tmp_path / "x.sqlite"
    db.write_bytes(b"a")
    into = tmp_path / "snap"
    into.mkdir()
    n = iter(range(100))
    monkeypatch.setattr(bk, "_sig", lambda paths: [next(n)])
    monkeypatch.setattr(bk.time, "sleep", lambda s: None)
    with pytest.raises(bk.BackupError, match="kept changing"):
        bk.snapshot(db, ("-wal",), into, tries=3)
