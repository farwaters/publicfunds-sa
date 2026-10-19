"""National Treasury Restricted Supplier and Tender Defaulter Report (PDF, SSRS export)."""
from __future__ import annotations

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

SOURCE_ID = "rsr"
URL = "https://ocpo.treasury.gov.za/RestrictedSupplier/RestrictedSuppliersReport.pdf"


def run(store: RawStore, fetcher: Fetcher) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    try:
        resp = fetcher.get(URL)
        if not resp.content.startswith(b"%PDF"):
            raise FetchError(f"expected PDF, got {resp.headers.get('content-type')}")
        rf = store.save(SOURCE_ID, "RestrictedSuppliersReport.pdf", resp.content, str(resp.url), resp.status_code)
        res.files.append(rf)
        res.status = "unchanged" if rf.status == "unchanged" else "ok"
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", [str(exc)]
    res.requests = fetcher.requests_made
    return res
