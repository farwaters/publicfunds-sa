"""eTenders OCDS: bulk compiled releases (OCP Data Registry mirror) + recent delta from the eTenders API.

Bulk:  https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz  (redirects to Fastly)
Delta: https://ocds-api.etenders.gov.za/api/OCDSReleases?PageNumber=N&PageSize=100&dateFrom=..&dateTo=..
       (PageSize > 100 returns HTTP 500 as of 19 Oct 2026 -> KE-001 update)
Fallback: if the bulk download fails, the research copy in src/full.jsonl.gz is registered (same bytes
were verified on 19 Oct 2026: 11,676,874 bytes) and the run is marked partial.
"""
from __future__ import annotations

from datetime import date, timedelta

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

SOURCE_ID = "etenders_ocds"
BULK_URL = "https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz"
API_URL = "https://ocds-api.etenders.gov.za/api/OCDSReleases"
PAGE_SIZE = 100


def run(store: RawStore, fetcher: Fetcher, seed_path=None, delta_days: int = 35, max_pages: int = 120,
        today: date | None = None) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    try:
        cached = store.fresh_today(SOURCE_ID, "full.jsonl.gz")
        if cached:
            res.files.append(cached)
        else:
            resp = fetcher.get(BULK_URL)
            res.files.append(store.save(SOURCE_ID, "full.jsonl.gz", resp.content, str(resp.url), resp.status_code))
    except FetchError as exc:
        res.errors.append(f"bulk: {exc}")
        if seed_path and seed_path.exists():
            res.files.append(store.save_file(SOURCE_ID, "full.jsonl.gz", seed_path, BULK_URL + " (seed copy)"))
            res.notes.append("bulk download failed; registered research seed copy")
    today = today or date.today()
    start = today - timedelta(days=delta_days)
    window = f"{start.isoformat()}_{today.isoformat()}"
    for page in range(1, max_pages + 1):
        name = f"delta_{window}_p{page:03d}.json"
        try:
            cached = store.fresh_today(SOURCE_ID, name)
            if cached:
                body = store.path_of(cached).read_bytes()
                res.files.append(cached)
            else:
                resp = fetcher.get(API_URL, params={"PageNumber": page, "PageSize": PAGE_SIZE,
                                                    "dateFrom": start.isoformat(), "dateTo": today.isoformat()})
                body = resp.content
                res.files.append(store.save(SOURCE_ID, name, body, str(resp.url), resp.status_code))
        except SourceBlocked as exc:
            res.errors.append(f"delta blocked: {exc}")
            break
        except FetchError as exc:
            res.errors.append(f"delta page {page}: {exc}")
            break
        import json

        data = json.loads(body)
        if len(data.get("releases", [])) < PAGE_SIZE or not (data.get("links") or {}).get("next"):
            break
    else:
        res.notes.append(f"delta stopped at max_pages={max_pages}")
    if res.errors:
        res.status = "partial" if res.files else "failed"
    elif all(f.status == "unchanged" for f in res.files):
        res.status = "unchanged"
    res.requests = fetcher.requests_made
    return res
