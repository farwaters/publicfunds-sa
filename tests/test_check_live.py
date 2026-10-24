"""scripts/check_live.py (CHG-2026-032, CSI-036, SLO-PD-1): local HTTP server fixtures, no real network."""
import functools
import hashlib
import importlib.util
import json
import socket
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("check_live", Path(__file__).resolve().parents[1] / "scripts" / "check_live.py")
cl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cl)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone(timedelta(hours=2)))
FILES = {"municipalities.json": b'{"m": 1}', "departments.json": b'{"d": 2}', "prices.json": b'{"p": 3}'}


def manifest(age_hours=8.0, build="B1", files=FILES):
    ts = (NOW - timedelta(hours=age_hours)).isoformat()
    return {"generated_at_sast": ts, "build": {"id": build},
            "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()]}


class Site:
    """Tiny mutable site: routes maps path -> (status, bytes); fail_first maps path -> number of 500s before success."""

    def __init__(self):
        self.routes, self.fail_first, self.hits = {}, {}, {}
        site = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                site.hits[self.path] = site.hits.get(self.path, 0) + 1
                if site.fail_first.get(self.path, 0) > 0:
                    site.fail_first[self.path] -= 1
                    self.send_response(500); self.end_headers(); return
                status, body = site.routes.get(self.path, (404, b""))
                self.send_response(status); self.end_headers(); self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def healthy(self, **kw):
        self.routes = {"/": (200, b"<html>redirect</html>"), "/apps/public-dashboard/": (200, b"<title>PublicFunds SA</title>"),
                       cl.MANIFEST_PATH: (200, json.dumps(manifest(**kw)).encode())}
        for n, b in FILES.items():
            self.routes[f"/public-data/v1/{n}"] = (200, b)
        return self

    def set_manifest(self, **kw):
        self.routes[cl.MANIFEST_PATH] = (200, json.dumps(manifest(**kw)).encode())


@pytest.fixture
def site():
    s = Site().healthy()
    yield s
    s.srv.shutdown(); s.srv.server_close()


def run(site_url, **kw):
    kw.setdefault("retries", 0); kw.setdefault("retry_delay", 0); kw.setdefault("timeout", 3)
    return {n: (s, d) for n, s, d in cl.run_checks(site_url, now_fn=lambda: NOW, **kw)}


def statuses(res):
    return {n: s for n, (s, _) in res.items()}


def test_healthy_site_is_ok(site):
    res = run(site.url)
    assert set(statuses(res).values()) == {cl.OK}
    assert {"site.home", "site.app", "site.manifest", "site.age", "site.file.municipalities.json"} <= set(res)
    assert cl.summarise([(n, s, d) for n, (s, d) in res.items()]) == ("OK", 0)


def test_stale_manifest_breaches_slo(site):
    site.set_manifest(age_hours=49)
    res = run(site.url)
    assert res["site.age"][0] == cl.BREACH and "49.0 h" in res["site.age"][1] and "SLO-PD-1" in res["site.age"][1]
    assert cl.summarise([(n, s, d) for n, (s, d) in res.items()])[1] == 1


def test_exactly_48h_is_within_slo_and_30_to_48_warns(site):
    site.set_manifest(age_hours=48)
    assert run(site.url)["site.age"][0] == cl.WARN
    site.set_manifest(age_hours=31)
    res = run(site.url)
    assert res["site.age"][0] == cl.WARN and "early warning" in res["site.age"][1]
    assert cl.summarise([(n, s, d) for n, (s, d) in res.items()]) == ("WARN (1)", 0)
    site.set_manifest(age_hours=29)
    assert run(site.url)["site.age"][0] == cl.OK


def test_thresholds_are_arguments(site):
    site.set_manifest(age_hours=10)
    assert run(site.url, max_age_hours=6, warn_age_hours=3)["site.age"][0] == cl.BREACH


def test_future_timestamp_breaches_but_small_skew_is_fine(site):
    site.set_manifest(age_hours=-2)
    assert run(site.url)["site.age"][0] == cl.BREACH
    site.set_manifest(age_hours=-0.05)
    assert run(site.url)["site.age"][0] == cl.OK


def test_timestamp_problems_are_breaches(site):
    for bad in ("not a date", None, "2026-10-24T03:05:16"):  # unreadable, missing, no UTC offset
        m = manifest(); m["generated_at_sast"] = bad
        if bad is None:
            del m["generated_at_sast"]
        site.routes[cl.MANIFEST_PATH] = (200, json.dumps(m).encode())
        assert run(site.url)["site.age"][0] == cl.BREACH


@pytest.mark.parametrize("body,status", [(b"", 404), (b"<html>oops</html>", 200), (b"[1, 2]", 200), (b"", 500)])
def test_bad_manifest_responses_breach(site, body, status):
    site.routes[cl.MANIFEST_PATH] = (status, body)
    res = run(site.url)
    assert res["site.manifest"][0] == cl.BREACH and "site.age" not in res


def test_home_and_app_failures(site):
    site.routes["/"] = (503, b"")
    site.routes["/apps/public-dashboard/"] = (200, b"<title>Parked domain</title>")
    res = run(site.url)
    assert res["site.home"][0] == cl.BREACH and res["site.app"][0] == cl.BREACH


def test_unreachable_site_breaches_everything():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]  # closed port after the socket closes
    res = run(f"http://127.0.0.1:{port}")
    assert {"site.home", "site.app", "site.manifest"} <= set(res) and set(statuses(res).values()) == {cl.BREACH}
    assert "unreachable" in res["site.home"][1]


def test_retry_rides_out_a_transient_500(site):
    site.fail_first[cl.MANIFEST_PATH] = 2
    assert run(site.url, retries=0)["site.manifest"][0] == cl.BREACH
    site.fail_first[cl.MANIFEST_PATH] = 2
    assert run(site.url, retries=2)["site.manifest"][0] == cl.OK


def test_404_is_not_retried(site):
    site.routes["/"] = (404, b"")
    run(site.url, retries=2)
    assert site.hits["/"] == 1


def test_sample_file_checksum_and_missing(site):
    site.routes["/public-data/v1/prices.json"] = (200, b'{"p": 999}')
    site.routes["/public-data/v1/departments.json"] = (404, b"")
    res = run(site.url)
    assert res["site.file.prices.json"][0] == cl.BREACH and "differ" in res["site.file.prices.json"][1]
    assert res["site.file.departments.json"][0] == cl.BREACH
    assert res["site.file.municipalities.json"][0] == cl.OK
    res = run(site.url, sample_files="nope.json")
    assert res["site.file.nope.json"][0] == cl.BREACH and "not listed" in res["site.file.nope.json"][1]


def test_raw_manifest_same_build_older_or_missing(site):
    raw = Site().healthy()
    try:
        url = raw.url + cl.MANIFEST_PATH
        res = run(site.url, raw_url=url)
        assert res["raw.manifest"][0] == cl.OK and res["raw.age"][0] == cl.OK
        raw.set_manifest(build="B2")
        assert run(site.url, raw_url=url)["raw.manifest"][0] == cl.WARN
        raw.set_manifest(age_hours=60, build="B1")
        assert run(site.url, raw_url=url)["raw.age"][0] == cl.BREACH
        raw.routes.pop(cl.MANIFEST_PATH)
        assert run(site.url, raw_url=url)["raw.manifest"][0] == cl.BREACH
    finally:
        raw.srv.shutdown(); raw.srv.server_close()


def test_no_raw_checks_without_raw_url(site):
    assert not [n for n in run(site.url) if n.startswith("raw.")]


def _local(tmp_path, build):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest(build=build)))
    return str(p)


def test_expect_local_match_mismatch_and_unreadable(site, tmp_path):
    assert run(site.url, expect_local=_local(tmp_path, "B1"))["local.build"][0] == cl.OK
    res = run(site.url, expect_local=_local(tmp_path, "B9"), wait=0)
    assert res["local.build"][0] == cl.BREACH and "B1" in res["local.build"][1] and "B9" in res["local.build"][1]
    assert run(site.url, expect_local=str(tmp_path / "missing.json"))["local.build"][0] == cl.BREACH


def test_expect_local_waits_for_pages_to_deploy(site, tmp_path):
    threading.Timer(0.3, lambda: site.set_manifest(build="B9")).start()
    res = run(site.url, expect_local=_local(tmp_path, "B9"), wait=5, poll=0.1)
    assert res["local.build"][0] == cl.OK


def test_main_exit_codes_text_and_json(site, capsys, monkeypatch):
    monkeypatch.setattr(cl, "run_checks", functools.partial(cl.run_checks, now_fn=lambda: NOW))  # fixed clock
    args = ["--site", site.url, "--retries", "0", "--retry-delay", "0"]
    assert cl.main(args) == 0
    out = capsys.readouterr().out
    assert "RESULT: OK" in out and "SAST" in out and "[OK] site.manifest" in out
    site.set_manifest(age_hours=400)
    assert cl.main(args + ["--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["result"].startswith("BREACH") and any(c["status"] == "BREACH" for c in data["checks"])
    assert "SAST" in data["checked_at"]


def test_script_is_stdlib_only_and_sends_no_credentials():
    src = (Path(cl.__file__)).read_text()
    for banned in ("import httpx", "import requests", "Authorization", "Cookie", "environ", "getenv"):
        assert banned not in src
