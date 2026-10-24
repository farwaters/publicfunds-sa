"""CHG-2026-035: read-only month-continuity report for curated.fuel_price (DMPR fuel history).

  uv run python scripts/fuel_continuity.py [--warehouse PATH]

Prints the first and last month present, the months missing between them split into expected known gaps
(`thusa.dq.FUEL_KNOWN_GAPS`) and NEW gaps, and known gaps that are now present (stale entries). Opens the warehouse
read-only; writes nothing. Exit 1 if there is a NEW gap or a stale entry, else 0 (the build's own check,
`fuel_month_continuity_info`, only warns)."""
import argparse
import sys

import duckdb

from thusa import dq
from thusa.settings import get_paths


def fmt(ym) -> str:
    return f"{ym[0]}-{ym[1]:02d}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", default=None, help="path to the DuckDB warehouse (default: this checkout's data/)")
    a = ap.parse_args(argv)
    path = a.warehouse or str(get_paths().warehouse)
    con = duckdb.connect(path, read_only=True)
    try:
        c = dq.fuel_continuity(con)
    finally:
        con.close()
    if c["first"] is None:
        print("fuel months: none in curated.fuel_price")
        return 1
    print(f"fuel months: {fmt(c['first'])} to {fmt(c['last'])}, {c['present']} present, {len(c['missing'])} missing")
    for g in c["expected"]:
        print(f"expected known gap: {fmt(g)} ({dq.FUEL_KNOWN_GAPS[g]})")
    for g in c["new"]:
        print(f"NEW gap: {fmt(g)}")
    for g in c["stale_known"]:
        print(f"STALE allow-list entry (month is present): {fmt(g)}")
    bad = len(c["new"]) + len(c["stale_known"])
    print("fuel continuity: " + ("OK" if not bad else f"{len(c['new'])} NEW gap(s), {len(c['stale_known'])} stale entry(ies)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
