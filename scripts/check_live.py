#!/usr/bin/env python3
"""Live site and data-age check (CHG-2026-032, CSI-036, SLO-PD-1, RB-12).

Read-only: fetches public URLs (home page, the data manifest, three sample data files) and reports OK / WARN /
BREACH per check. Standard library only. Writes nothing, sends no cookies or credentials.

    python3 scripts/check_live.py                                  # production site, SLO-PD-1 age check
    python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --wait 600 --raw-url <manifest URL>

Exit code: 0 = OK or WARN only, 1 = at least one BREACH, 2 = bad command line (nothing was checked).
Only http and https URLs are accepted (also for redirects). Redirects are followed (urllib's limit of 10). The timeout
(20 s) is per socket read, not a total deadline for a request; a request is tried up to 3 times.
URLs are printed without userinfo or query string. A default run measures the site, not raw.githubusercontent.com (the SLO's measuring point): add --raw-url for that.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_SITE = "https://publicfunds.grokforum.site"
MANIFEST_PATH = "/public-data/v1/manifest.json"
APP_PATH = "/apps/public-dashboard/"
SAMPLE_FILES = "municipalities.json,departments.json,prices.json"
USER_AGENT = "publicfunds-check/1"
SAST = timezone(timedelta(hours=2), "SAST")
FUTURE_SLACK = timedelta(minutes=5)
OK, WARN, BREACH = "OK", "WARN", "BREACH"
MIN_POLL = 0.05  # seconds; run_checks never polls faster than this, whatever it is given
MAX_WAIT = 3600.0
MAX_POLL = 600.0


def safe_url(url: str) -> str:
    """The URL as it may be printed: no userinfo, no query string, no fragment."""
    try:
        p = urllib.parse.urlsplit(url)
        host = p.hostname or ""
        port = f":{p.port}" if p.port else ""
    except ValueError:
        return "<unreadable URL>"
    host = f"[{host}]" if ":" in host else host
    return urllib.parse.urlunsplit((p.scheme, host + port, p.path, "", ""))


def validate_url(url: str, *, base: bool = False) -> str:
    """Accept only plain http(s) URLs with a host and no embedded credentials; raise ValueError otherwise.
    base=True (the --site value) also refuses a query string or fragment. Messages never repeat the URL."""
    try:
        p = urllib.parse.urlsplit(url)
        host = p.hostname
        _ = p.port  # raises ValueError for a bad port
    except ValueError:  # Python's message can repeat part of the URL (a bad port, for example): never pass it on
        raise ValueError("not a valid URL (it could not be parsed)") from None
    if p.scheme not in ("http", "https"):
        raise ValueError(f"only http and https URLs are allowed (got scheme {p.scheme or 'none'!r})")
    if not host:
        raise ValueError("URL has no host")
    if p.username is not None or p.password is not None:
        raise ValueError("URLs with embedded credentials are not allowed")
    if base and (p.query or p.fragment):
        raise ValueError("the site URL must not have a query string or fragment")
    return url


class _HttpOnlyRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but only to http(s) URLs (urllib itself would also follow ftp)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme not in ("http", "https"):
            raise urllib.error.HTTPError(req.full_url, code, "redirect to a non-http(s) URL refused", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_HttpOnlyRedirects)


def fetch(url: str, timeout: float = 20.0, retries: int = 2, delay: float = 5.0) -> tuple[int | None, bytes, str]:
    """GET url. Returns (status, body, error). Retries network errors, truncated bodies and 5xx; a 4xx is final.
    status None = unreachable or unreadable. The timeout applies to each socket read."""
    try:
        validate_url(url)
    except ValueError as e:
        return None, b"", str(e)
    status, body, err = None, b"", ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(delay)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                return r.status, r.read(), ""
        except urllib.error.HTTPError as e:
            status, body, err = e.code, b"", f"HTTP {e.code}"
            if e.code < 500:
                return status, body, err
        except http.client.HTTPException as e:  # IncompleteRead (truncated body), BadStatusLine, ...
            status, body, err = None, b"", f"truncated or malformed response ({type(e).__name__})"
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            status, body, err = None, b"", f"unreachable ({type(e).__name__})"
    return status, body, err


def parse_manifest(body: bytes) -> tuple[dict | None, str]:
    try:
        m = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None, "not valid JSON"
    if not isinstance(m, dict):
        return None, "manifest is not a JSON object"
    return m, ""


def manifest_age(m: dict, now: datetime) -> tuple[timedelta | None, str]:
    raw = m.get("generated_at_sast")
    try:
        ts = datetime.fromisoformat(str(raw))
    except ValueError:
        return None, f"generated_at_sast missing or unreadable ({str(raw)[:40]!r})"
    if ts.tzinfo is None:
        return None, "generated_at_sast has no UTC offset"
    return now - ts, ""


def _hours(td: timedelta) -> str:
    return f"{td.total_seconds() / 3600:.1f} h"


def _sast(ts: datetime) -> str:
    return ts.astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")


def _age_checks(label: str, m: dict, now: datetime, max_h: float, warn_h: float) -> list[tuple[str, str, str]]:
    age, why = manifest_age(m, now)
    if age is None:
        return [(f"{label}.age", BREACH, why)]
    if age < -FUTURE_SLACK:
        return [(f"{label}.age", BREACH, f"generated_at_sast is {_hours(-age)} in the future")]
    stamp = _sast(datetime.fromisoformat(str(m["generated_at_sast"])))
    if age > timedelta(hours=max_h):
        return [(f"{label}.age", BREACH, f"data is {_hours(age)} old (generated {stamp}); SLO-PD-1 is {max_h:g} h")]
    if age > timedelta(hours=warn_h):
        return [(f"{label}.age", WARN, f"data is {_hours(age)} old (generated {stamp}); over the {warn_h:g} h early warning")]
    return [(f"{label}.age", OK, f"data is {_hours(max(age, timedelta(0)))} old (generated {stamp})")]


def _build_id(m: dict | None) -> str | None:
    b = m.get("build") if isinstance(m, dict) else None
    bid = b.get("id") if isinstance(b, dict) else None
    return bid if isinstance(bid, str) and bid else None


def sample_names(sample_files: str) -> list[str]:
    """The sample file names; raises ValueError if there are none (an empty list would be a silent, empty OK)."""
    names = [n.strip() for n in sample_files.split(",") if n.strip()]
    if not names:
        raise ValueError("no sample file names given")
    return names


def _file_checks(site: str, manifest: dict, sample_files: str, get) -> list[tuple[str, str, str]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        return [("site.files", BREACH, f"manifest `files` is not a list (found {type(files).__name__})")]
    listed = {f.get("name"): f for f in files if isinstance(f, dict)}
    results = []
    for name in sample_names(sample_files):
        entry = listed.get(name)
        if entry is None:
            results.append((f"site.file.{name}", BREACH, "not listed in the manifest"))
            continue
        st, fbody, err = get(f"{site}/public-data/v1/{name}")
        if st != 200:
            results.append((f"site.file.{name}", BREACH, f"-> {err or st}"))
        elif len(fbody) != entry.get("bytes"):
            results.append((f"site.file.{name}", BREACH, f"served {len(fbody)} bytes, the manifest says {entry.get('bytes')!r}"))
        elif hashlib.sha256(fbody).hexdigest() != entry.get("sha256"):
            results.append((f"site.file.{name}", BREACH, "served sha256 differs from the manifest (a mismatch right after a publish can be Pages still deploying)"))
        else:
            results.append((f"site.file.{name}", OK, f"{len(fbody)} bytes, sha256 matches the manifest"))
    return results


def _guard(name: str, fn) -> list[tuple[str, str, str]]:
    """Run one group of checks; any unexpected error becomes a BREACH line for that group, never a traceback."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - deliberate: the check could not be evaluated
        return [(name, BREACH, f"check could not be evaluated ({type(e).__name__})")]


def run_checks(site: str, *, raw_url: str | None = None, expect_local: str | None = None, max_age_hours: float = 48.0,
               warn_age_hours: float = 30.0, sample_files: str = SAMPLE_FILES, wait: float = 0.0, poll: float = 30.0,
               retries: int = 2, retry_delay: float = 5.0, timeout: float = 20.0, now_fn=None) -> list[tuple[str, str, str]]:
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    validate_url(site, base=True)
    sample_names(sample_files)
    if raw_url:
        validate_url(raw_url)
    site = site.rstrip("/")
    shown = safe_url(site)  # only this form is ever printed
    poll = max(poll, MIN_POLL)
    results: list[tuple[str, str, str]] = []
    get = lambda url: fetch(url, timeout=timeout, retries=retries, delay=retry_delay)  # noqa: E731

    st, _, err = get(site + "/")
    results.append(("site.home", OK if st == 200 else BREACH, f"{shown}/ -> HTTP 200" if st == 200 else f"{shown}/ -> {err or st}"))

    st, body, err = get(site + APP_PATH)
    if st == 200 and b"PublicFunds" in body:
        results.append(("site.app", OK, f"{APP_PATH} -> HTTP 200"))
    else:
        results.append(("site.app", BREACH, f"{APP_PATH} -> " + (err or ("HTTP 200 but the page does not look like the dashboard" if st == 200 else str(st)))))

    def load_manifest() -> tuple[dict | None, str]:
        st, body, err = get(site + MANIFEST_PATH)
        if st != 200:
            return None, f"{MANIFEST_PATH} -> {err or st}"
        m, why = parse_manifest(body)
        return (m, "") if m is not None else (None, f"{MANIFEST_PATH} {why}")

    want = None
    if expect_local:
        try:
            with open(expect_local, encoding="utf-8") as fh:
                want = _build_id(json.load(fh))
        except (OSError, ValueError, RecursionError):
            want = None

    manifest, problem = load_manifest()
    waited = False
    if want:  # give Pages time to deploy the build that was just published; everything below uses the final manifest
        deadline = time.monotonic() + wait
        while _build_id(manifest) != want and time.monotonic() < deadline:
            waited = True
            time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
            manifest, problem = load_manifest()

    if manifest is None:
        results.append(("site.manifest", BREACH, problem))
    else:
        results.append(("site.manifest", OK, f"{MANIFEST_PATH} -> HTTP 200, build {_build_id(manifest) or 'unknown'}"))
        results += _guard("site.age", lambda: _age_checks("site", manifest, now_fn(), max_age_hours, warn_age_hours))
        results += _guard("site.files", lambda: _file_checks(site, manifest, sample_files, get))

    if raw_url:
        def raw():
            out = []
            st, body, err = get(raw_url)
            rm, why = (None, err or str(st)) if st != 200 else parse_manifest(body)
            if rm is None:
                return [("raw.manifest", BREACH, f"git host manifest: {why}")]
            out += _age_checks("raw", rm, now_fn(), max_age_hours, warn_age_hours)
            if manifest is None:
                return out
            site_id, raw_id = _build_id(manifest), _build_id(rm)
            if site_id is None or raw_id is None:
                out.append(("raw.manifest", WARN, f"cannot confirm the same build: build id missing (site {site_id}, git host {raw_id})"))
            elif raw_id != site_id:
                out.append(("raw.manifest", WARN, f"git host has build {raw_id}, site serves {site_id} (Pages lagging or its build failed)"))
            else:
                out.append(("raw.manifest", OK, f"same build as the site ({raw_id})"))
            return out
        results += _guard("raw.manifest", raw)

    if expect_local:
        if not want:
            results.append(("local.build", BREACH, f"cannot read a build id from {expect_local}"))
        elif _build_id(manifest) == want:
            results.append(("local.build", OK, f"site serves the build just published ({want})"))
        else:
            results.append(("local.build", BREACH, f"site serves build {_build_id(manifest) or 'unknown'}, expected {want} (waited {wait:g} s)"))
    return results


def summarise(results) -> tuple[str, int]:
    b = sum(1 for _, s, _ in results if s == BREACH)
    w = sum(1 for _, s, _ in results if s == WARN)
    if b:
        return f"BREACH ({b})", 1
    if w:
        return f"WARN ({w})", 0
    return "OK", 0


def _site_arg(value: str) -> str:
    try:
        return validate_url(value, base=True)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _names_arg(value: str) -> str:
    try:
        sample_names(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"{e}: give at least one name, or leave the default") from None
    return value


def _url_arg(value: str) -> str:
    try:
        return validate_url(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _num(lo: float, hi: float, *, lo_open: bool = False, integer: bool = False):
    def conv(value: str):
        try:
            x = int(value) if integer else float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
        if not math.isfinite(x) or x < lo or x > hi or (lo_open and x == lo):
            raise argparse.ArgumentTypeError(f"must be {'greater than' if lo_open else 'at least'} {lo:g} and at most {hi:g}")
        return x
    return conv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only live site and data-age check (SLO-PD-1).")
    ap.add_argument("--site", type=_site_arg, default=DEFAULT_SITE, help="site base URL, http or https (default: production)")
    ap.add_argument("--raw-url", type=_url_arg, help="manifest URL on the git host; compared with the site (the SLO's measuring point)")
    ap.add_argument("--expect-local", metavar="MANIFEST", help="local manifest.json whose build id the site must serve")
    ap.add_argument("--wait", type=_num(0, MAX_WAIT), default=0.0, help=f"seconds to wait for --expect-local (Pages deploy), 0 to {MAX_WAIT:g}, default 0")
    ap.add_argument("--poll", type=_num(1, MAX_POLL), default=30.0, help=f"seconds between polls while waiting, 1 to {MAX_POLL:g}, default 30")
    ap.add_argument("--max-age-hours", type=_num(0, 24 * 365, lo_open=True), default=48.0, help="SLO-PD-1 breach threshold, default 48")
    ap.add_argument("--warn-age-hours", type=_num(0, 24 * 365, lo_open=True), default=30.0, help="early-warning threshold, must be below --max-age-hours, default 30")
    ap.add_argument("--sample-files", type=_names_arg, default=SAMPLE_FILES, help="comma-separated data files to checksum; at least one (an empty list is refused)")
    ap.add_argument("--retries", type=_num(0, 10, integer=True), default=2, help="extra attempts per request, 0 to 10, default 2")
    ap.add_argument("--retry-delay", type=_num(0, 60), default=5.0, help="seconds between attempts, 0 to 60, default 5")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)
    if a.warn_age_hours >= a.max_age_hours:
        ap.error("--warn-age-hours must be below --max-age-hours")
    try:
        results = run_checks(a.site, raw_url=a.raw_url, expect_local=a.expect_local, max_age_hours=a.max_age_hours,
                             warn_age_hours=a.warn_age_hours, sample_files=a.sample_files, wait=a.wait, poll=a.poll,
                             retries=a.retries, retry_delay=a.retry_delay)
    except Exception as e:  # noqa: BLE001 - never a traceback: report a breach and exit 1
        results = [("check_live", BREACH, f"the check itself failed ({type(e).__name__})")]
    verdict, code = summarise(results)
    checked = _sast(datetime.now(timezone.utc))
    if a.json:
        print(json.dumps({"checked_at": checked, "result": verdict,
                          "checks": [{"check": n, "status": s, "detail": d} for n, s, d in results]}, indent=2))
    else:
        for n, s, d in results:
            print(f"[{s}] {n}: {d}")
        print(f"RESULT: {verdict} (checked {checked})")
    return code


if __name__ == "__main__":
    sys.exit(main())
