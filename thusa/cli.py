"""Thusa command line: `thusa run` = ingest -> build -> report (the daily routine, ADR-0001)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone

from thusa.settings import get_paths

SOURCES = ["muni_api", "etenders_ocds", "rsr", "ppd_payments", "nt_budget"]


def ingest(only: list[str] | None = None, refresh: bool = False) -> list[dict]:
    from thusa.build import git_sha
    from thusa.connectors import muni_api, ocds, ppd, rsr, vulekamali
    from thusa.http import Fetcher
    from thusa.raw import RawStore, log_run

    p = get_paths()
    store = RawStore(p.raw, resume=not refresh)
    runners = {
        "muni_api": lambda: muni_api.run(store, Fetcher()),
        "etenders_ocds": lambda: ocds.run(store, Fetcher(), seed_path=p.seed / "full.jsonl.gz"),
        "rsr": lambda: rsr.run(store, Fetcher()),
        "ppd_payments": lambda: ppd.run(store, p.drop / "ppd"),
        "nt_budget": lambda: vulekamali.run(store, Fetcher(retries=1)),
    }
    out = []
    for sid in only or SOURCES:
        started = datetime.now(timezone.utc)
        res = runners[sid]()
        rec = {"run_id": started.strftime(f"I%Y%m%dT%H%M%SZ-{sid}"), "started_at_utc": started.isoformat(),
               "ended_at_utc": datetime.now(timezone.utc).isoformat(), "git_commit": git_sha(p.root), **res.summary()}
        log_run(p.raw, rec)
        print(json.dumps(rec), flush=True)
        out.append(rec)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="thusa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("--only", help="comma-separated source ids")
    i.add_argument("--refresh", action="store_true", help="refetch even if today's raw copy exists")
    b = sub.add_parser("build")
    b.add_argument("--as-of", type=date.fromisoformat)
    sub.add_parser("report")
    r = sub.add_parser("run")
    r.add_argument("--as-of", type=date.fromisoformat)
    r.add_argument("--refresh", action="store_true")
    r.add_argument("--only", help="comma-separated source ids")
    a = ap.parse_args(argv)
    if a.cmd in ("ingest", "run"):
        ingest(a.only.split(",") if getattr(a, "only", None) else None, refresh=getattr(a, "refresh", False))
    summary = None
    if a.cmd in ("build", "run"):
        from thusa.build import build
        summary = build(get_paths(), as_of=a.as_of)
        print(json.dumps({k: summary[k] for k in ("build_id", "rows", "flags", "dq")}, indent=1, default=str))
    if a.cmd in ("report", "run"):
        from thusa.report import render
        print(json.dumps(render(get_paths()), indent=1, default=str))
    if summary and summary["dq"]["fail"]:
        print("DATA-QUALITY FAILURES - build is not releasable", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
