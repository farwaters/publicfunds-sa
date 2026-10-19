"""Review store: a small SQLite database next to (not inside) the rebuilt DuckDB warehouse. ADR-0008.

Why SQLite: the warehouse is rebuilt and swapped atomically on every pipeline run, and DuckDB allows one writer
process; reviews must survive rebuilds and be writable by the web app and the `pf` CLI at the same time.

Integrity:
- `decision` and `reviewer_event` are append-only: UPDATE and DELETE are refused by triggers.
- every decision carries `prev_hash` and `record_hash` (SHA-256 chain), so edits made by bypassing the triggers
  are detectable with `pf review verify` / `verify_chain()`.
- decisions are keyed on the deterministic flag_id (sha256 of detector|subject|body|period) plus the evidence hash
  the reviewer saw.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from thusa.review import workflow as wf

SAST = ZoneInfo("Africa/Johannesburg")
GENESIS = "0" * 64
SCHEMA_VERSION = 1

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviewer (
  reviewer_id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE CHECK (length(username) BETWEEN 2 AND 32),
  display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('reviewer', 'admin')),
  password_hash TEXT NOT NULL,
  token_hash TEXT UNIQUE,
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  created_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviewer_event (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL,
  event TEXT NOT NULL CHECK (event IN ('created', 'password_reset', 'token_issued', 'token_revoked', 'disabled',
                                       'enabled', 'role_changed')),
  detail TEXT,
  actor TEXT NOT NULL,
  at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decision (
  decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
  flag_id TEXT NOT NULL CHECK (length(flag_id) = 16),
  reviewer_id INTEGER NOT NULL REFERENCES reviewer(reviewer_id),
  reviewer_username TEXT NOT NULL,
  reviewer_role TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('confirm', 'reject', 'needs_info', 'escalate')),
  prev_status TEXT NOT NULL,
  new_status TEXT NOT NULL,
  reason TEXT NOT NULL CHECK (length(trim(reason)) >= {wf.REASON_MIN}),
  notes TEXT,
  evidence_hash TEXT NOT NULL CHECK (length(evidence_hash) = 64),
  flag_snapshot TEXT NOT NULL,
  build_id TEXT,
  channel TEXT NOT NULL CHECK (channel IN ('web', 'api', 'cli', 'bot')),
  decided_at_utc TEXT NOT NULL,
  decided_at_sast TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  record_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS decision_flag ON decision(flag_id, decision_id);
CREATE TRIGGER IF NOT EXISTS decision_no_update BEFORE UPDATE ON decision
  BEGIN SELECT RAISE(ABORT, 'decision log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS decision_no_delete BEFORE DELETE ON decision
  BEGIN SELECT RAISE(ABORT, 'decision log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS reviewer_event_no_update BEFORE UPDATE ON reviewer_event
  BEGIN SELECT RAISE(ABORT, 'reviewer events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS reviewer_event_no_delete BEFORE DELETE ON reviewer_event
  BEGIN SELECT RAISE(ABORT, 'reviewer events are append-only'); END;
CREATE TABLE IF NOT EXISTS session (
  session_hash TEXT PRIMARY KEY,
  reviewer_id INTEGER NOT NULL REFERENCES reviewer(reviewer_id),
  csrf_token TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  last_seen_utc TEXT NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS login_attempt (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL,
  ok INTEGER NOT NULL,
  at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS login_attempt_key ON login_attempt(key, at_utc);
"""

HASHED_FIELDS = ["flag_id", "reviewer_username", "reviewer_role", "decision", "prev_status", "new_status", "reason",
                 "notes", "evidence_hash", "flag_snapshot", "build_id", "channel", "decided_at_utc", "prev_hash"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def iso_sast(t: datetime) -> str:
    return t.astimezone(SAST).isoformat(timespec="seconds")


def sast_label(value: str | None) -> str:
    """Display form: '2026-10-19 10:51 SAST'."""
    if not value:
        return ""
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t.astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")


def record_hash(rec: dict) -> str:
    return hashlib.sha256(json.dumps([rec.get(k) for k in HASHED_FIELDS], ensure_ascii=False).encode()).hexdigest()


class ReviewStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, mode=0o700)   # WAL/SHM side files inherit a private directory
        new = not self.path.exists()
        with self.connect() as con:
            con.executescript(SCHEMA)
            con.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", [str(SCHEMA_VERSION)])
        if new:
            self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA busy_timeout = 10000")
        try:
            yield con
        finally:
            con.close()

    # ------------------------------------------------------------------ reviewers
    def add_reviewer(self, username: str, display_name: str, role: str, password_hash: str, actor: str) -> dict:
        now = iso_utc(utcnow())
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute("INSERT INTO reviewer (username, display_name, role, password_hash, created_at_utc) "
                            "VALUES (?, ?, ?, ?, ?)", [username, display_name, role, password_hash, now])
                con.execute("INSERT INTO reviewer_event (username, event, detail, actor, at_utc) VALUES (?,?,?,?,?)",
                            [username, "created", f"role={role}", actor, now])
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
        return self.get_reviewer(username)

    def get_reviewer(self, username: str) -> dict | None:
        with self.connect() as con:
            r = con.execute("SELECT * FROM reviewer WHERE username = ?", [username]).fetchone()
        return dict(r) if r else None

    def get_reviewer_by_id(self, reviewer_id: int) -> dict | None:
        with self.connect() as con:
            r = con.execute("SELECT * FROM reviewer WHERE reviewer_id = ?", [reviewer_id]).fetchone()
        return dict(r) if r else None

    def get_reviewer_by_token_hash(self, token_hash: str) -> dict | None:
        with self.connect() as con:
            r = con.execute("SELECT * FROM reviewer WHERE token_hash = ? AND active = 1", [token_hash]).fetchone()
        return dict(r) if r else None

    def list_reviewers(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT reviewer_id, username, display_name, role, active, created_at_utc, "
                               "token_hash IS NOT NULL AS has_token FROM reviewer ORDER BY username").fetchall()
        return [dict(r) for r in rows]

    def update_reviewer(self, username: str, event: str, actor: str, detail: str | None = None, **fields) -> None:
        allowed = {"password_hash", "token_hash", "active", "role"}
        assert set(fields) <= allowed, fields
        now = iso_utc(utcnow())
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                if fields:
                    sets = ", ".join(f"{k} = ?" for k in fields)  # keys come from the fixed allow-list above
                    cur = con.execute(f"UPDATE reviewer SET {sets} WHERE username = ?", [*fields.values(), username])
                    if cur.rowcount != 1:
                        raise KeyError(username)
                con.execute("INSERT INTO reviewer_event (username, event, detail, actor, at_utc) VALUES (?,?,?,?,?)",
                            [username, event, detail, actor, now])
                if event in ("disabled", "password_reset"):
                    con.execute("UPDATE session SET revoked = 1 WHERE reviewer_id = "
                                "(SELECT reviewer_id FROM reviewer WHERE username = ?)", [username])
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

    def reviewer_events(self) -> list[dict]:
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM reviewer_event ORDER BY event_id").fetchall()]

    # ------------------------------------------------------------------ decisions
    def decisions(self, flag_id: str | None = None) -> list[dict]:
        with self.connect() as con:
            if flag_id:
                rows = con.execute("SELECT * FROM decision WHERE flag_id = ? ORDER BY decision_id", [flag_id])
            else:
                rows = con.execute("SELECT * FROM decision ORDER BY decision_id")
            return [dict(r) for r in rows.fetchall()]

    def states(self, names_by_flag: dict[str, bool]) -> dict[str, wf.State]:
        """Replay the log for many flags at once. Flags with no decisions get their initial state."""
        by_flag: dict[str, list[dict]] = {}
        for d in self.decisions():
            by_flag.setdefault(d["flag_id"], []).append(d)
        out = {fid: wf.replay(by_flag.get(fid, []), named) for fid, named in names_by_flag.items()}
        for fid, ds in by_flag.items():           # decisions on flags no longer in the build (kept, never lost)
            out.setdefault(fid, wf.replay(ds, json.loads(ds[-1]["flag_snapshot"]).get("names_supplier", True)))
        return out

    def decide(self, flag: dict, reviewer: dict, decision: str, reason: str, notes: str | None, channel: str,
               build_id: str | None, now: datetime | None = None) -> dict:
        """Validate and append one decision atomically (BEGIN IMMEDIATE serialises concurrent reviewers)."""
        if not reviewer or not reviewer.get("active"):
            raise wf.ReviewError("Reviewer account is not active.")
        if channel not in ("web", "api", "cli", "bot"):
            raise wf.ReviewError("Unknown channel.")
        reason, notes = wf.validate_text(reason, notes)
        named = bool(flag["names_supplier"])
        ev_hash = wf.evidence_hash(flag)
        t = now or utcnow()
        snapshot = json.dumps({k: flag.get(k) for k in ("detector_id", "detector_version", "severity", "score",
                                                        "title", "gov_body_id", "period_label", "names_supplier")},
                              sort_keys=True, default=str)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                prior = [dict(r) for r in con.execute(
                    "SELECT * FROM decision WHERE flag_id = ? ORDER BY decision_id", [flag["flag_id"]]).fetchall()]
                state = wf.replay(prior, named)
                new_status = wf.next_status(state, decision, reviewer["username"], reviewer["role"], named, ev_hash)
                last = con.execute("SELECT record_hash FROM decision ORDER BY decision_id DESC LIMIT 1").fetchone()
                rec = {"flag_id": flag["flag_id"], "reviewer_id": reviewer["reviewer_id"],
                       "reviewer_username": reviewer["username"], "reviewer_role": reviewer["role"],
                       "decision": decision, "prev_status": state.status, "new_status": new_status,
                       "reason": reason, "notes": notes, "evidence_hash": ev_hash, "flag_snapshot": snapshot,
                       "build_id": build_id, "channel": channel, "decided_at_utc": iso_utc(t),
                       "decided_at_sast": iso_sast(t), "prev_hash": last["record_hash"] if last else GENESIS}
                rec["record_hash"] = record_hash(rec)
                cols = list(rec)
                cur = con.execute(f"INSERT INTO decision ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                  [rec[c] for c in cols])
                rec["decision_id"] = cur.lastrowid
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
        return rec

    def verify_chain(self) -> dict:
        prev, n = GENESIS, 0
        for d in self.decisions():
            n += 1
            if d["prev_hash"] != prev or record_hash(d) != d["record_hash"]:
                return {"ok": False, "n": n, "broken_at_decision_id": d["decision_id"], "head": prev}
            prev = d["record_hash"]
        return {"ok": True, "n": n, "head": prev}

    # ------------------------------------------------------------------ sessions and login attempts
    def create_session(self, session_hash: str, reviewer_id: int, csrf: str) -> None:
        now = iso_utc(utcnow())
        with self.connect() as con:
            con.execute("INSERT INTO session VALUES (?, ?, ?, ?, ?, 0)", [session_hash, reviewer_id, csrf, now, now])

    def get_session(self, session_hash: str) -> dict | None:
        with self.connect() as con:
            r = con.execute("SELECT s.*, r.username, r.display_name, r.role, r.active FROM session s "
                            "JOIN reviewer r USING (reviewer_id) WHERE s.session_hash = ?", [session_hash]).fetchone()
        return dict(r) if r else None

    def touch_session(self, session_hash: str) -> None:
        with self.connect() as con:
            con.execute("UPDATE session SET last_seen_utc = ? WHERE session_hash = ?", [iso_utc(utcnow()), session_hash])

    def revoke_session(self, session_hash: str) -> None:
        with self.connect() as con:
            con.execute("UPDATE session SET revoked = 1 WHERE session_hash = ?", [session_hash])

    def record_attempt(self, keys: list[str], ok: bool) -> None:
        now = iso_utc(utcnow())
        with self.connect() as con:
            con.executemany("INSERT INTO login_attempt (key, ok, at_utc) VALUES (?, ?, ?)",
                            [(k, int(ok), now) for k in keys])

    def failures_since(self, key: str, since_utc: str) -> int:
        with self.connect() as con:
            return con.execute("SELECT count(*) FROM login_attempt WHERE key = ? AND ok = 0 AND at_utc >= ? AND "
                               "attempt_id > coalesce((SELECT max(attempt_id) FROM login_attempt WHERE key = ? "
                               "AND ok = 1), 0)", [key, since_utc, key]).fetchone()[0]
