import json

import httpx
import pytest

from thusa.connectors import muni_api, ppd, vulekamali
from thusa.http import FetchError, Fetcher, SourceBlocked
from thusa.raw import RawStore, sha256_file


def fetcher_for(handler, retries=3):
    return Fetcher(retries=retries, backoff=0.01, sleep=lambda s: None, transport=httpx.MockTransport(handler))


def test_retries_then_succeeds():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(503 if calls["n"] < 3 else 200, text="ok")
    assert fetcher_for(h).get("https://x.test/a").text == "ok" and calls["n"] == 3


def test_blocked_is_not_retried():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(403)
    with pytest.raises(SourceBlocked):
        fetcher_for(h).get("https://x.test/a")
    assert calls["n"] == 1


def test_gives_up_after_retries():
    with pytest.raises(FetchError):
        fetcher_for(lambda r: httpx.Response(500), retries=2).get("https://x.test/a")


def test_transport_errors_retried():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, text="ok")
    assert fetcher_for(h).get("https://x.test/a").text == "ok"


def test_raw_store_idempotent(tmp_path):
    s = RawStore(tmp_path)
    a = s.save("src", "f.json", b"{}", "u")
    b = s.save("src", "f.json", b"{}", "u")
    assert a.status == "ok" and b.status == "unchanged" and a.path == b.path
    assert sha256_file(s.path_of(a)) == a.sha256
    assert (s.path_of(a).parent / "f.json.sha256").read_text().startswith(a.sha256)
    c = s.save("src", "f.json", b'{"x":1}', "u")
    assert c.status == "ok" and c.sha256 != a.sha256
    assert len(s.entries()) == 3 and s.latest_files("src")[0].sha256 == c.sha256
    assert s.fresh_today("src", "f.json") is not None


def test_muni_paging_honours_server_page_size(tmp_path):
    """Facts endpoints cap page_size at 10,000 even when we ask for 20,000."""
    pages = {1: 10000, 2: 10000, 3: 5}

    def h(req):
        url = str(req.url)
        if "/facts" in url and "audit_opinions" in url:
            p = int(req.url.params["page"])
            return httpx.Response(200, json={"status": "ok", "total_fact_count": 20005, "page_size": 10000,
                                             "page": p, "data": [{}] * pages[p]})
        if "/members/financial_year_end" in url:
            return httpx.Response(200, json={"status": "ok", "data": [{"financial_year_end.year": 2024}]})
        if "/members/" in url:
            return httpx.Response(200, json={"status": "ok", "data": []})
        if "/facts" in url:
            return httpx.Response(200, json={"status": "ok", "total_fact_count": 1, "page_size": 10000, "data": [{}]})
        return httpx.Response(200, json={"status": "ok", "total_cell_count": 1, "page_size": 20000, "cells": [{}]})
    res = muni_api.run(RawStore(tmp_path), fetcher_for(h))
    names = sorted(f.name for f in res.files)
    assert res.status == "ok"
    assert [n for n in names if n.startswith("audit_opinions")] == [
        "audit_opinions_p1.json", "audit_opinions_p2.json", "audit_opinions_p3.json"]


def test_muni_partial_when_one_year_fails(tmp_path):
    def h(req):
        url = str(req.url)
        if "/members/financial_year_end" in url:
            return httpx.Response(200, json={"status": "ok", "data": [{"financial_year_end.year": 2023},
                                                                     {"financial_year_end.year": 2024}]})
        if "/members/" in url:
            return httpx.Response(200, json={"status": "ok", "data": []})
        if "incexp_v2/aggregate" in url and "2023" in req.url.params.get("cut", ""):
            return httpx.Response(500)
        key = "cells" if "aggregate" in url else "data"
        return httpx.Response(200, json={"status": "ok", "total_cell_count": 1, "total_fact_count": 1,
                                         "page_size": 10000, key: [{}]})
    res = muni_api.run(RawStore(tmp_path), fetcher_for(h, retries=1))
    assert res.status == "partial" and any("FYE 2023" in e for e in res.errors)
    assert any(f.name == "incexp_v2_fye2024_p1.json" for f in res.files)


def test_vulekamali_link_helpers():
    html = ('<a href="/datasets/budgeted-and-actual-national-expenditure/budgeted-and-actual-national-expenditure-2024">'
            '<a href="/datasets/budgeted-and-actual-national-expenditure/budgeted-and-actual-national-expenditure-2025">')
    assert vulekamali.pick_latest_year_page(html).endswith("-2025")
    assert vulekamali.csv_links('<a href="resources/A.csv"><a href="resources/A.xlsx">') == ["resources/A.csv"]


def test_ppd_manual_drop(tmp_path):
    s = RawStore(tmp_path / "raw")
    assert ppd.run(s, tmp_path / "drop").status == "awaiting_manual_drop"
    (tmp_path / "drop").mkdir()
    (tmp_path / "drop" / "x.csv").write_text("Department,Supplier,Amount\nA,B,1\n")
    r = ppd.run(s, tmp_path / "drop")
    assert r.status == "ok" and json.loads(json.dumps(r.summary()))["files"] == 1
