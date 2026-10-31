"""Nightly state backup and restore check (CHG-2026-044).

Backs up the DuckDB warehouse and the SQLite review database to a dated folder OUTSIDE the repo.
Nothing opens a live database file. A database open can write side files (SQLite -wal/-shm, DuckDB .wal), so
the backup first takes a SNAPSHOT: it copies the db file and any existing -wal/.wal file into a private temp dir
(0700). The copy is retried until the size and mtime of every source file are the same before and after the copy;
it fails after SNAPSHOT_TRIES. The live folders stay byte-for-byte unchanged.
- SQLite: the online backup API (Connection.backup) reads the snapshot. SQLite replays the copied WAL, so
  committed but un-checkpointed writes are in the backup. integrity_check runs on the result.
- DuckDB: EXPORT DATABASE (Parquet) from the snapshot. The backup refuses when a writer is active.
  A writer is a running `thusa ingest|build|run` process, a `*.building.duckdb` file, or a lock that blocks a
  read-only open. The backup never copies an open database file.
A manifest records the sha256 of every backup file and the row count of every table.
Every error makes the command exit non-zero (fail closed). Backup folders and files use mode 0700 and 0600.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .settings import Paths, REPO_ROOT

DEFAULT_DEST = Path("/home/box/publicfunds-backups")
DEFAULT_KEEP = 14
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WRITER_RE = re.compile(r"(^|[/\s])thusa\s+(ingest|build|run)(\s|$)")


SNAPSHOT_TRIES = 5


def _sig(paths: list[Path]) -> list:
    return [(p.name, st.st_size, st.st_mtime_ns, st.st_ino) if (st := _stat(p)) else (p.name, None) for p in paths]


def _stat(p: Path):
    try:
        return os.stat(p)
    except FileNotFoundError:
        return None


def snapshot(db: Path, side_suffixes: tuple[str, ...], into: Path, tries: int = SNAPSHOT_TRIES) -> Path:
    """Copy db and its side files (only those that exist; never -shm) into `into` without opening them as a database.
    Read-only file reads; the source folder does not change. Retries while a source file changes during the copy."""
    srcs = [db] + [db.with_name(db.name + s) for s in side_suffixes]
    for _ in range(tries):
        before = _sig(srcs)
        for f in into.iterdir():
            f.unlink()
        for src in srcs:
            if src.exists():
                shutil.copyfile(src, into / src.name)
                os.chmod(into / src.name, 0o600)
        if _sig(srcs) == before:
            return into / db.name
        time.sleep(0.2)
    raise BackupError(f"{db.name} kept changing during {tries} snapshot attempts; backup refused")


class BackupError(Exception):
    """Any failure. The caller exits non-zero."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def active_writers(warehouse: Path, ps_output: str | None = None) -> list[str]:
    """Return the reasons that a writer is active. An empty list means that no writer was found."""
    reasons = []
    if ps_output is None:
        try:
            ps_output = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as e:
            raise BackupError(f"cannot list processes: {e}") from e
    for line in ps_output.splitlines():
        if WRITER_RE.search(line):
            reasons.append(f"process: {line.strip()[:200]}")
    building = warehouse.with_suffix(".building.duckdb")
    if building.exists():
        reasons.append(f"build in progress: {building.name} exists")
    return reasons


def _duckdb_locked(path: Path) -> bool:
    """True when another process holds an fcntl WRITE lock on the DuckDB file. Opens the file O_RDONLY and only
    queries the lock (F_GETLK); this writes nothing."""
    import fcntl
    import struct
    fd = os.open(path, os.O_RDONLY)
    try:
        # Ask for a read lock: only a write lock held by another process conflicts. Readers (pf serve) do not.
        fmt = "hhqqi4x"
        res = fcntl.fcntl(fd, fcntl.F_GETLK, struct.pack(fmt, fcntl.F_RDLCK, 0, 0, 0, 0))
        return struct.unpack(fmt, res)[0] != fcntl.F_UNLCK
    finally:
        os.close(fd)


def duckdb_counts(con) -> dict[str, int]:
    rows = con.execute("SELECT table_schema, table_name FROM information_schema.tables "
                       "WHERE table_type = 'BASE TABLE' AND table_catalog = current_database() "
                       "ORDER BY 1, 2").fetchall()
    return {f"{s}.{t}": con.execute(f'SELECT count(*) FROM "{s}"."{t}"').fetchone()[0] for s, t in rows}


def sqlite_counts(con) -> dict[str, int]:
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' "
                                       "AND name NOT LIKE 'sqlite_%' ORDER BY 1")]
    return {n: con.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0] for n in names}


def _secure_tree(root: Path) -> None:
    os.chmod(root, 0o700)
    for p in root.rglob("*"):
        os.chmod(p, 0o700 if p.is_dir() else 0o600)


def backup(warehouse: Path, review_db: Path, dest: Path, keep: int = DEFAULT_KEEP,
           day: str | None = None, ps_output: str | None = None) -> Path:
    if keep < 1:
        raise BackupError("keep must be at least 1")
    day = day or datetime.now().strftime("%Y-%m-%d")
    if not DAY_RE.match(day):
        raise BackupError(f"bad day: {day}")
    for f in (warehouse, review_db):
        if not f.is_file():
            raise BackupError(f"missing: {f}")
    writers = active_writers(warehouse, ps_output)
    if writers:
        raise BackupError("writer active; backup refused: " + "; ".join(writers))
    old_umask = os.umask(0o077)
    try:
        dest.mkdir(parents=True, exist_ok=True)
        os.chmod(dest, 0o700)
        work = Path(tempfile.mkdtemp(prefix=f".{day}.", dir=dest))
        try:
            manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "day": day, "sources": {"duckdb": warehouse.name, "sqlite": review_db.name}}
            snap = Path(tempfile.mkdtemp(prefix=".snap.", dir=work))
            os.chmod(snap, 0o700)
            (snap / "duckdb").mkdir(mode=0o700)
            (snap / "sqlite").mkdir(mode=0o700)
            # DuckDB: never open the live file (an open can create a .wal). A writer holds an fcntl lock on it.
            if _duckdb_locked(warehouse):
                raise BackupError("the warehouse is locked by another process (writer lock); backup refused")
            wsnap = snapshot(warehouse, (".wal",), snap / "duckdb")
            try:
                con = duckdb.connect(str(wsnap))
            except duckdb.Error as e:
                raise BackupError(f"cannot open the warehouse snapshot: {e}") from e
            try:
                manifest["duckdb_tables"] = duckdb_counts(con)
                out = work / "duckdb"
                con.execute(f"EXPORT DATABASE '{out}' (FORMAT PARQUET)")
            finally:
                con.close()
            # SQLite: online backup API from the snapshot (db + -wal). SQLite replays the WAL in the snapshot.
            rsnap = snapshot(review_db, ("-wal",), snap / "sqlite")
            src = sqlite3.connect(rsnap)
            try:
                dst = sqlite3.connect(work / "review.sqlite")
                try:
                    src.backup(dst)
                    if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise BackupError("sqlite integrity_check failed on the copy")
                    manifest["sqlite_tables"] = sqlite_counts(dst)
                finally:
                    dst.close()
            finally:
                src.close()
            shutil.rmtree(snap)
            manifest["files"] = {str(p.relative_to(work)): sha256(p)
                                 for p in sorted(work.rglob("*")) if p.is_file()}
            (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
            _secure_tree(work)
            final = dest / day
            if final.exists():
                old = dest / f".{day}.old"
                shutil.rmtree(old, ignore_errors=True)
                final.rename(old)
                work.rename(final)
                shutil.rmtree(old)
            else:
                work.rename(final)
        except BaseException:
            shutil.rmtree(work, ignore_errors=True)
            raise
        prune(dest, keep)
        return final
    finally:
        os.umask(old_umask)


def daily_dirs(dest: Path) -> list[Path]:
    return sorted(p for p in dest.iterdir() if p.is_dir() and DAY_RE.match(p.name)) if dest.is_dir() else []


def prune(dest: Path, keep: int) -> list[Path]:
    dirs = daily_dirs(dest)
    gone = dirs[:-keep] if len(dirs) > keep else []
    for p in gone:
        shutil.rmtree(p)
    return gone


def restore_check(dest: Path, log: Path, day: str | None = None) -> bool:
    """Restore the latest (or the given) backup into a temp dir and compare it with its manifest.
    Append one PASS or FAIL line to the log. Return True on PASS."""
    problems: list[str] = []
    name = "none"
    try:
        dirs = daily_dirs(dest)
        if day:
            dirs = [d for d in dirs if d.name == day]
        if not dirs:
            raise BackupError(f"no backup found in {dest}")
        bdir = dirs[-1]
        name = bdir.name
        manifest = json.loads((bdir / "manifest.json").read_text())
        actual = {str(p.relative_to(bdir)) for p in bdir.rglob("*") if p.is_file()} - {"manifest.json"}
        if actual != set(manifest["files"]):
            problems.append(f"file list differs: extra {sorted(actual - set(manifest['files']))}, "
                            f"missing {sorted(set(manifest['files']) - actual)}")
        for rel, digest in manifest["files"].items():
            p = bdir / rel
            if p.is_file() and sha256(p) != digest:
                problems.append(f"sha256 mismatch: {rel}")
        with tempfile.TemporaryDirectory(prefix="pf-restore-") as tmp:
            con = duckdb.connect(str(Path(tmp) / "restored.duckdb"))
            try:
                con.execute(f"IMPORT DATABASE '{bdir / 'duckdb'}'")
                if duckdb_counts(con) != manifest["duckdb_tables"]:
                    problems.append("duckdb row counts differ from the manifest")
            finally:
                con.close()
            copy = Path(tmp) / "review.sqlite"
            shutil.copyfile(bdir / "review.sqlite", copy)
            s = sqlite3.connect(copy)
            try:
                if s.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    problems.append("sqlite integrity_check failed")
                if sqlite_counts(s) != manifest["sqlite_tables"]:
                    problems.append("sqlite row counts differ from the manifest")
            finally:
                s.close()
    except Exception as e:  # fail closed: any error is a FAIL
        problems.append(f"error: {type(e).__name__}: {e}")
    ok = not problems
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp} {'PASS' if ok else 'FAIL'} backup={name}" + ("" if ok else " " + " | ".join(problems))
    log.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(line.replace("\n", " ") + "\n")
    print(line)
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m thusa.backup")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--keep", type=int, default=int(os.environ.get("PF_BACKUP_KEEP", DEFAULT_KEEP)))
    r = sub.add_parser("restore-check")
    r.add_argument("--day")
    a = ap.parse_args(argv)
    root = Path(os.environ.get("THUSA_ROOT", REPO_ROOT))
    paths = Paths(root)
    dest = Path(os.environ.get("PF_BACKUP_DIR", DEFAULT_DEST))
    try:
        if a.cmd == "backup":
            out = backup(paths.warehouse, paths.review_db, dest, a.keep)
            print(f"backup: ok {out}")
            return 0
        log = Path(os.environ.get("PF_RESTORE_LOG", dest / "restore-check.log"))
        return 0 if restore_check(dest, log, a.day) else 1
    except Exception as e:
        print(f"backup: FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
