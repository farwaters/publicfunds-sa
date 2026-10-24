"""Price-benchmark reference data for the public dashboard's on-the-glass utilities (CHG-2026-006).

dmpr_fuel : DMPR (via CEF) monthly fuel price adjustments. The public Fuel Prices page lists the newest documents
            first: either a "Fuel Price Adjustment Documents" ZIP or a separate "History of Fuel Prices" DOCX.
            We store whatever the page links (ZIP or DOCX) unchanged; the parser reads the history table.
oecd_cpi  : Stats SA headline CPI is the primary source, but statssa.gov.za blocks scripted access (Incapsula,
            KE-003); we do not work around that. The OECD republishes the Stats SA national CPI (index 2015=100,
            CC BY 4.0) through its public SDMX API, which we use as a clearly labelled secondary source (KE-012).
imf_cpi   : the OECD series lags (last month 2025-01). The IMF CPI dataset (IMF.STA:CPI, public SDMX API, IMF
            "Special Terms for Statistical Data": reuse with attribution) carries the Stats SA headline index on
            Stats SA's current base (Dec 2024 = 100) to the latest month (CHG-2026-018, CSI-031). When loaded it is
            the curated CPI series; the OECD series stays as the fallback.
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

IMF_CPI_ID = "imf_cpi"
IMF_CPI_URL = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/ZAF.CPI._T.IX.M?startPeriod=2008-01"

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


# Earlier years: DMPR's own yearly "Fuel Price History" PDFs (same table as the current-year DOCX), linked from the
# DMPR site; URLs checked 20 Oct 2026 (2025 ends at November; 2015-2018 are not at this path). CHG-2026-009, KE-012.
_HIST = "https://www.dmpr.gov.za/Portals/0/Resources/Fuel%20Prices%20Adjustments/Fuel%20Prices%20Per%20Zone/{y}/{m}%20{y}/Fuel-Price-History.pdf"
FUEL_HISTORY_PDFS = {y: _HIST.format(y=y, m="December") for y in range(2019, 2025)} | {2025: _HIST.format(y=2025, m="November")}


def run_fuel_history(store: RawStore, fetcher: Fetcher, res: IngestResult) -> None:
    """Fetch each past year's history PDF once (they no longer change); a failed year is noted, not fatal."""
    for year, url in sorted(FUEL_HISTORY_PDFS.items()):
        name = f"fuel-price-history-{year}.pdf"
        if store.latest(FUEL_ID, name):
            continue
        try:
            resp = fetcher.get(url)
            if not resp.content.startswith(b"%PDF"):
                raise FetchError(f"expected a PDF, got {resp.headers.get('content-type')}")
            res.files.append(store.save(FUEL_ID, name, resp.content, str(resp.url), resp.status_code))
        except (SourceBlocked, FetchError) as exc:
            res.notes.append(f"fuel price history {year}: {exc}")


# CHG-2026-027: no December 2025 history table exists at the yearly-PDF address (the 2025 PDF ends at November and
# the current-year DOCX covers 2026 only), so 2025-12 is read from DMPR's own 'December-2025-Fuel-Regulations.xlsx'
# (DMPR Petrol Price Archive page; the page's link goes through a broken /uat1/ path, the normal /Portals/ path is
# the public file). Only gap months are listed here: other months stay with the history PDFs. Source type: DMPR
# fuel regulations xlsx (government public information; DMPR Terms & Conditions: free reproduction if accurate and
# the source URL and copyright status are acknowledged).
_XLSX = ("https://www.dmpr.gov.za/Portals/0/Resources/Fuel%20Prices%20Adjustments/Fuel%20Prices%20Per%20Zone/"
         "{y}/{m}%20{y}/{m}-{y}-Fuel-Regulations.xlsx")
FUEL_REGULATIONS_XLSX = {"December-2025-Fuel-Regulations.xlsx": _XLSX.format(y=2025, m="December")}


def run_fuel_regulations_xlsx(store: RawStore, fetcher: Fetcher, res: IngestResult) -> None:
    """Fetch each gap-month workbook once (the file is a past month's regulations); a failure is noted, not fatal."""
    for name, url in sorted(FUEL_REGULATIONS_XLSX.items()):
        if store.latest(FUEL_ID, name):
            continue
        try:
            resp = fetcher.get(url)
            if not resp.content.startswith(b"PK"):
                raise FetchError(f"expected an xlsx workbook, got {resp.headers.get('content-type')}")
            res.files.append(store.save(FUEL_ID, name, resp.content, str(resp.url), resp.status_code))
        except (SourceBlocked, FetchError) as exc:
            res.notes.append(f"fuel regulations xlsx {name}: {exc}")


def run_fuel(store: RawStore, fetcher: Fetcher, max_docs: int = 1) -> IngestResult:
    res = IngestResult(FUEL_ID)
    run_fuel_history(store, fetcher, res)
    run_fuel_regulations_xlsx(store, fetcher, res)
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


def run_imf_cpi(store: RawStore, fetcher: Fetcher) -> IngestResult:
    res = IngestResult(IMF_CPI_ID)
    try:
        resp = fetcher.get(IMF_CPI_URL)
        if b"StructureSpecificData" not in resp.content[:2000]:
            raise FetchError(f"expected SDMX-ML data, got {resp.headers.get('content-type')}")
        rf = store.save(IMF_CPI_ID, "imf_cpi_zaf_monthly.xml", resp.content, str(resp.url), resp.status_code)
        res.files.append(rf)
        res.status = "unchanged" if rf.status == "unchanged" else "ok"
        res.notes.append("secondary source: Stats SA headline CPI (Dec 2024=100) as republished by the IMF CPI dataset")
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", [str(exc)]
    res.requests = fetcher.requests_made
    return res
