"""Build the warehouse from raw files: staging -> curated -> marts (coverage) -> flags -> DQ.

Plain SQL models executed in filename order (ADR-0007). The warehouse is rebuilt from scratch on every
run, so builds are deterministic and idempotent for a given set of raw files.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from thusa import detectors, dq, staging
from thusa.raw import RawStore
from thusa.settings import Paths, detector_config, hmac_secret

MODELS = Path(__file__).parent / "models"


def git_sha(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def run_sql_dir(con, sub: str) -> list[str]:
    done = []
    for f in sorted((MODELS / sub).glob("*.sql")):
        con.execute(f.read_text())
        done.append(f"{sub}/{f.name}")
    return done


def load_runs(con, raw_dir: Path) -> None:
    con.execute("""CREATE OR REPLACE TABLE ops.ingest_run (run_id VARCHAR, source_id VARCHAR, started_at_utc TIMESTAMPTZ,
        ended_at_utc TIMESTAMPTZ, status VARCHAR, files INTEGER, new_files INTEGER, bytes BIGINT, requests INTEGER,
        errors VARCHAR, notes VARCHAR, git_commit VARCHAR)""")
    f = raw_dir / "runs.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                con.execute("INSERT INTO ops.ingest_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
                    r.get("run_id"), r.get("source_id"), r.get("started_at_utc"), r.get("ended_at_utc"),
                    r.get("status"), r.get("files"), r.get("new_files"), r.get("bytes"), r.get("requests"),
                    json.dumps(r.get("errors", [])), json.dumps(r.get("notes", [])), r.get("git_commit")])


def build(paths: Paths, as_of: date | None = None, fye_min: int = 2020, fye_max: int = 2026,
          min_rows: dict | None = None, secret: bytes | None = None) -> dict:
    as_of = as_of or date.today()
    build_id = datetime.now(timezone.utc).strftime("B%Y%m%dT%H%M%SZ")
    paths.warehouse.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.warehouse.with_suffix(".building.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    for s in ("ops", "staging", "curated", "marts"):
        con.execute(f"CREATE SCHEMA {s}")
    store = RawStore(paths.raw)
    summary: dict = {"build_id": build_id, "as_of": as_of.isoformat(), "git_commit": git_sha(paths.root),
                     "fye_range": [fye_min, fye_max], "rows": {}}
    summary["raw_files"] = staging.load_raw_files(con, store)
    load_runs(con, paths.raw)
    sdir = paths.staging_files
    summary["rows"].update(staging.stage_muni(con, store, sdir))
    summary["rows"].update(staging.stage_ocds(con, store, sdir))
    summary["rows"].update(staging.stage_rsr(con, store, sdir, secret or hmac_secret()))
    summary["rows"].update(staging.stage_nt_budget(con, store, sdir))
    summary["rows"].update(staging.stage_ppd(con, store, sdir))
    summary["rows"].update(staging.stage_prices(con, store, sdir))
    summary["rows"].update(staging.stage_agsa(con, store, sdir))
    summary["models"] = run_sql_dir(con, "curated")
    con.execute(f"SET VARIABLE as_of = DATE '{as_of.isoformat()}'")
    con.execute(f"SET VARIABLE fye_min = {int(fye_min)}")
    con.execute(f"SET VARIABLE fye_max = {int(fye_max)}")
    summary["models"] += run_sql_dir(con, "marts")
    summary["flags"] = detectors.build(con, detector_config(), build_id)
    for t in ("curated.gov_body", "curated.muni_fin_line", "curated.nat_budget_line", "curated.uifw_line",
              "curated.audit_outcome", "curated.award", "curated.ocds_release", "curated.restriction",
              "curated.payment", "curated.fuel_price", "curated.cpi", "curated.agsa_audit_outcome",
              "curated.agsa_uifw", "marts.coverage_cell", "marts.flag"):
        summary["rows"][t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    results = dq.run(con, build_id, min_rows, raw_root=paths.root)
    summary["dq"] = {"pass": sum(r["status"] == "pass" for r in results),
                     "warn": sum(r["status"] == "warn" for r in results),
                     "fail": [r for r in results if r["status"] not in ("pass", "warn")]}
    con.execute("CREATE TABLE ops.build AS SELECT ? AS build_id, ?::JSON AS summary",
                [build_id, json.dumps(summary, default=str)])
    con.close()
    tmp.replace(paths.warehouse)  # atomic swap: readers never see a half-built warehouse
    return summary
