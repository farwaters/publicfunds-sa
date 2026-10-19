"""Municipal Finance Data API (Babbage cubes) -> raw JSON pages.

Cubes: municipalities, demarcation_changes, incexp_v2 (annual; ORGB/ADJB/AUDA/ACT x all items),
uifwexp (unauthorised / irregular / fruitless & wasteful), audit_opinions.
"""
from __future__ import annotations

import json

from thusa.connectors.base import IngestResult
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore

SOURCE_ID = "muni_api"
BASE = "https://municipaldata.treasury.gov.za/api/cubes"
AMOUNT_TYPES = ["ORGB", "ADJB", "AUDA", "ACT"]
PAGE_SIZE = 20000


def _get_json(fetcher: Fetcher, url: str, params: dict | None = None) -> tuple[dict, bytes, str]:
    resp = fetcher.get(url, params=params)
    data = resp.json()
    if isinstance(data, dict) and data.get("status") not in (None, "ok"):
        raise FetchError(f"API status {data.get('status')} for {resp.url}")
    return data, resp.content, str(resp.url)


def _paged(fetcher, store, res, name_prefix, url, params, list_key):
    page = 1
    while True:
        name = f"{name_prefix}_p{page}.json"
        cached = store.fresh_today(SOURCE_ID, name)
        if cached:
            data = json.loads(store.path_of(cached).read_bytes())
            res.files.append(cached)
        else:
            data, body, final_url = _get_json(fetcher, url, {**params, "page": page, "pagesize": PAGE_SIZE})
            res.files.append(store.save(SOURCE_ID, name, body, final_url))
        got = len(data.get(list_key, []))
        total = data.get("total_cell_count") or data.get("total_fact_count") or 0
        size = int(data.get("page_size") or PAGE_SIZE)  # facts endpoints cap page_size at 10,000
        if got == 0 or page * size >= total:
            return
        page += 1


def run(store: RawStore, fetcher: Fetcher, years: list[int] | None = None) -> IngestResult:
    res = IngestResult(SOURCE_ID)
    try:
        # reference data
        for cube in ("municipalities", "demarcation_changes"):
            _paged(fetcher, store, res, cube, f"{BASE}/{cube}/facts", {}, "data")
        for cube, dim in (("incexp_v2", "item"), ("uifwexp", "item"), ("incexp_v2", "financial_year_end")):
            data, body, url = _get_json(fetcher, f"{BASE}/{cube}/members/{dim}")
            res.files.append(store.save(SOURCE_ID, f"{cube}_members_{dim}.json", body, url))
            if cube == "incexp_v2" and dim == "financial_year_end" and years is None:
                years = sorted(int(m["financial_year_end.year"]) for m in data["data"])
        # income & expenditure, budget vs actual: one request set per financial year
        for y in years or []:
            try:
                _paged(fetcher, store, res, f"incexp_v2_fye{y}", f"{BASE}/incexp_v2/aggregate", {
                    "drilldown": "demarcation.code|financial_year_end.year|amount_type.code|item.code",
                    "cut": f'period_length.length:"year"|financial_year_end.year:{y}|amount_type.code:'
                           + ";".join(f'"{a}"' for a in AMOUNT_TYPES),
                    "aggregates": "amount.sum",
                }, "cells")
            except SourceBlocked:
                raise
            except FetchError as exc:  # keep going; one bad year must not lose the others
                res.errors.append(f"incexp_v2 FYE {y}: {exc}")
        _paged(fetcher, store, res, "uifwexp", f"{BASE}/uifwexp/aggregate", {
            "drilldown": "demarcation.code|financial_year_end.year|item.code", "aggregates": "amount.sum"}, "cells")
        _paged(fetcher, store, res, "audit_opinions", f"{BASE}/audit_opinions/facts", {}, "data")
    except SourceBlocked as exc:
        res.status, res.errors = "blocked", res.errors + [str(exc)]
    except FetchError as exc:
        res.status, res.errors = "failed", res.errors + [str(exc)]
    else:
        if res.errors:
            res.status = "partial"
        elif all(f.status == "unchanged" for f in res.files):
            res.status = "unchanged"
    res.requests = fetcher.requests_made
    return res
