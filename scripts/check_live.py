#!/usr/bin/env python3
"""Live site and data-age check (CHG-2026-032, CSI-036, SLO-PD-1, RB-12).

Read-only: fetches public URLs (home page, the data manifest, three sample data files) and reports OK / WARN /
BREACH per check. Standard library only. Writes nothing, sends no cookies or credentials.

    python3 scripts/check_live.py                                  # production site, SLO-PD-1 age check
    python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --wait 600 --raw-url <manifest URL>

Exit code: 0 = OK or WARN only, 1 = at least one BREACH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
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


def fetch(url: str, timeout: float = 20.0, retries: int = 2, delay: float = 5.0) -> tuple[int | None, bytes, str]:
    """GET url. Returns (status, body, error). Retries network errors and 5xx; a 4xx is final. status None = unreachable."""
    status, body, err = None, b"", ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(delay)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), ""
        except urllib.error.HTTPError as e:
            status, body, err = e.code, b"", f"HTTP {e.code}"
            if e.code < 500:
                return status, body, err
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            status, body, err = None, b"", f"unreachable ({type(e).__name__})"
    return status, body, err


def parse_manifest(body: bytes) -> tuple[dict | None, str]:
    try:
        m = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "not valid JSON"
    if not isinstance(m, dict):
        return None, "manifest is not a JSON object"
    return m, ""


def manifest_age(m: dict, now: datetime) -> tuple[timedelta | None, str]:
    raw = m.get("generated_at_sast")
    try:
        ts = datetime.fromisoformat(str(raw))
    except ValueError:
        return None, f"generated_at_sast missing or unreadable ({raw!r})"
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
    stamp = _sast(datetime.fromisoformat(m["generated_at_sast"]))
    if age > timedelta(hours=max_h):
        return [(f"{label}.age", BREACH, f"data is {_hours(age)} old (generated {stamp}); SLO-PD-1 is {max_h:g} h")]
    if age > timedelta(hours=warn_h):
        return [(f"{label}.age", WARN, f"data is {_hours(age)} old (generated {stamp}); over the {warn_h:g} h early warning")]
    return [(f"{label}.age", OK, f"data is {_hours(max(age, timedelta(0)))} old (generated {stamp})")]


def _build_id(m: dict) -> str | None:
    b = m.get("build")
    return b.get("id") if isinstance(b, dict) else None


def run_checks(site: str, *, raw_url: str | None = None, expect_local: str | None = None, max_age_hours: float = 48.0,
               warn_age_hours: float = 30.0, sample_files: str = SAMPLE_FILES, wait: float = 0.0, poll: float = 30.0,
               retries: int = 2, retry_delay: float = 5.0, timeout: float = 20.0, now_fn=None) -> list[tuple[str, str, str]]:
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    site = site.rstrip("/")
    results: list[tuple[str, str, str]] = []
    get = lambda url: fetch(url, timeout=timeout, retries=retries, delay=retry_delay)  # noqa: E731

    st, _, err = get(site + "/")
    results.append(("site.home", OK if st == 200 else BREACH, f"{site}/ -> HTTP 200" if st == 200 else f"{site}/ -> {err or st}"))

    st, body, err = get(site + APP_PATH)
    if st == 200 and b"PublicFunds" in body:
        results.append(("site.app", OK, f"{APP_PATH} -> HTTP 200"))
    else:
        results.append(("site.app", BREACH, f"{APP_PATH} -> " + (err or ("HTTP 200 but the page does not look like the dashboard" if st == 200 else str(st)))))

    manifest = None
    st, body, err = get(site + MANIFEST_PATH)
    if st != 200:
        results.append(("site.manifest", BREACH, f"{MANIFEST_PATH} -> {err or st}"))
    else:
        manifest, why = parse_manifest(body)
        if manifest is None:
            results.append(("site.manifest", BREACH, f"{MANIFEST_PATH} {why}"))
        else:
            results.append(("site.manifest", OK, f"{MANIFEST_PATH} -> HTTP 200, build {_build_id(manifest) or 'unknown'}"))
            results += _age_checks("site", manifest, now_fn(), max_age_hours, warn_age_hours)

    if manifest is not None:
        listed = {f.get("name"): f for f in manifest.get("files", []) if isinstance(f, dict)}
        for name in [n.strip() for n in sample_files.split(",") if n.strip()]:
            entry = listed.get(name)
            if entry is None:
                results.append((f"site.file.{name}", BREACH, "not listed in the manifest"))
                continue
            st, fbody, err = get(f"{site}/public-data/v1/{name}")
            if st != 200:
                results.append((f"site.file.{name}", BREACH, f"-> {err or st}"))
            elif len(fbody) != entry.get("bytes") or hashlib.sha256(fbody).hexdigest() != entry.get("sha256"):
                results.append((f"site.file.{name}", BREACH, "served bytes or sha256 differ from the manifest"))
            else:
                results.append((f"site.file.{name}", OK, f"{len(fbody)} bytes, sha256 matches the manifest"))

    if raw_url:
        st, body, err = get(raw_url)
        rm, why = (None, err or str(st)) if st != 200 else parse_manifest(body)
        if rm is None:
            results.append(("raw.manifest", BREACH, f"git host manifest: {why}"))
        else:
            results += _age_checks("raw", rm, now_fn(), max_age_hours, warn_age_hours)
            if manifest is not None and _build_id(rm) != _build_id(manifest):
                results.append(("raw.manifest", WARN, f"git host has build {_build_id(rm)}, site serves {_build_id(manifest)} (Pages lagging or its build failed)"))
            elif manifest is not None:
                results.append(("raw.manifest", OK, f"same build as the site ({_build_id(rm)})"))

    if expect_local:
        try:
            with open(expect_local, encoding="utf-8") as fh:
                want = _build_id(json.load(fh))
        except (OSError, ValueError):
            want = None
        if not want:
            results.append(("local.build", BREACH, f"cannot read a build id from {expect_local}"))
        else:
            deadline = time.monotonic() + wait
            seen = _build_id(manifest) if manifest else None
            while seen != want and time.monotonic() < deadline:
                time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
                st, body, _ = get(site + MANIFEST_PATH)
                m2, _ = parse_manifest(body) if st == 200 else (None, "")
                seen = _build_id(m2) if m2 else seen
            if seen == want:
                results.append(("local.build", OK, f"site serves the build just published ({want})"))
            else:
                results.append(("local.build", BREACH, f"site serves build {seen or 'unknown'}, expected {want} (waited {wait:g} s)"))
    return results


def summarise(results) -> tuple[str, int]:
    b = sum(1 for _, s, _ in results if s == BREACH)
    w = sum(1 for _, s, _ in results if s == WARN)
    if b:
        return f"BREACH ({b})", 1
    if w:
        return f"WARN ({w})", 0
    return "OK", 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only live site and data-age check (SLO-PD-1).")
    ap.add_argument("--site", default=DEFAULT_SITE, help="site base URL (default: production)")
    ap.add_argument("--raw-url", help="manifest URL on the git host; compared with the site (the SLO's measuring point)")
    ap.add_argument("--expect-local", metavar="MANIFEST", help="local manifest.json whose build id the site must serve")
    ap.add_argument("--wait", type=float, default=0.0, help="seconds to wait for --expect-local (Pages deploy), default 0")
    ap.add_argument("--poll", type=float, default=30.0, help="seconds between polls while waiting, default 30")
    ap.add_argument("--max-age-hours", type=float, default=48.0, help="SLO-PD-1 breach threshold, default 48")
    ap.add_argument("--warn-age-hours", type=float, default=30.0, help="early-warning threshold, default 30")
    ap.add_argument("--sample-files", default=SAMPLE_FILES, help="comma-separated data files to checksum")
    ap.add_argument("--retries", type=int, default=2, help="extra attempts per request, default 2")
    ap.add_argument("--retry-delay", type=float, default=5.0, help="seconds between attempts, default 5")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)
    results = run_checks(a.site, raw_url=a.raw_url, expect_local=a.expect_local, max_age_hours=a.max_age_hours,
                         warn_age_hours=a.warn_age_hours, sample_files=a.sample_files, wait=a.wait, poll=a.poll,
                         retries=a.retries, retry_delay=a.retry_delay)
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
