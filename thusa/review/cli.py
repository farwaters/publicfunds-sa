"""`pf` - command line for the Thusa review app. JSON on stdout so a bot (or script) can drive reviews.

  pf reviewer add NAME --display-name "..." [--admin] --credentials-file PATH   (password written to a 0600 file)
  pf reviewer list | disable NAME | enable NAME | reset-password NAME --credentials-file PATH
  pf reviewer token NAME --out PATH        issue an API/CLI token (0600 file; replaces any previous token)
  pf reviewer revoke-token NAME
  pf review list [--status S] [--detector D] [--severity S] [--named yes|no] [--q TEXT] [--limit N]
  pf review show FLAG_ID
  pf review history FLAG_ID
  pf review decide FLAG_ID --decision confirm|reject|needs_info|escalate --reason "..." [--notes "..."] [--via cli|bot]
        authenticates with PF_REVIEW_TOKEN or --token-file (default ~/.config/publicfunds/review_token)
  pf review verify                         check the audit hash chain
  pf review export [--format csv|json] [--all] [--out PATH]
  pf case export FLAG_ID [--out DIR] [--pdf]   case referral pack (Markdown) for one hidden lead, for independent
                                           checking; no personal information; default DIR data/cases/ (gitignored)
  pf serve [--host 127.0.0.1] [--port 8765]
  pf publish                               rebuild the public static snapshot (dist/public/)
  pf publish-data [--out DIR]              write the public JSON data for the dashboard (public-data/v1/);
                                           refuses (exit 3) if the build failed data quality or the export is unsafe

Exit codes: 0 ok · 2 invalid input / not found · 3 workflow rule (e.g. four-eyes) · 4 authentication.
Secrets (passwords, tokens) are never printed.
"""
from __future__ import annotations

import argparse
import getpass
import ipaddress
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

from thusa.review import security as sec
from thusa.review import workflow as wf
from thusa.review.store import SAST
from thusa.settings import get_paths

DEFAULT_TOKEN_FILE = Path.home() / ".config" / "publicfunds" / "review_token"


class CliError(Exception):
    def __init__(self, msg: str, code: int = 2):
        super().__init__(msg)
        self.code = code


def out(obj) -> None:
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def write_secret_file(path: Path, text: str, force: bool = False) -> None:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise CliError(f"{path} already exists; pass --force to overwrite")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)


def read_token(token_file: str | None) -> str:
    tok = os.environ.get("PF_REVIEW_TOKEN")
    if tok:
        return tok.strip()
    p = Path(token_file).expanduser() if token_file else DEFAULT_TOKEN_FILE
    if not p.exists():
        raise CliError("No reviewer token: set PF_REVIEW_TOKEN or pass --token-file (see `pf reviewer token`)", 4)
    if p.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise CliError(f"{p} is readable by other users; run chmod 600 {p}", 4)
    return p.read_text(encoding="utf-8").strip()


def _svc():
    from thusa.review.service import Service
    return Service(get_paths())


def _actor(a) -> str:
    return a.actor or f"os:{getpass.getuser()}"


def _cred_text(username: str, password: str, role: str) -> str:
    now = datetime.now(timezone.utc).astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")
    return (f"# Thusa review app credentials - created {now}. Keep this file private (mode 600).\n"
            f"# Sign in at http://127.0.0.1:{os.environ.get('PF_PORT', '8765')}/login: the PublicFunds Bot opens it in its own browser (RB-08).\n"
            f"username={username}\nrole={role}\npassword={password}\n")


def cmd_reviewer(a) -> int:
    from thusa.review.store import ReviewStore
    store = ReviewStore(get_paths().review_db)
    if a.action == "list":
        out(store.list_reviewers())
        return 0
    name = (a.username or "").lower()
    if not sec.valid_username(name):
        raise CliError("username must be 2-32 chars: lowercase letters, digits, . _ - (starting with a letter)")
    if a.action == "add":
        if store.get_reviewer(name):
            raise CliError(f"reviewer {name} already exists")
        if not a.credentials_file:
            raise CliError("--credentials-file is required (passwords are never printed)")
        pw = sec.generate_password()
        role = "admin" if a.admin else "reviewer"
        write_secret_file(Path(a.credentials_file), _cred_text(name, pw, role), a.force)
        store.add_reviewer(name, a.display_name or name, role, sec.hash_password(pw), _actor(a))
        out({"created": name, "role": role, "credentials_file": str(Path(a.credentials_file).expanduser())})
        return 0
    r = store.get_reviewer(name)
    if not r:
        raise CliError(f"no reviewer {name}")
    if a.action == "reset-password":
        if not a.credentials_file:
            raise CliError("--credentials-file is required (passwords are never printed)")
        pw = sec.generate_password()
        write_secret_file(Path(a.credentials_file), _cred_text(name, pw, r["role"]), a.force)
        store.update_reviewer(name, "password_reset", _actor(a), password_hash=sec.hash_password(pw))
        out({"password_reset": name, "credentials_file": str(Path(a.credentials_file).expanduser())})
    elif a.action == "token":
        if not a.out:
            raise CliError("--out is required (tokens are never printed)")
        tok = sec.new_token()
        write_secret_file(Path(a.out), tok + "\n", a.force)
        store.update_reviewer(name, "token_issued", _actor(a), token_hash=sec.sha256_hex(tok))
        out({"token_issued": name, "token_file": str(Path(a.out).expanduser())})
    elif a.action == "revoke-token":
        store.update_reviewer(name, "token_revoked", _actor(a), token_hash=None)
        out({"token_revoked": name})
    elif a.action in ("disable", "enable"):
        store.update_reviewer(name, a.action + "d", _actor(a), active=int(a.action == "enable"))
        out({a.action + "d": name})
    return 0


def _brief(f: dict) -> dict:
    from thusa.review.app import _flag_summary
    return json.loads(json.dumps(_flag_summary(f), default=str))


def cmd_review(a) -> int:
    svc = _svc()
    if a.action == "list":
        if a.status and a.status not in wf.STATUSES + ["open", "stale"]:
            raise CliError(f"unknown status; use one of {wf.STATUSES + ['open', 'stale']}")
        flags = svc.list_flags(a.detector, a.severity, a.status, a.q, a.named)
        out({"total": len(flags), "shown": min(len(flags), a.limit), "flags": [_brief(f) for f in flags[:a.limit]]})
    elif a.action == "show":
        from thusa.review.app import _flag_full
        f = svc.get_flag(a.flag_id)
        if not f:
            raise CliError("no such flag in the current build")
        out(_flag_full(f))
    elif a.action == "history":
        out([{k: d[k] for k in ("decision_id", "reviewer_username", "decision", "prev_status", "new_status", "reason",
                                "notes", "channel", "decided_at_sast", "evidence_hash", "record_hash")}
             for d in svc.store.decisions(a.flag_id)])
    elif a.action == "decide":
        tok = read_token(a.token_file)
        r = svc.store.get_reviewer_by_token_hash(sec.sha256_hex(tok)) if tok.startswith(sec.TOKEN_PREFIX) else None
        if not r:
            raise CliError("token not recognised (revoked, wrong file, or reviewer disabled)", 4)
        try:
            rec = svc.decide(a.flag_id, r, a.decision, a.reason, a.notes, a.via)
        except wf.FourEyesError as e:
            raise CliError(str(e), 3)
        except wf.ReviewError as e:
            raise CliError(str(e), 2)
        from thusa.review.app import _decision_out
        out(_decision_out(rec))
    elif a.action == "verify":
        res = svc.store.verify_chain()
        out(res)
        return 0 if res["ok"] else 3
    elif a.action == "export":
        from thusa.review.service import to_csv
        rows = svc.reviewed(include_unreviewed=a.all)
        text = to_csv(rows) if a.format == "csv" else json.dumps(rows, indent=1, ensure_ascii=False, default=str)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            out({"rows": len(rows), "file": a.out})
        else:
            sys.stdout.write(text)
    return 0


def cmd_case(a) -> int:
    from thusa.review.casepack import UnsafePack, export
    out_dir = Path(a.out) if a.out else get_paths().root / "data" / "cases"
    try:
        out(export(_svc(), a.flag_id, out_dir, a.pdf))
    except LookupError as e:
        raise CliError(str(e), 2)
    except UnsafePack as e:
        raise CliError(str(e), 3)
    return 0


def cmd_serve(a) -> int:
    import uvicorn

    from thusa.review.app import create_app
    try:
        loopback = ipaddress.ip_address(a.host).is_loopback
    except ValueError:
        loopback = a.host == "localhost"
    if not loopback and not a.allow_remote:
        raise CliError("refusing to bind a non-loopback address without --allow-remote; put it behind a TLS reverse "
                       "proxy instead (runbook RB-08)")
    uvicorn.run(create_app(), host=a.host, port=a.port, server_header=False, date_header=True,
                proxy_headers=a.proxy_headers, forwarded_allow_ips=a.forwarded_allow_ips, log_level="info")
    return 0


def cmd_publish(a) -> int:
    from thusa.publish import render_public
    out(render_public(get_paths()))
    return 0


def cmd_publish_data(a) -> int:
    from thusa.publish_data import UnsafeExport, export
    try:
        out(export(get_paths(), a.out))
    except UnsafeExport as e:
        raise CliError(f"public data not written: {e}", 3)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pf", description="Thusa review app CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rv = sub.add_parser("reviewer", help="manage reviewer accounts (admin, local shell only)")
    rv.add_argument("action", choices=["add", "list", "disable", "enable", "reset-password", "token", "revoke-token"])
    rv.add_argument("username", nargs="?")
    rv.add_argument("--display-name")
    rv.add_argument("--admin", action="store_true")
    rv.add_argument("--credentials-file")
    rv.add_argument("--out", help="token file to write (token action)")
    rv.add_argument("--force", action="store_true", help="overwrite an existing credentials/token file")
    rv.add_argument("--actor", help="who is doing this (recorded in reviewer_event); default os:<user>")

    r = sub.add_parser("review", help="list, inspect and decide flags")
    rs = r.add_subparsers(dest="action", required=True)
    ls = rs.add_parser("list")
    ls.add_argument("--status")
    ls.add_argument("--detector")
    ls.add_argument("--severity", choices=["high", "med", "low", "info"])
    ls.add_argument("--named", choices=["yes", "no"])
    ls.add_argument("--q")
    ls.add_argument("--limit", type=int, default=25)
    for name in ("show", "history"):
        p = rs.add_parser(name)
        p.add_argument("flag_id")
    d = rs.add_parser("decide")
    d.add_argument("flag_id")
    d.add_argument("--decision", required=True, choices=list(wf.DECISIONS))
    d.add_argument("--reason", required=True)
    d.add_argument("--notes")
    d.add_argument("--via", choices=["cli", "bot"], default="cli")
    d.add_argument("--token-file")
    rs.add_parser("verify")
    e = rs.add_parser("export")
    e.add_argument("--format", choices=["csv", "json"], default="json")
    e.add_argument("--all", action="store_true", help="include flags with no decision yet")
    e.add_argument("--out")

    c = sub.add_parser("case", help="case referral pack for one hidden lead")
    cs = c.add_subparsers(dest="action", required=True)
    ce = cs.add_parser("export")
    ce.add_argument("flag_id")
    ce.add_argument("--out", help="output directory (default: <repo>/data/cases, gitignored)")
    ce.add_argument("--pdf", action="store_true", help="also write a PDF (needs pandoc)")

    s = sub.add_parser("serve", help="run the web app")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--allow-remote", action="store_true")
    s.add_argument("--proxy-headers", action="store_true", help="trust X-Forwarded-For from --forwarded-allow-ips")
    s.add_argument("--forwarded-allow-ips", default="127.0.0.1")

    sub.add_parser("publish", help="rebuild the public static snapshot from confirmed flags")
    pdp = sub.add_parser("publish-data", help="write the public dashboard JSON (public-data/v1/)")
    pdp.add_argument("--out", help="output directory (default: <repo>/public-data/v1)")

    a = ap.parse_args(argv)
    try:
        return {"reviewer": cmd_reviewer, "review": cmd_review, "case": cmd_case, "serve": cmd_serve, "publish": cmd_publish,
                "publish-data": cmd_publish_data}[a.cmd](a)
    except CliError as e:
        print(json.dumps({"error": str(e), "exit_code": e.code}), file=sys.stderr)
        return e.code


if __name__ == "__main__":
    raise SystemExit(main())
