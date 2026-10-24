"""CHG-2026-027 gate: do the figures in DMPR's monthly '<Month>-2025-Fuel-Regulations.xlsx' equal the yearly
Fuel-Price-History PDF rows for the same month and grade?  Prints one table; exit 1 if any grade differs.

  uv run python scripts/fuel_xlsx_crosscheck.py --fetch      # download Jan-Nov 2025 to data/xcheck/ (public files)
  uv run python scripts/fuel_xlsx_crosscheck.py              # compare with the stored 2025 history PDF

The downloaded workbooks stay in data/xcheck/ (git-ignored, outside the raw store and the warehouse); the manifest
there records URL, sha256 and fetch time. Only cells are read; document properties are never opened."""
import argparse
import json
import sys
from datetime import datetime, timezone

from thusa import parsers
from thusa.connectors import prices
from thusa.http import Fetcher
from thusa.raw import RawStore, sha256_bytes
from thusa.settings import get_paths

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--months", default=",".join(MONTHS))
    ap.add_argument("--gate-month", type=int, default=11, help="a mismatch here fails the run (default 11 = November); "
                    "mismatches in other months are printed as observations only")
    a = ap.parse_args()
    p = get_paths()
    xdir = p.data / "xcheck"
    names = [f"{m}-2025-Fuel-Regulations.xlsx" for m in a.months.split(",")]
    if a.fetch:
        xdir.mkdir(parents=True, exist_ok=True)
        f, man = Fetcher(retries=2), {}
        for n in names:
            m = n.split("-")[0]
            r = f.get(prices._XLSX.format(y=2025, m=m))
            if not r.content.startswith(b"PK"):
                print(f"{n}: not a workbook", file=sys.stderr)
                return 1
            (xdir / n).write_bytes(r.content)
            man[n] = {"url": str(r.url), "sha256": sha256_bytes(r.content),
                      "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        (xdir / "manifest.json").write_text(json.dumps(man, indent=1))
    pdf_f = RawStore(p.raw).latest("dmpr_fuel", "fuel-price-history-2025.pdf")
    pdf = {(r["month"], r["grade"]): r["cents_per_litre"] for r in parsers.fuel_history_pdf_rows(
        (p.raw / pdf_f.path).read_bytes(), "fuel-price-history-2025.pdf")}
    bad = other = 0
    print("month | grade | xlsx | history PDF | equal")
    for n in names:
        for r in parsers.fuel_regulations_xlsx_rows((xdir / n).read_bytes(), n):
            h = pdf.get((r["month"], r["grade"]))
            ok = h == r["cents_per_litre"]
            gate = r["month"] == a.gate_month
            bad += (not ok) and gate
            other += (not ok) and not gate
            print(f"2025-{r['month']:02d} | {r['grade']} | {r['cents_per_litre']} | {h} | "
                  f"{'yes' if ok else ('NO (GATE)' if gate else 'NO (observation)')}")
    print(f"GATE MISMATCHES (month {a.gate_month}): {bad}; other-month observations: {other}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
