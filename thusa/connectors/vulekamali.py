"""Vulekamali budget data.

The CKAN datastore/API (data.vulekamali.gov.za) fails TLS on 19 Oct 2026 (KE-002); we do not work around it.
The public dataset pages on vulekamali.gov.za still link resource files, so we fetch the latest
'Budgeted and Actual National Expenditure' CSV from there (national departments: main, adjusted and
final appropriation and audit outcome by programme / economic classification).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

SOURCE_ID = "nt_budget"
CKAN_STATUS = "https://data.vulekamali.gov.za/api/3/action/status_show"
DATASET = "https://vulekamali.gov.za/datasets/budgeted-and-actual-national-expenditure"


def pick_latest_year_page(html: str) -> str | None:
    years = re.findall(r'href="(/datasets/budgeted-and-actual-national-expenditure/'
                       r'budgeted-and-actual-national-expenditure-(\d{4}))"', html)
    return max(years, key=lambda t: int(t[1]))[0] if years else None


def csv_links(html: str) -> list[str]:
    return sorted(set(re.findall(r'href="(resources/[^"]+\.csv)"', html)))


def run(store: RawStore, fetcher: Fetcher) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    try:
        fetcher.get(CKAN_STATUS)
        res.notes.append("CKAN API reachable")
    except FetchError as exc:
        res.notes.append(f"CKAN API unavailable (KE-002): {exc}")
    try:
        listing = fetcher.get(DATASET).text
        page = pick_latest_year_page(listing)
        if not page:
            raise FetchError("no yearly resource page found on dataset listing")
        page_url = urljoin("https://vulekamali.gov.za", page)
        html = fetcher.get(page_url).text
        links = csv_links(html)
        if not links:
            raise FetchError(f"no CSV resources on {page_url}")
        for rel in links:
            # resource hrefs are relative to the dataset (not the year page): verified 19 Oct 2026
            url = f"{DATASET}/{rel}"
            resp = fetcher.get(url)
            if "text/html" in resp.headers.get("content-type", ""):
                raise FetchError(f"{url} returned HTML, not CSV")
            res.files.append(store.save(SOURCE_ID, rel.split("/")[-1], resp.content, str(resp.url),
                                        resp.status_code))
        res.status = "unchanged" if all(f.status == "unchanged" for f in res.files) else "ok"
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", [str(exc)]
    res.requests = fetcher.requests_made
    return res
