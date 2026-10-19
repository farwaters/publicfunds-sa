"""Price-benchmark reference data for the public dashboard's on-the-glass utilities (CHG-2026-006).

dmpr_fuel : DMPR (via CEF) monthly fuel price adjustments. The public Fuel Prices page lists the newest documents
            first: either a "Fuel Price Adjustment Documents" ZIP or a separate "History of Fuel Prices" DOCX.
            We store whatever the page links (ZIP or DOCX) unchanged; the parser reads the history table.
oecd_cpi  : Stats SA headline CPI is the primary source, but statssa.gov.za blocks scripted access (Incapsula,
            KE-003); we do not work around that. The OECD republishes the Stats SA national CPI (index 2015=100,
            CC BY 4.0) through its public SDMX API, which we use as a clearly labelled secondary source (KE-012).
"""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

FUEL_ID = "dmpr_fuel"
FUEL_PAGE = "https://www.dmpr.gov.za/Branches/Petroleum-Resources/Fuel-Prices"
CPI_ID = "oecd_cpi"
CPI_URL = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
           "ZAF.M.N.CPI.IX._T.N._Z?startPeriod=2008-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels")

_CARD = re.compile(r"<h4>(.*?)</h4>.*?href=\"([^\"]+)\"", re.S)


def fuel_documents(page_html: str) -> list[tuple[str, str]]:
    """(title, absolute url) of the history-bearing documents on the Fuel Prices page, newest first."""
    out = []
    for m in _CARD.finditer(page_html):
        title = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", m.group(1)))).strip()
        if re.search(r"(?i)fuel price adjustment documents|history of fuel prices", title):
            out.append((title, urljoin(FUEL_PAGE, html.unescape(m.group(2)))))
    return out


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"(?i)\(zip\)", "", title).lower()).strip("-")


def run_fuel(store: RawStore, fetcher: Fetcher, max_docs: int = 1) -> IngestResult:
    res = IngestResult(FUEL_ID)
    try:
        docs = fuel_documents(fetcher.get(FUEL_PAGE).text)
        if not docs:
            raise FetchError("no 'History of Fuel Prices' or adjustment ZIP link found on the DMPR Fuel Prices page")
        for title, url in docs[:max_docs]:
            resp = fetcher.get(url)
            body = resp.content
            if not body.startswith(b"PK"):          # both DOCX and ZIP are zip containers
                raise FetchError(f"expected a ZIP/DOCX for {title!r}, got {resp.headers.get('content-type')}")
            ext = ".zip" if "documents" in title.lower() else ".docx"
            res.files.append(store.save(FUEL_ID, _slug(title) + ext, body, str(resp.url), resp.status_code))
        res.status = "unchanged" if all(f.status == "unchanged" for f in res.files) else "ok"
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", [str(exc)]
    res.requests = fetcher.requests_made
    return res


def run_cpi(store: RawStore, fetcher: Fetcher) -> IngestResult:
    res = IngestResult(CPI_ID)
    try:
        resp = fetcher.get(CPI_URL)
        if not resp.content.startswith(b"STRUCTURE,"):
            raise FetchError(f"expected SDMX CSV, got {resp.headers.get('content-type')}")
        rf = store.save(CPI_ID, "oecd_cpi_zaf_monthly.csv", resp.content, str(resp.url), resp.status_code)
        res.files.append(rf)
        res.status = "unchanged" if rf.status == "unchanged" else "ok"
        res.notes.append("secondary source: Stats SA CPI as republished by the OECD (Stats SA site blocks scripts, KE-003)")
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", [str(exc)]
    res.requests = fetcher.requests_made
    return res
