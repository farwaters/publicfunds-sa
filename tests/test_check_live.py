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


def manifest(age_hours=8.0, build="B1", files=FILES, tz=None):
    ts = (NOW - timedelta(hours=age_hours)).astimezone(tz or NOW.tzinfo).isoformat()
    return {"generated_at_sast": ts, "build": {"id": build},
            "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()]}


class Site:
    """Tiny mutable site: routes maps path -> (status, bytes[, headers]); fail_first maps path -> number of 500s before success."""

    def __init__(self):
        self.routes, self.fail_first, self.hits = {}, {}, {}
        site = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                site.hits[self.path] = site.hits.get(self.path, 0) + 1
                if site.fail_first.get(self.path, 0) > 0:
                    site.fail_first[self.path] -= 1
                    self.send_response(500); self.end_headers(); return
                status, body, *extra = site.routes.get(self.path, (404, b""))
                headers = dict(extra[0]) if extra else {}
                truncate = headers.pop("X-Truncate", None)  # promise more bytes than are sent, then hang up
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                if truncate:
                    self.send_header("Content-Length", str(len(body) + 50))
                self.end_headers(); self.wfile.write(body)

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


def test_sample_file_missing_and_unlisted(site):
    site.routes["/public-data/v1/departments.json"] = (404, b"")
    res = run(site.url)
    assert res["site.file.departments.json"][0] == cl.BREACH
    assert res["site.file.municipalities.json"][0] == cl.OK
    res = run(site.url, sample_files="nope.json")
    assert res["site.file.nope.json"][0] == cl.BREACH and "not listed" in res["site.file.nope.json"][1]


def test_same_length_corrupt_body_is_caught_by_the_sha_check_alone(site):
    assert len(b'{"p": 9}') == len(FILES["prices.json"])  # same byte count, different content
    site.routes["/public-data/v1/prices.json"] = (200, b'{"p": 9}')
    res = run(site.url)
    assert res["site.file.prices.json"][0] == cl.BREACH and "sha256 differs" in res["site.file.prices.json"][1]
    assert res["site.file.municipalities.json"][0] == cl.OK


def test_wrong_byte_count_is_caught_by_the_length_check_alone(site):
    m = manifest()
    for f in m["files"]:
        if f["name"] == "prices.json":
            f["bytes"] += 1  # the sha256 in the manifest is still the right one for the served body
    site.routes[cl.MANIFEST_PATH] = (200, json.dumps(m).encode())
    res = run(site.url)
    assert res["site.file.prices.json"][0] == cl.BREACH and "bytes" in res["site.file.prices.json"][1]
    assert "sha256" not in res["site.file.prices.json"][1]


def test_shorter_corrupt_body_breaches(site):
    site.routes["/public-data/v1/prices.json"] = (200, b'{"p": 999}')
    assert run(site.url)["site.file.prices.json"][0] == cl.BREACH


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


def test_raw_manifest_with_missing_build_ids_is_not_ok(site):
    raw = Site().healthy()
    try:
        url = raw.url + cl.MANIFEST_PATH
        for site_build, raw_build in ((None, None), ("B1", None), (None, "B1")):
            site.set_manifest(build=site_build); raw.set_manifest(build=raw_build)
            status, detail = run(site.url, raw_url=url)["raw.manifest"]
            assert status == cl.WARN and "cannot confirm the same build" in detail
        site.set_manifest(build="B1"); raw.set_manifest(build="B1")
        assert run(site.url, raw_url=url)["raw.manifest"][0] == cl.OK
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


OLD_FILES = {**FILES, "prices.json": b'{"p": 3}'}
NEW_FILES = {**FILES, "prices.json": b'{"p": 33, "new": true}'}  # different length and sha256 from the old build's file


def test_expect_local_wait_rechecks_age_and_files_on_the_manifest_fetched_after_the_wait(site, tmp_path):
    # Before the wait: the OLD build (stale, listing the old prices.json). After: the NEW build lists a different
    # prices.json (other bytes and sha256) and the site serves that. Only the post-wait manifest agrees with what is
    # served, so using the pre-wait manifest for the file checks (or the age check) fails this test.
    site.set_manifest(build="B1", age_hours=60, files=OLD_FILES)
    site.routes["/public-data/v1/prices.json"] = (200, OLD_FILES["prices.json"])

    def deploy():  # Pages finishes deploying: the new, fresh build, its manifest and its files
        site.set_manifest(build="B9", age_hours=1, files=NEW_FILES)
        site.routes["/public-data/v1/prices.json"] = (200, NEW_FILES["prices.json"])
    threading.Timer(0.3, deploy).start()
    res = run(site.url, expect_local=_local(tmp_path, "B9"), wait=5, poll=0.1)
    assert res["local.build"][0] == cl.OK
    assert res["site.age"][0] == cl.OK and "1.0 h" in res["site.age"][1]  # not the 60 h of the pre-wait manifest
    assert res["site.file.prices.json"] == (cl.OK, f"{len(NEW_FILES['prices.json'])} bytes, sha256 matches the manifest")
    assert all(s == cl.OK for s in statuses(res).values())
    assert "build B9" in res["site.manifest"][1]


def test_expect_local_wait_that_never_succeeds_still_reports_age_and_files(site, tmp_path):
    site.set_manifest(build="B1", age_hours=60)
    res = run(site.url, expect_local=_local(tmp_path, "B9"), wait=0.3, poll=0.1)
    assert res["local.build"][0] == cl.BREACH and res["site.age"][0] == cl.BREACH


def test_wait_with_zero_poll_does_not_busy_loop(site, tmp_path):
    site.set_manifest(build="B1")
    before = site.hits.get(cl.MANIFEST_PATH, 0)
    res = run(site.url, expect_local=_local(tmp_path, "B9"), wait=0.5, poll=0)
    polls = site.hits[cl.MANIFEST_PATH] - before
    assert res["local.build"][0] == cl.BREACH
    assert 2 <= polls <= 0.5 / cl.MIN_POLL + 3  # polled, but never faster than MIN_POLL


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


# ---- odd manifests, truncated bodies, other parsing errors: BREACH line, RESULT line, exit 1, never a traceback ----

def _main_default_site(monkeypatch, site, extra=()):
    monkeypatch.setattr(cl, "run_checks", functools.partial(cl.run_checks, now_fn=lambda: NOW))
    return cl.main(["--site", site.url, "--retries", "0", "--retry-delay", "0", *extra])


@pytest.mark.parametrize("files", [None, {"municipalities.json": 1}, "municipalities.json", 7, [1, "x", None]])
def test_manifest_files_not_a_usable_list_is_a_breach(site, capsys, monkeypatch, files):
    m = manifest(); m["files"] = files
    site.routes[cl.MANIFEST_PATH] = (200, json.dumps(m).encode())
    rc = _main_default_site(monkeypatch, site)
    out = capsys.readouterr().out
    assert rc == 1 and "Traceback" not in out and "RESULT: BREACH" in out
    if isinstance(files, list):  # a list of junk: every sample file is "not listed"
        assert "[BREACH] site.file.prices.json: not listed in the manifest" in out
    else:
        assert "[BREACH] site.files: manifest `files` is not a list" in out


def test_manifest_without_files_key_is_a_breach(site):
    m = manifest(); del m["files"]
    site.routes[cl.MANIFEST_PATH] = (200, json.dumps(m).encode())
    assert run(site.url)["site.files"][0] == cl.BREACH


def test_truncated_body_is_a_breach_not_a_traceback(site, capsys, monkeypatch):
    full = json.dumps(manifest()).encode()
    site.routes[cl.MANIFEST_PATH] = (200, full[:40], {"X-Truncate": "1"})
    rc = _main_default_site(monkeypatch, site)
    out = capsys.readouterr().out
    assert rc == 1 and "Traceback" not in out and "RESULT: BREACH" in out
    assert "[BREACH] site.manifest:" in out and "truncated" in out


def test_truncated_sample_file_is_a_breach(site):
    site.routes["/public-data/v1/prices.json"] = (200, b'{"p"', {"X-Truncate": "1"})
    res = run(site.url)
    assert res["site.file.prices.json"][0] == cl.BREACH and "truncated" in res["site.file.prices.json"][1]


def test_truncated_body_is_retried(site):
    site.routes[cl.MANIFEST_PATH] = (200, b"{", {"X-Truncate": "1"})
    run(site.url, retries=2)
    assert site.hits[cl.MANIFEST_PATH] == 3


@pytest.mark.parametrize("body", [b"[" * 200000, b"\xff\xfe not utf-8", b'{"generated_at_sast": {"a": 1}}',
                                  b'{"generated_at_sast": 12345, "files": []}', b"null"])
def test_other_unparseable_manifests_are_breaches(site, capsys, monkeypatch, body):
    site.routes[cl.MANIFEST_PATH] = (200, body)
    rc = _main_default_site(monkeypatch, site)
    out = capsys.readouterr().out
    assert rc == 1 and "Traceback" not in out and "[BREACH]" in out and "RESULT: BREACH" in out


def test_an_unexpected_error_inside_a_check_becomes_a_breach_line(site, monkeypatch):
    def boom(*a, **k):
        raise TypeError("unexpected")
    monkeypatch.setattr(cl, "_age_checks", boom)
    res = run(site.url)
    assert res["site.age"] == (cl.BREACH, "check could not be evaluated (TypeError)")


def test_main_reports_a_breach_if_run_checks_itself_fails(site, capsys, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(cl, "run_checks", boom)
    rc = cl.main(["--site", site.url])
    out = capsys.readouterr().out
    assert rc == 1 and "[BREACH] check_live: the check itself failed (RuntimeError)" in out and "RESULT: BREACH (1)" in out


# ---- URL and flag validation ----

@pytest.mark.parametrize("url", ["file:///etc/passwd", "file://localhost/etc/passwd", "ftp://example.org/x", "gopher://example.org", "javascript:alert(1)",
                                 "example.org", "http://", "//example.org", ""])
@pytest.mark.parametrize("flag", ["--site", "--raw-url"])
def test_only_http_and_https_urls_are_accepted(capsys, flag, url):
    with pytest.raises(SystemExit) as e:
        cl.main([flag, url])
    assert e.value.code == 2 and "Traceback" not in capsys.readouterr().err


def test_run_checks_and_fetch_refuse_other_schemes_too(site):
    with pytest.raises(ValueError):
        cl.run_checks("file:///etc", now_fn=lambda: NOW)
    with pytest.raises(ValueError):
        cl.run_checks(site.url, raw_url="ftp://example.org/m.json", now_fn=lambda: NOW)
    assert cl.fetch("file:///etc/passwd")[0] is None and "http" in cl.fetch("file:///etc/passwd")[2]


def test_redirect_to_a_file_url_is_refused_and_http_redirects_are_followed(site):
    site.routes["/apps/public-dashboard/"] = (302, b"", {"Location": "file:///etc/passwd"})
    res = run(site.url)
    assert res["site.app"][0] == cl.BREACH
    site.routes["/"] = (302, b"", {"Location": "/real-home"})
    site.routes["/real-home"] = (200, b"home")
    assert run(site.url)["site.home"][0] == cl.OK  # documented: redirects are followed


def test_redirect_to_ftp_is_refused_before_any_connection_is_made(site):
    # Python's own redirect handler refuses file:// but follows ftp://. The guard must refuse it before connecting:
    # a listener stands in for an FTP server and must never see a connection (fails with the guard removed or with
    # urllib's default opener, which would connect to it).
    with socket.socket() as lst:
        lst.bind(("127.0.0.1", 0)); lst.listen(5); lst.setblocking(False)
        site.routes["/apps/public-dashboard/"] = (302, b"", {"Location": f"ftp://127.0.0.1:{lst.getsockname()[1]}/x"})
        res = run(site.url)
        assert res["site.app"] == (cl.BREACH, f"{cl.APP_PATH} -> HTTP 302")
        with pytest.raises(BlockingIOError):  # nobody connected
            lst.accept()


@pytest.mark.parametrize("args", [["--wait", "-1"], ["--wait", "3601"], ["--wait", "nan"], ["--wait", "inf"], ["--wait", "x"],
                                  ["--poll", "0"], ["--poll", "0.5"], ["--poll", "-5"], ["--poll", "601"], ["--poll", "nan"],
                                  ["--max-age-hours", "0"], ["--max-age-hours", "-1"], ["--warn-age-hours", "0"],
                                  ["--warn-age-hours", "-3"], ["--max-age-hours", "inf"],
                                  ["--warn-age-hours", "48"], ["--warn-age-hours", "50"],
                                  ["--max-age-hours", "20"],  # below the default warn of 30
                                  ["--retries", "-1"], ["--retries", "11"], ["--retries", "1.5"],
                                  ["--retry-delay", "-1"], ["--retry-delay", "61"]])
def test_nonsense_flag_values_are_rejected_before_anything_is_fetched(site, capsys, args):
    with pytest.raises(SystemExit) as e:
        cl.main(["--site", site.url, *args])
    assert e.value.code == 2 and not site.hits
    assert "Traceback" not in capsys.readouterr().err


def test_sensible_flag_values_are_accepted(site, capsys, monkeypatch):
    rc = _main_default_site(monkeypatch, site, ["--wait", "0", "--poll", "1", "--max-age-hours", "100", "--warn-age-hours", "99"])
    assert rc == 0


@pytest.mark.parametrize("flag,url", [("--site", "http://u:pw@h:PORTSECRET/"), ("--site", "http://h:PORTSECRET/"),
                                      ("--raw-url", "http://h:PORTSECRET/m.json"), ("--site", "http://h:99999999/"),
                                      ("--site", "http://[::1/")])
def test_a_bad_port_or_unparseable_url_gets_a_fixed_message_without_any_part_of_the_url(capsys, flag, url):
    with pytest.raises(SystemExit) as e:
        cl.main([flag, url])
    cap = capsys.readouterr()
    assert e.value.code == 2 and "could not be parsed" in cap.err
    for part in ("PORTSECRET", "u:pw", "99999999", "[::1"):
        assert part not in cap.out + cap.err


def test_validate_url_and_fetch_never_repeat_python_s_parser_message():
    with pytest.raises(ValueError) as e:
        cl.validate_url("http://h:PORTSECRET/")
    assert "PORTSECRET" not in str(e.value) and str(e.value) == "not a valid URL (it could not be parsed)"
    status, _, err = cl.fetch("http://u:pw@h:PORTSECRET/")
    assert status is None and "PORTSECRET" not in err and "pw" not in err


@pytest.mark.parametrize("value", ["", " ", ",", " , ,"])
def test_empty_sample_files_is_rejected_with_exit_2_and_nothing_is_fetched(site, capsys, value):
    with pytest.raises(SystemExit) as e:
        cl.main(["--site", site.url, "--sample-files", value])
    assert e.value.code == 2 and not site.hits and "at least one name" in capsys.readouterr().err


def test_run_checks_also_refuses_an_empty_sample_file_list(site):
    with pytest.raises(ValueError):
        cl.run_checks(site.url, sample_files=" , ", now_fn=lambda: NOW)
    assert not site.hits


def test_a_single_sample_file_still_works(site):
    res = run(site.url, sample_files="prices.json")
    assert [n for n in res if n.startswith("site.file.")] == ["site.file.prices.json"]


# ---- CLI defaults (a fixed clock, the local site standing in for production) ----

@pytest.mark.parametrize("age,verdict,code", [(29, "OK", 0), (31, "WARN (1)", 0), (49, "BREACH (1)", 1)])
def test_main_with_no_flags_uses_the_slo_defaults(site, capsys, monkeypatch, age, verdict, code):
    site.set_manifest(age_hours=age)
    monkeypatch.setattr(cl, "DEFAULT_SITE", site.url)
    monkeypatch.setattr(cl, "run_checks", functools.partial(cl.run_checks, now_fn=lambda: NOW, retries=0, retry_delay=0))
    assert cl.main([]) == code
    assert f"RESULT: {verdict} (checked " in capsys.readouterr().out


def test_main_boundaries_are_strict_30h_is_ok_and_48h_is_warn_not_breach(site, capsys, monkeypatch):
    monkeypatch.setattr(cl, "DEFAULT_SITE", site.url)
    monkeypatch.setattr(cl, "run_checks", functools.partial(cl.run_checks, now_fn=lambda: NOW, retries=0, retry_delay=0))
    site.set_manifest(age_hours=30)
    assert cl.main([]) == 0 and "RESULT: OK (" in capsys.readouterr().out
    site.set_manifest(age_hours=30.01)
    assert cl.main([]) == 0 and "RESULT: WARN (1) (" in capsys.readouterr().out
    site.set_manifest(age_hours=48)
    assert cl.main([]) == 0 and "RESULT: WARN (1) (" in capsys.readouterr().out
    site.set_manifest(age_hours=48.01)
    assert cl.main([]) == 1 and "RESULT: BREACH (1) (" in capsys.readouterr().out


def test_times_are_shown_in_sast_with_the_exact_format(site):
    utc, west = timezone.utc, timezone(timedelta(hours=-5))
    for tz in (utc, west, None):  # the same instant written three ways: 04:00 SAST on 24 October
        site.set_manifest(age_hours=8, tz=tz)
        assert run(site.url)["site.age"] == (cl.OK, "data is 8.0 h old (generated 2026-10-24 04:00 SAST)")
    assert cl._sast(datetime(2026, 12, 31, 23, 30, tzinfo=utc)) == "2027-01-01 01:30 SAST"


# ---- printing never echoes userinfo or a query string ----

def test_safe_url_strips_userinfo_query_and_fragment():
    assert cl.safe_url("https://user:pw@example.org:8443/a/b?token=SECRET#frag") == "https://example.org:8443/a/b"
    assert cl.safe_url("http://[::1]:8080/x?y=1") == "http://[::1]:8080/x"
    assert cl.safe_url("http://host:notaport/") == "<unreadable URL>"


@pytest.mark.parametrize("args", [["--site", "http://user:SECRETPW@127.0.0.1:9"], ["--site", "http://127.0.0.1:9/?token=SECRETQ"],
                                  ["--site", "http://127.0.0.1:9/#SECRETF"], ["--raw-url", "http://u:SECRETPW@127.0.0.1:9/m.json"]])
def test_rejected_urls_are_not_echoed(capsys, args):
    with pytest.raises(SystemExit) as e:
        cl.main(args)
    cap = capsys.readouterr()
    assert e.value.code == 2 and "SECRET" not in cap.out + cap.err


def test_raw_url_query_string_is_never_printed(site, capsys, monkeypatch):
    raw = Site().healthy()
    try:
        raw.routes.pop(cl.MANIFEST_PATH)  # the raw check fails, so its details are printed
        for extra in ([], ["--json"]):
            rc = _main_default_site(monkeypatch, site, ["--raw-url", raw.url + cl.MANIFEST_PATH + "?token=SECRETQ", *extra])
            cap = capsys.readouterr()
            assert rc == 1 and "raw.manifest" in cap.out and "SECRET" not in cap.out + cap.err
    finally:
        raw.srv.shutdown(); raw.srv.server_close()


def test_unreachable_site_line_shows_host_but_no_secrets(capsys):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    rc = cl.main(["--site", f"http://127.0.0.1:{port}", "--retries", "0"])
    out = capsys.readouterr().out
    assert rc == 1 and f"http://127.0.0.1:{port}/ -> unreachable" in out


def test_script_is_stdlib_only_and_sends_no_credentials():
    src = (Path(cl.__file__)).read_text()
    for banned in ("import httpx", "import requests", "Authorization", "Cookie", "environ", "getenv"):
        assert banned not in src
