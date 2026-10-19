"""Headless check of apps/public-dashboard against local public-data (CHG-2026-006).

Serves the repo root on 127.0.0.1:PORT, opens every page on desktop and mobile viewports in Chromium, fails on
console errors, failed requests or the error view, exercises the tools and CSV download, and writes screenshots to
dist/public-dashboard/. Run: uv run --group screenshots python scripts/dashboard_check.py [--port 8791]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import shutil
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = [("home", "#/"), ("coverage", "#/coverage"), ("municipalities", "#/municipalities"),
         ("municipality", "#/m/MUN:BUF"), ("departments", "#/departments"), ("department", None),
         ("tenders", "#/tenders"), ("flags", "#/flags"), ("tools", "#/tools"), ("compare", "#/tools/compare?a=MUN:BUF&b=MUN:NMA&y=2024"),
         ("sources", "#/sources"), ("unknowns", "#/unknowns"), ("changes", "#/changes")]
# Optional accessibility scan with axe-core (npm i axe-core); serious/critical WCAG 2.x A/AA violations fail the check.
AXE_JS = next((Path(x) for x in (os.environ.get("AXE_JS", ""), "/workspace/tools/web/node_modules/axe-core/axe.min.js",
                                 str(ROOT / "node_modules/axe-core/axe.min.js")) if x and Path(x).is_file()), None)
VIEWPORTS = {"desktop": {"width": 1366, "height": 900}, "mobile": {"width": 390, "height": 844}}


class Quiet(http.server.SimpleHTTPRequestHandler):
    """Serves only the app and the public data (never data/, the review DB or anything else in the repo)."""

    def do_GET(self):
        if not self.path.split("?")[0].startswith(("/apps/public-dashboard/", "/public-data/")):
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0, help="0 = any free port")
    ap.add_argument("--out", default=str(ROOT / "dist" / "public-dashboard"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    app = f"{base}/apps/public-dashboard/index.html?data={base}/public-data/v1/"
    dep = json.loads((ROOT / "public-data" / "v1" / "departments.json").read_text())["departments"][0]["id"]
    problems, shots, checks = [], [], {}
    with sync_playwright() as p:
        chrome = shutil.which("google-chrome") or shutil.which("chromium")   # box Chrome; else Playwright's own
        browser = p.chromium.launch(executable_path=chrome, headless=True) if chrome else p.chromium.launch()
        for vname, vp in VIEWPORTS.items():
            ctx = browser.new_context(viewport=vp, accept_downloads=True, device_scale_factor=1,
                                      is_mobile=vname == "mobile", has_touch=vname == "mobile")
            page = ctx.new_page()
            page.on("console", lambda m: problems.append(f"{vname} console {m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: problems.append(f"{vname} pageerror: {e}"))
            page.on("requestfailed", lambda r: problems.append(f"{vname} requestfailed: {r.url}"))
            for name, hash_ in PAGES:
                hash_ = hash_ or f"#/d/{dep}"
                page.goto(app + hash_ if name == "home" else app.split("#")[0] + hash_)
                page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
                h1 = page.locator("#view h1").inner_text()
                if h1 in ("Something went wrong", "Page not found", "Municipality not found", "Department not found"):
                    problems.append(f"{vname} {name}: {h1}: {page.locator('#view').inner_text()[:300]}")
                if AXE_JS:
                    page.add_script_tag(content=AXE_JS.read_text())
                    res = page.evaluate("""() => axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}})
                        .then(r => r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length})))""")
                    checks.setdefault("axe", {})[f"{vname}:{name}"] = res
                    problems += [f"{vname} {name} axe {v['impact']}: {v['id']} ({v['n']} nodes)" for v in res
                                 if v["impact"] in ("serious", "critical")]
                f = out / f"{name}-{vname}.png"
                page.screenshot(path=str(f), full_page=vname == "desktop" and name in ("home", "flags", "tools", "unknowns", "changes"))
                shots.append(str(f))
            # tools: inflation + fuel checker produce results; CSV download works
            page.goto(app.split("#")[0] + "#/tools")
            page.wait_for_selector('#view[aria-busy="false"]')
            page.fill("#fuel-date", "2026-10-15")
            page.select_option("#fuel-grade", "petrol_95_inland")
            page.fill("#fuel-paid", "30.50")
            checks[f"{vname}_fuel"] = page.locator("#t-fuel").locator("xpath=..").locator(".result").inner_text()
            checks[f"{vname}_inflation"] = page.locator("#t-inf").locator("xpath=..").locator(".result").inner_text()
            page.click("details summary")
            with page.expect_download() as dl:
                page.locator("button.btn-csv:visible").first.click()
            checks[f"{vname}_csv"] = dl.value.suggested_filename
            if vname == "mobile":
                page.goto(app.split("#")[0] + "#/")
                page.wait_for_selector('#view[aria-busy="false"]')
                page.click("#navtoggle")
                page.screenshot(path=str(out / "menu-mobile.png"))
                shots.append(str(out / "menu-mobile.png"))
                page.click('nav a[href="#/coverage"]')
                page.wait_for_selector('#view[aria-busy="false"]')
                checks["mobile_nav_to_coverage"] = page.locator("#view h1").inner_text()
            ctx.close()
        browser.close()
    srv.shutdown()
    print(json.dumps({"screenshots": shots, "checks": checks, "problems": problems}, indent=1, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
