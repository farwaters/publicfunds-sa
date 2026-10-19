"""Auditor-General of South Africa (AGSA) general-report annexures (official Excel files, CHG-2026-011).

Annexure 1 (audit outcomes; unauthorised, irregular, fruitless and wasteful expenditure) and Annexure 3 (five-year
audit opinions) for local government (MFMA) and national/provincial government (PFMA). Each published file is
immutable, so it is fetched once and then reused from the raw store.
"""
from __future__ import annotations

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

SOURCE_ID = "agsa_annexures"
XLSX_MAGIC = b"PK\x03\x04"
_MFMA = "https://mfma-2024.agsa.co.za/report/"
_PFMA = "https://pfma-2023-24.agsa.co.za/report/"
ANNEXURES = {  # stored name -> official URL (links from each reports site's "Annexures to the report" footer)
    "mfma-2023-24-annexure-1.xlsx": _MFMA + "2023-24-MFMA-Annexure-1.xlsx",
    "mfma-2023-24-annexure-3.xlsx": _MFMA + "2023-24-MFMA-Annexure-3.xlsx",
    "pfma-2023-24-annexure-1.xlsx": _PFMA + "2023-24-Annexure%201%20-%20Audit%20outcomes.xlsx",
    "pfma-2023-24-annexure-3.xlsx": _PFMA + "2023-24-Annexure%203%20-%20Five-year%20audit%20opinions.xlsx",
}


def run(store: RawStore, fetcher: Fetcher) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    for name, url in ANNEXURES.items():
        if store.latest(SOURCE_ID, name):
            res.notes.append(f"{name}: already stored (published files do not change)")
            continue
        try:
            resp = fetcher.get(url)
            if not resp.content.startswith(XLSX_MAGIC):
                raise FetchError(f"{name}: expected an Excel file, got {resp.headers.get('content-type')}")
            res.files.append(store.save(SOURCE_ID, name, resp.content, str(resp.url), resp.status_code))
        except SourceBlocked as exc:
            res.status = "blocked"
            res.errors.append(str(exc))
            break
        except FetchError as exc:
            res.errors.append(str(exc))
    if res.status != "blocked":
        res.status = "failed" if res.errors and not res.files else "partial" if res.errors else (
            "ok" if any(f.status != "unchanged" for f in res.files) else "unchanged")
    res.requests = fetcher.requests_made
    return res
