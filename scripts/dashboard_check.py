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
import re
import shutil
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))      # thusa.coverage_ceiling, wherever the script is started from
from thusa.coverage_ceiling import by_province, core_gap_lines, model, province_order  # noqa: E402
PAGES = [("home", "#/"), ("coverage", "#/coverage"), ("municipalities", "#/municipalities"),
         ("municipality", "#/m/MUN:BUF"), ("departments", "#/departments"), ("department", None),
         ("tenders", "#/tenders"), ("flags", "#/flags"), ("tools", "#/tools"), ("compare", "#/tools/compare?a=MUN:BUF&b=MUN:NMA&y=2024"),
         ("sources", "#/sources"), ("unknowns", "#/unknowns"), ("changes", "#/changes"), ("glossary", "#/glossary"), ("report-card", "#/m/MUN:BUF/card")]
# Optional accessibility scan with axe-core (npm i axe-core); serious/critical WCAG 2.x A/AA violations fail the check.
AXE_JS = next((Path(x) for x in (os.environ.get("AXE_JS", ""), "/workspace/tools/web/node_modules/axe-core/axe.min.js",
                                 str(ROOT / "node_modules/axe-core/axe.min.js")) if x and Path(x).is_file()), None)
VIEWPORTS = {"desktop": {"width": 1366, "height": 900}, "mobile": {"width": 390, "height": 844}}


OLD_HEADERS = ("Irregular & wasteful spending", "Budget", "Audited actuals", "Audit opinion", "Tender awards")
PROVINCES = {"EC": "Eastern Cape", "FS": "Free State", "GT": "Gauteng", "KZN": "KwaZulu-Natal", "LP": "Limpopo", "MP": "Mpumalanga",
             "NC": "Northern Cape", "NW": "North West", "WC": "Western Cape"}          # mirror of PROVINCES in index.html
ROUTES = [r"^#?/?$", r"^#/coverage$", r"^#/municipalities$", r"^#/m/.+$", r"^#/departments$", r"^#/d/.+$", r"^#/tenders$", r"^#/flags$",
          r"^#/tools(?:/\w+)?$", r"^#/sources$", r"^#/unknowns$", r"^#/changes$", r"^#/glossary$"]   # mirror of `routes` in index.html
# CHG-2026-034: state wording on the report card and the glossary says "not available", not "not published". "published" stays where it is
# about an official source or this site's own release (attribution, "Data published <date>", "confirmed, published flags").
BANNED_STATE_WORDING = ("not published", "has not published", "blank: not published", "data items published")
MIN_OPACITY = 0.9


def check_by_type(page, vname, app, problems, cov, mun):
    """CHG-2026-033: the 'By data type' table on #/unknowns against the reference model (thusa/coverage_ceiling.py)."""
    def say(msg):
        problems.append(f"{vname} unknowns/by-type: {msg}")

    def text(loc, what):
        """Normalised visible text of a locator that must exist exactly once and be visible; None (and a problem) otherwise."""
        try:
            if loc.count() != 1:
                say(f"{what}: expected 1 element, found {loc.count()}")
                return None
            if not loc.is_visible():
                say(f"{what}: present but not visible")
                return None
            return re.sub(r"\s+", " ", loc.inner_text(timeout=2000)).strip()
        except Exception as exc:                      # a broken page must be reported, never crash the whole check
            say(f"{what}: could not be read ({type(exc).__name__})")
            return None

    def top(loc):
        try:
            bb = loc.bounding_box(timeout=2000)
            return bb["y"] if bb else None
        except Exception:
            return None

    def opaque(loc, what):
        """Effective opacity (own x every ancestor) must be at least MIN_OPACITY: text kept 'visible' but faded out is not readable."""
        try:
            o = loc.evaluate("el => { let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; }",
                             timeout=2000)
            if o < MIN_OPACITY:
                say(f"{what}: effective opacity {o:.2f} is below {MIN_OPACITY}")
        except Exception as exc:
            say(f"{what}: opacity could not be read ({type(exc).__name__})")

    if app:                                           # app=None: the caller has already put the page under test in `page` (mock test)
        page.goto(app.split("#")[0] + "#/unknowns")
        page.wait_for_selector('#view[aria-busy="false"]')
    want, bp = model(cov, mun), by_province(cov, mun)
    tx = want["_text"]
    bt = page.locator("#by-type")
    table = bt.locator("table")
    if bt.count() != 1 or table.count() != 1:
        say("#by-type table not found")
        return

    # 1. headers: the exact new label in every column, never the old bare label; the empty-year marker inside that column's th;
    #    the column ORDER is the data_types order
    for dt, label in tx["headers"].items():
        th = text(bt.locator(f'thead th[data-dt="{dt}"]'), f"header {dt}")
        if th is None:
            continue
        marks = [f"{fy}: none complete" for fy in want[dt]["empty"]]
        own = th
        for m in marks:
            if m not in th:
                say(f"header {dt} lacks the marker {m!r}: {th!r}")
            own = own.replace(m, "")
        own = own.strip()
        if own != label:
            say(f"header {dt} reads {own!r}, expected {label!r}")
        if own in OLD_HEADERS:
            say(f"header {dt} still has the old bare label {own!r}")
        if not marks and "none complete" in th:
            say(f"header {dt} carries a marker but no year is empty for it")
    try:
        head_dts = bt.locator("thead th[data-dt]").evaluate_all("els => els.map(e => e.dataset.dt)")
        head_idx = bt.locator("thead th[data-dt]").evaluate_all("els => els.map(e => Array.from(e.parentElement.children).indexOf(e))")
        if head_dts != cov["data_types"]:
            say(f"column order is {head_dts}, expected {cov['data_types']}")
    except Exception as exc:
        say(f"header order could not be read ({type(exc).__name__})")
        head_dts, head_idx = [], []

    # 1b. rows: the data-prov of each row, its visible province name and its position (lowest overall share first, as the page sorts)
    try:
        rows = bt.locator("tbody tr[data-prov]").evaluate_all(
            "els => els.map(r => ({prov: r.dataset.prov, label: (r.children[0] || {}).innerText || '', "
            "dts: Array.from(r.querySelectorAll('td[data-dt]')).map(c => c.dataset.dt), "
            "idx: Array.from(r.querySelectorAll('td[data-dt]')).map(c => Array.from(r.children).indexOf(c))}))")
        order = [r["prov"] for r in rows]
        if order != province_order(cov, mun):
            say(f"row order is {order}, expected {province_order(cov, mun)} (lowest overall share first)")
        for r in rows:
            if re.sub(r"\s+", " ", r["label"]).strip() != PROVINCES.get(r["prov"]):
                say(f"row data-prov={r['prov']} shows the name {r['label']!r}, expected {PROVINCES.get(r['prov'])!r}")
            if r["dts"] != head_dts or r["idx"] != head_idx:
                say(f"row {r['prov']}: cells are in the order {r['dts']} at positions {r['idx']}, headers {head_dts} at {head_idx}")
    except Exception as exc:
        say(f"rows could not be read ({type(exc).__name__})")

    # 2. banner: visible, readable, exact text, above the table, one link that resolves to an existing view; absent when nothing is empty
    ban = page.locator("#by-type-banner")
    if want["_banner"]:
        b = text(ban, "banner")
        if b is not None:
            opaque(ban, "banner")
            for line in want["_banner"]:
                if line not in b:
                    say(f"banner lacks {line!r}: {b!r}")
            by, ty = top(ban), top(table)
            if by is None or ty is None:
                say("banner/table position could not be measured")
            elif by >= ty:
                say("banner is not above the table")
            link = ban.locator("a.to-trend")
            if link.count() != 1:
                say("banner has no (single) link to the trend table")
            else:
                try:
                    href = link.get_attribute("href", timeout=2000) or ""
                    if not any(re.match(rx, href) for rx in ROUTES):
                        say(f"trend link href {href!r} is not an existing route (the hash router would show 'Page not found')")
                    elif page.locator("#trend").count() != 1:
                        say("trend heading #trend not found (exactly one expected)")
                    else:
                        link.click(timeout=2000)
                        now = page.evaluate("location.hash")
                        if not any(re.match(rx, now) for rx in ROUTES) or now != "#/unknowns":
                            say(f"after the click on the trend link the address is {now!r}, expected the same view '#/unknowns'")
                        if page.locator("#by-type table").count() != 1:
                            say("after the click on the trend link the by-type table is gone (the view was replaced)")
                        ty2 = top(page.locator("#trend"))
                        vh = page.evaluate("window.innerHeight")
                        hb = page.evaluate("document.querySelector('header').getBoundingClientRect().bottom")   # the header is sticky
                        if ty2 is None or not (hb - 2 <= ty2 < vh):
                            say(f"after the click the trend heading is not in view below the sticky header "
                                f"(top={ty2}, header bottom={hb}, viewport height={vh})")
                except Exception as exc:
                    say(f"trend link could not be exercised ({type(exc).__name__})")
    elif ban.count() and ban.is_visible():
        say("unexpected banner: no type has an empty year")

    # 3. every province x data type cell shows exactly "<P> of <n>" as visible, readable text (no hover), the % matches,
    #    and "(highest possible x%)" is shown for exactly the types with an empty year
    seen = 0
    for p, d in bp.items():
        for dt, c in d.items():
            if not c["n"]:
                continue
            td = bt.locator(f'tbody tr[data-prov="{p}"] td[data-dt="{dt}"]')
            nn = td.locator(".nn")
            got = text(nn, f"cell {p}/{dt} n-of-N")
            seen += 1
            if got is None:
                continue
            opaque(nn, f"cell {p}/{dt} n-of-N")
            if got != f"{c['P']} of {c['n']}":
                say(f"cell {p}/{dt} shows {got!r}, data says '{c['P']} of {c['n']}'")
            h = None
            try:
                bb = nn.bounding_box(timeout=2000)
                h = bb["height"] if bb else None
            except Exception:
                pass
            if h is None or h < 8:
                say(f"cell {p}/{dt} n-of-N has no usable box (height {h})")
            pc = text(td.locator(".pct"), f"cell {p}/{dt} percentage")
            if pc is not None:
                try:
                    shown = float(re.sub(r"[^0-9.,]", "", pc).replace(",", "."))
                    if abs(shown - 100 * c["P"] / c["n"]) > 0.051:
                        say(f"cell {p}/{dt} percentage {pc!r} does not match {c['P']}/{c['n']}")
                except ValueError:
                    say(f"cell {p}/{dt} percentage {pc!r} is not a number")
            hp, wanted_hp = td.locator(".hp"), tx["in_cell"][p][dt]
            if wanted_hp:
                g = text(hp, f"cell {p}/{dt} highest-possible text")
                if g is not None and g != wanted_hp:
                    say(f"cell {p}/{dt} reads {g!r}, expected {wanted_hp!r}")
            elif hp.count():
                say(f"cell {p}/{dt} has a highest-possible text but no year is empty for {dt}")
    total = bt.locator("tbody td .nn").count()
    if total != seen:
        say(f"{total} n-of-N elements on the page, data has {seen}")

    # 4. notes: exact text per type, only for types with an empty year
    for dt in cov["data_types"]:
        li = page.locator(f'#by-type-notes li[data-dt="{dt}"]')
        if want[dt]["note"]:
            got = text(li, f"note {dt}")
            if got is not None and got != want[dt]["note"]:
                say(f"note {dt} reads {got!r}, expected {want[dt]['note']!r}")
        elif li.count():
            say(f"unexpected note for {dt}")

    # 5. static strings: caption, how-to-read card, tender caption exactly as the model (which is jargon-tested in pytest)
    for what, loc, exp in (("caption", table.locator("caption"), tx["caption"]), ("how-to-read card", page.locator("#by-type-howto"), tx["how_to_read"]),
                           ("tender caption", page.locator("#by-type-tender"), tx["tender_caption"])):
        got = text(loc, what)
        if got is not None and got != exp:
            say(f"{what} reads {got!r}, expected {exp!r}")

    # 6. the word "publish" anywhere in the #/unknowns view (CHG-2026-034 changed the last state wording there: nothing is left to allow)
    try:
        view = page.locator("#view")
        whole = re.sub(r"\s+", " ", view.inner_text(timeout=3000) if view.count() else page.locator("body").inner_text(timeout=3000))
        for m in re.finditer(r"publish", whole, re.I):
            say(f"the word 'publish' appears in the view: ...{whole[max(0, m.start() - 40):m.end() + 40]}...")
    except Exception as exc:
        say(f"page text could not be scanned for 'published' ({type(exc).__name__})")


def check_gap_lines(page, vname, app, problems, cov):
    """CHG-2026-034 (option A): the note under the headline (home), on the coverage page and on the report card equals core_gap_lines(coverage.json);
    the headline itself is still there and unchanged; the report card and glossary no longer say 'not published'."""
    base = app.split("#")[0]
    want = core_gap_lines(cov)
    h = cov["headline"]

    def say(where, msg):
        problems.append(f"{vname} gap-lines/{where}: {msg}")

    for where, hash_ in (("home", "#/"), ("coverage", "#/coverage"), ("report-card", "#/m/MUN:BUF/card")):
        page.goto(base + hash_)
        page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
        box = page.locator("#gap-lines")
        if not want:
            if box.count():
                say(where, "a gap note is shown although no core type has an empty year")
        elif box.count() != 1:
            say(where, f"expected 1 gap note, found {box.count()}")
        elif not box.is_visible():
            say(where, "gap note present but not visible")
        else:
            got = [re.sub(r"\s+", " ", t).strip() for t in box.locator("p > b").all_inner_texts()]
            if got != want:
                say(where, f"gap lines read {got!r}, expected {want!r}")
            if where == "home":
                kpi = page.locator(".kpi").first
                kt = re.sub(r"\s+", " ", kpi.inner_text())
                for need in (f"{h['complete_pct']}%", f"{h['complete']} of {h['applicable']}"):
                    if need not in kt:
                        say(where, f"the headline card no longer shows {need!r}: {kt!r}")
                kb, bb = kpi.bounding_box(), box.bounding_box()
                if kb and bb and bb["y"] - (kb["y"] + kb["height"]) > 80:
                    say(where, "the gap note is not next to the headline card")
            if where != "report-card" and not page.locator('#gap-lines a[href="#/unknowns"]').count():
                say(where, "gap note has no link to #/unknowns")
        if where == "report-card":
            txt = re.sub(r"\s+", " ", page.locator("#view").inner_text(timeout=3000))
            for bad in BANNED_STATE_WORDING:
                if bad in txt:
                    say(where, f"state wording {bad!r} is still on the report card")
    page.goto(base + "#/glossary")
    page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
    txt = re.sub(r"\s+", " ", page.locator("#view").inner_text(timeout=3000))
    for bad in BANNED_STATE_WORDING + ("has not published it",):
        if bad in txt:
            say("glossary", f"state wording {bad!r} is still in the glossary")


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
    cov = json.loads((ROOT / "public-data" / "v1" / "coverage.json").read_text())
    mun = json.loads((ROOT / "public-data" / "v1" / "municipalities.json").read_text())
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
            check_by_type(page, vname, app, problems, cov, mun)      # CHG-2026-033: "By data type" table, banner, notes, order, text
            check_gap_lines(page, vname, app, problems, cov)        # CHG-2026-034: note under the headline, coverage page, report card; wording
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
