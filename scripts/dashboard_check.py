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
from thusa.coverage_ceiling import by_province, core_gap_lines, headline_context_lines, model, province_order  # noqa: E402
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
BANNED_STATE_WORDING = ("not published", "has not published", "has not been published", "blank: not published", "data items published")
MIN_OPACITY = 0.9
MIN_CONTRAST = 3.0          # text colour against its effective background; real text on this page is >= 4.5 (axe checks that), so 3 only catches hidden text
MIN_FONT_PX = 8             # anything smaller is not readable text (font-size:0 and the like)
MIN_BOX_PX = 8
# Runs in the page: for the element and every descendant that holds its own text, the effective opacity (own x every ancestor), the
# computed text colour with its alpha, the effective background (blended up the ancestors, white when none is opaque), the font size
# and the box. Hidden-text tricks (transparent or background-coloured text, font-size:0, opacity on a container, a zero-size box, text pushed off the
# page, text-indent, clip-path, filter:opacity, a hidden-overflow container that clips the text) show here.
READABILITY_JS = """root => {
  const rgba = c => { const m = c.match(/rgba?\\(([^)]*)\\)/); if (!m) return [0, 0, 0, 0]; const v = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const bgOf = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] === 1) break; }
    let out = [255, 255, 255]; for (const c of layers.reverse()) out = out.map((x, i) => c[i] * c[3] + x * (1 - c[3])); return out; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const out = [], els = [root, ...root.querySelectorAll('*')];
  for (const el of els) {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect(), fg = rgba(cs.color), bg = bgOf(el);
    let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    const eff = [0, 1, 2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3])), l1 = lum(eff), l2 = lum(bg);
    const hide = [];
    if (parseFloat(cs.textIndent) <= -100) hide.push('text-indent ' + cs.textIndent);
    if (r.right + scrollX <= 0 || r.bottom + scrollY <= 0) hide.push('positioned off the page');
    for (let a = el; a; a = a.parentElement) {
      const ac = getComputedStyle(a);
      if (ac.clipPath && ac.clipPath !== 'none') hide.push('clip-path ' + ac.clipPath + ' on <' + a.tagName.toLowerCase() + '>');
      const fm = /opacity\\(\\s*([0-9.]+)(%?)/.exec(ac.filter || ''); if (fm && parseFloat(fm[1]) / (fm[2] ? 100 : 1) < 0.9) hide.push('filter ' + ac.filter + ' on <' + a.tagName.toLowerCase() + '>');
      if (/inset\\(|rect\\(/.test(ac.clip || '') ) hide.push('clip ' + ac.clip + ' on <' + a.tagName.toLowerCase() + '>');
      if (ac.overflowX === 'hidden' || ac.overflowX === 'clip' || ac.overflowY === 'hidden' || ac.overflowY === 'clip') {   // scroll containers (auto/scroll) are not a clip
        const ar = a.getBoundingClientRect(), ix = Math.max(0, Math.min(r.right, ar.right) - Math.max(r.left, ar.left)), iy = Math.max(0, Math.min(r.bottom, ar.bottom) - Math.max(r.top, ar.top));
        if (r.width * r.height > 0 && ix * iy < 0.5 * r.width * r.height) hide.push('clipped by <' + a.tagName.toLowerCase() + '> (overflow hidden)');
      }
    }
    out.push({tag: el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''), opacity: o, alpha: fg[3], contrast: (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05),
              font: parseFloat(cs.fontSize), w: r.width, h: r.height, vis: cs.visibility, disp: cs.display, hide});
  }
  return out; }"""


def readable(loc, what, say):
    """Text that exists and is 'visible' to Playwright but cannot be read: faded (effective opacity, ancestors included), transparent or
    background-coloured text, font-size 0, a zero-size box. Applies to the element and to every descendant that holds text."""
    try:
        items = loc.evaluate(READABILITY_JS, timeout=2000)
    except Exception as exc:
        say(f"{what}: readability could not be read ({type(exc).__name__})")
        return
    if not items:
        say(f"{what}: no text found to check")
    for it in items:
        why = []
        if it["opacity"] < MIN_OPACITY:
            why.append(f"effective opacity {it['opacity']:.2f} is below {MIN_OPACITY}")
        if it["alpha"] < MIN_OPACITY:
            why.append(f"the text colour is transparent (alpha {it['alpha']:.2f})")
        elif it["contrast"] < MIN_CONTRAST:
            why.append(f"the text colour is too close to its background (contrast {it['contrast']:.2f}:1, needs {MIN_CONTRAST}:1)")
        if it["font"] < MIN_FONT_PX:
            why.append(f"font size {it['font']}px")
        if it["w"] < MIN_BOX_PX or it["h"] < MIN_BOX_PX:
            why.append(f"box {it['w']:.0f}x{it['h']:.0f}px")
        if it["vis"] != "visible" or it["disp"] == "none":
            why.append(f"visibility {it['vis']}, display {it['disp']}")
        why.extend(sorted(set(it.get("hide", []))))
        if why:
            say(f"{what}: text in <{it['tag']}> is not readable: " + "; ".join(why))


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
            got = re.sub(r"\s+", " ", loc.inner_text(timeout=2000)).strip()
            readable(loc, what, say)
            return got
        except Exception as exc:                      # a broken page must be reported, never crash the whole check
            say(f"{what}: could not be read ({type(exc).__name__})")
            return None

    def top(loc):
        try:
            bb = loc.bounding_box(timeout=2000)
            return bb["y"] if bb else None
        except Exception:
            return None

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
    #    and "(at most x% with the data loaded today)" is shown for exactly the types with an empty year
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
            if got != f"{c['P']} of {c['n']}":
                say(f"cell {p}/{dt} shows {got!r}, data says '{c['P']} of {c['n']}'")
            title = nn.get_attribute("title", timeout=2000) or ""
            if title != f"{c['P']} of {c['n']} municipality-years":
                say(f"cell {p}/{dt} n-of-N title is {title!r}, expected the count with its unit 'municipality-years'")
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
                g = text(hp, f"cell {p}/{dt} at-most text")
                if g is not None and g != wanted_hp:
                    say(f"cell {p}/{dt} reads {g!r}, expected {wanted_hp!r}")
            elif hp.count():
                say(f"cell {p}/{dt} has an at-most text but no year is empty for {dt}")
    # 3b. sideways-scroll hint: visible (exact text) exactly while the table is wider than its box, hidden otherwise
    try:
        over = bt.locator(".tablewrap").evaluate("e => e.scrollWidth > e.clientWidth + 1")
        hint = page.locator("#by-type-scrollhint")
        if over:
            got = text(hint, "scroll hint")
            if got is not None and got != tx["scroll_hint"]:
                say(f"scroll hint reads {got!r}, expected {tx['scroll_hint']!r}")
        elif hint.count() != 1 or hint.is_visible():
            say("the scroll hint is shown although the table fits (or is missing from the page)")
    except Exception as exc:
        say(f"scroll hint could not be checked ({type(exc).__name__})")
    # 3c. no sideways overflow of the page itself, and a table that scrolls sideways is reachable from the keyboard (focusable, named, arrow keys scroll it)
    try:
        wrap = bt.locator(".tablewrap")
        if page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"):
            say("the page scrolls sideways (horizontal overflow outside the table)")
        if over:
            if wrap.get_attribute("tabindex") != "0":
                say("the by-type table scrolls sideways but is not keyboard-focusable (needs tabindex=0)")
            if not (wrap.get_attribute("aria-label") or "").strip() or wrap.get_attribute("role") != "region":
                say("the by-type table scrolls sideways but has no accessible name (role=region and aria-label)")
            wrap.focus()
            before = wrap.evaluate("e => e.scrollLeft")
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(250)
            if not wrap.evaluate("(e, b) => e.scrollLeft > b", before):
                say("the by-type table does not scroll sideways with the arrow keys")
            wrap.evaluate("e => { e.scrollLeft = 0; }")
    except Exception as exc:
        say(f"overflow and keyboard scrolling could not be checked ({type(exc).__name__})")
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
    for what, loc, exp in (("caption", page.locator("#by-type-caption"), tx["caption"]), ("csv note", page.locator("#by-type-csvnote"), tx["csv_note"]), ("legend (unit of x of y)", page.locator("#by-type-legend"), tx["legend"]),
                           ("how-to-read card", page.locator("#by-type-howto"), tx["how_to_read"]),
                           ("tender caption", page.locator("#by-type-tender"), tx["tender_caption"])):
        got = text(loc, what)
        if got is not None and got != exp:
            say(f"{what} reads {got!r}, expected {exp!r}")

    # 5b. the caption is fully visible: a paragraph above the scrolling box (never inside it) and no wider than the screen (it was clipped at 390 px)
    try:
        cap = page.locator("#by-type-caption")
        if cap.count() == 1:
            ok = cap.evaluate("e => !e.closest('.tablewrap') && e.getBoundingClientRect().left >= 0 && e.getBoundingClientRect().right <= innerWidth + 1 && e.scrollWidth <= e.clientWidth + 1")
            if not ok:
                say("the caption is inside the scrolling box, wider than the screen or clipped (it must be fully visible)")
    except Exception as exc:
        say(f"caption visibility could not be checked ({type(exc).__name__})")

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
    want_ctx = headline_context_lines(cov)
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
            # the note must be READABLE, not only present: effective opacity (ancestors included), non-transparent colour that differs from the
            # effective background (white on white), font size > 0, a real box; and it never uses the word 'publish' (nor do its context lines)
            readable(box, f"gap note ({where})", lambda m, w=where: say(w, m))
            whole = re.sub(r"\s+", " ", box.inner_text(timeout=2000))
            if re.search(r"publish", whole, re.I):
                say(where, f"the word 'publish' appears in the gap note: {whole!r}")
            ctx = [re.sub(r"\s+", " ", t).strip() for t in box.locator('p[data-note="context"]').all_inner_texts()]
            if ctx != (want_ctx if where == "home" else []):
                say(where, f"headline context lines read {ctx!r}, expected {(want_ctx if where == 'home' else [])!r}")
            if where == "home":
                kpi = page.locator(".kpi").first
                kt = re.sub(r"\s+", " ", kpi.inner_text())
                for need in (f"{h['complete_pct']}%", f"{h['complete']} of {h['applicable']} municipality-years"):
                    if need not in kt:
                        say(where, f"the headline card no longer shows {need!r}: {kt!r}")
                kb, bb = kpi.bounding_box(), box.bounding_box()
                if kb and bb and bb["y"] - (kb["y"] + kb["height"]) > 80:
                    say(where, "the gap note is not next to the headline card")
            if where == "coverage":
                fl = dict(zip(cov["years"], cov["fy_labels"]))
                sent = page.locator('#view p.small.muted:has-text("Headline:")')
                want_sent = (f"Headline: {h['complete_pct']}% of municipality-years from {fl[h['fye_min']]} to {fl[h['fye_max']]} have every core data type "
                             f"(budget, audited actuals, irregular & wasteful spending, audit opinion).")
                if sent.count() != 1:
                    say(where, f"expected 1 headline sentence, found {sent.count()}")
                else:
                    readable(sent, "coverage headline sentence", lambda m: say("coverage", m))
                    got_s = re.sub(r"\s+", " ", sent.inner_text(timeout=2000)).strip()
                    if got_s != want_sent:
                        say(where, f"headline sentence reads {got_s!r}, expected {want_sent!r}")
            if where != "report-card" and not page.locator('#gap-lines a[href="#/unknowns"]').count():
                say(where, "gap note has no link to #/unknowns")
        if where == "report-card":
            txt = re.sub(r"\s+", " ", page.locator("#view").inner_text(timeout=3000))
            for bad in BANNED_STATE_WORDING:
                if bad in txt:
                    say(where, f"state wording {bad!r} is still on the report card")
    # home KPI: the tender count says what it counts, not that the source "published" it
    page.goto(base + "#/")
    page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
    kpis = [re.sub(r"\s+", " ", t).strip() for t in page.locator(".kpi span").all_inner_texts()]
    if sum(1 for t in kpis if re.fullmatch(r"tender award records", t)) != 1 or any("published" in t for t in kpis if "tender" in t):
        say("home", f"the tender KPI label must read exactly 'tender award records' (no 'published'): {kpis!r}")
    # coverage map, tender awards: every 'not applicable' cell with the old reason now says what it means
    page.goto(base + "#/coverage?dt=procurement")
    page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
    titles = page.locator("table.heat td").evaluate_all("els => els.map(e => e.title)")
    new, old = "tender award records are not counted for this year", "was not publishing"
    n_new = sum(1 for t in titles if t.endswith(": " + new))
    n_exp = sum(1 for e in cov["entities"] for r in e["r"]["procurement"] if r not in ("0", 0) and cov["reasons"][int(r) - 1] == "source_not_publishing_yet")
    if n_new != n_exp or any(old in t for t in titles):
        say("coverage", f"{n_new} tender cells say {new!r}, expected {n_exp} (from coverage.json); old wording present: {any(old in t for t in titles)}")
    # #/unknowns: the lead sentence
    page.goto(base + "#/unknowns")
    page.wait_for_selector('#view[aria-busy="false"]', timeout=30000)
    lead = page.locator("#view p.lead")
    fl = {y: l for y, l in zip(cov["years"], cov["fy_labels"])}
    want_lead = (f"For each province, how much of the expected data PublicFunds has for its municipalities, over the financial years "
                 f"{fl[h['fye_min']]} to {fl[h['fye_max']]} (the years whose audits are due). Lowest first, so the biggest blind spots are at the top.")
    if lead.count() != 1:
        say("unknowns", f"expected 1 lead sentence, found {lead.count()}")
    else:
        readable(lead, "unknowns lead", lambda m: say("unknowns", m))
        got = re.sub(r"\s+", " ", lead.inner_text(timeout=2000)).strip()
        if got != want_lead:
            say("unknowns", f"lead reads {got!r}, expected {want_lead!r}")
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
