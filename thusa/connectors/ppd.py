"""Procurement Payments Dashboard (BAS + LOGIS) - MANUAL DROP loader.

The dashboard is a Power BI report; the transaction list is exported from inside the report UI and there
is no documented scriptable download (checked 19 Oct 2026). We do not automate the Power BI session
(design D-07). Operator procedure: itil/knowledge/runbooks.md RB-06.

Drop files into data/drop/ppd/ as CSV exports named e.g. Procurement_Spend_Transaction_List_2026-10.csv
"""
from __future__ import annotations

from pathlib import Path

from thusa.connectors.base import IngestResult
from thusa.raw import RawStore

SOURCE_ID = "ppd_payments"
PORTAL = "https://data.etenders.gov.za/ (Procurement Payments Dashboard, Power BI export)"


def run(store: RawStore, drop_dir: Path) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    files = sorted(Path(drop_dir).glob("*.csv")) if Path(drop_dir).exists() else []
    if not files:
        res.status = "awaiting_manual_drop"
        res.notes.append(f"no CSV in {drop_dir}; see runbook RB-06")
        return res
    for f in files:
        res.files.append(store.save_file(SOURCE_ID, f.name, f, f"manual drop: {PORTAL}"))
    res.status = "unchanged" if all(f.status == "unchanged" for f in res.files) else "ok"
    return res
