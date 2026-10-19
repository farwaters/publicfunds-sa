"""Static INTERNAL dashboard + PNG charts generated from the warehouse (dist/ is git-ignored).

Outputs: dist/site/index.html, dist/site/muni/<CODE>.html, dist/coverage_heatmap.png, dist/coverage_by_type.png,
dist/flags_summary.png, dist/summary.json. Screenshots: dist/screenshot_*.png (headless Chrome, if present).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from jinja2 import Environment, select_autoescape  # noqa: E402

from thusa.settings import Paths  # noqa: E402

STATE_ORDER = ["present", "partial", "missing", "n.a."]
STATE_COLOURS = {"present": "#1a9850", "complete": "#1a9850", "partial": "#fdae61", "missing": "#d73027",
                 "n.a.": "#d9d9d9"}
SEV_ORDER = {"high": 0, "med": 1, "low": 2, "info": 3}
TYPES = ["budget", "actual_audited", "uifw", "audit_opinion", "procurement"]
TYPE_LABEL = {"budget": "Budget (orig. + adj.)", "actual_audited": "Audited actuals", "uifw": "UIF&W expenditure",
              "audit_opinion": "Audit opinion", "procurement": "eTenders awards"}


def _rows(con, sql, params=None):
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def rand(cents):
    if cents is None:
        return "unknown"
    v = cents / 100
    for div, suf in ((1e9, "bn"), (1e6, "m")):
        if abs(v) >= div:
            return f"R{v / div:,.1f}{suf}"
    return f"R{v:,.0f}"


def headline(con) -> dict:
    h = _rows(con, """SELECT count(*) FILTER (WHERE core_state <> 'n.a.') AS applicable,
        count(*) FILTER (WHERE core_state = 'complete') AS complete,
        count(*) FILTER (WHERE core_state = 'partial') AS partial,
        count(*) FILTER (WHERE core_state = 'missing') AS missing,
        count(DISTINCT gov_body_id) FILTER (WHERE core_state <> 'n.a.') AS entities,
        min(fye) AS fye_min, max(fye) AS fye_max FROM marts.coverage_entity_year WHERE all_core_due""")[0]
    h["complete_pct"] = round(100 * h["complete"] / h["applicable"], 1) if h["applicable"] else None
    cells = _rows(con, """SELECT data_type, state, count(*) AS n FROM marts.coverage_cell
        WHERE (gov_body_id, fye) IN (SELECT (gov_body_id, fye) FROM marts.coverage_entity_year WHERE core_state <> 'n.a.' AND all_core_due)
        GROUP BY ALL""")
    by_type = {t: {s: 0 for s in STATE_ORDER} for t in TYPES}
    for c in cells:
        by_type[c["data_type"]][c["state"]] = c["n"]
    for t, d in by_type.items():
        app = sum(v for k, v in d.items() if k != "n.a.")
        d["present_pct"] = round(100 * d["present"] / app, 1) if app else None
    h["by_type"] = by_type
    h["by_year"] = _rows(con, """SELECT fye, fy_label, count(*) FILTER (WHERE core_state <> 'n.a.') AS applicable,
        count(*) FILTER (WHERE core_state = 'complete') AS complete, bool_and(all_core_due) AS all_core_due
        FROM marts.coverage_entity_year GROUP BY ALL ORDER BY fye""")
    return h


# ------------------------------------------------------------------------------------------------ charts
def chart_coverage_heatmap(con, out: Path) -> None:
    """The coverage model itself: one panel per data type, municipality (rows, grouped by province) x year."""
    rows = _rows(con, """SELECT c.gov_body_id, c.province, c.body_type, c.name, c.fye, c.data_type, c.state
        FROM marts.coverage_cell c WHERE gov_body_id IN (SELECT gov_body_id FROM marts.coverage_entity_year
        GROUP BY 1 HAVING bool_or(core_state <> 'n.a.')) ORDER BY province, body_type, name, fye""")
    ents = list(dict.fromkeys((r["gov_body_id"], r["province"]) for r in rows))
    years = sorted({r["fye"] for r in rows})
    idx = {e[0]: i for i, e in enumerate(ents)}
    code = {"present": 0, "partial": 1, "missing": 2, "n.a.": 3}
    grids = {t: [[3] * len(years) for _ in ents] for t in TYPES}
    for r in rows:
        grids[r["data_type"]][idx[r["gov_body_id"]]][years.index(r["fye"])] = code[r["state"]]
    cmap = ListedColormap([STATE_COLOURS[s] for s in STATE_ORDER])
    fig, axes = plt.subplots(1, len(TYPES), figsize=(15, 16), sharey=True)
    prov_pos: dict[str, list[int]] = {}
    for i, e in enumerate(ents):
        prov_pos.setdefault(e[1], []).append(i)
    for ax, t in zip(axes, TYPES):
        ax.imshow(grids[t], aspect="auto", cmap=cmap, vmin=-0.5, vmax=3.5, interpolation="nearest")
        ax.set_xticks(range(len(years)), [f"{y-1}/{str(y)[-2:]}" for y in years], rotation=60, fontsize=8)
        ax.set_title(TYPE_LABEL[t], fontsize=10)
        for v in prov_pos.values():
            ax.axhline(max(v) + 0.5, color="white", lw=1.2)
    axes[0].set_yticks([sum(v) / len(v) for v in prov_pos.values()], list(prov_pos.keys()), fontsize=9)
    fig.suptitle(f"Coverage model: {len(ents)} municipalities x financial year x data type "
                 "(computed from loaded data)", fontsize=12)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATE_COLOURS[s]) for s in STATE_ORDER]
    fig.legend(handles, ["present", "partial", "missing", "n.a. (not yet due / source not live / not in existence)"],
               loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_coverage_by_type(con, out: Path) -> None:
    rows = _rows(con, """SELECT data_type, fye, count(*) FILTER (WHERE state='present') AS p,
        count(*) FILTER (WHERE state <> 'n.a.') AS app FROM marts.coverage_cell GROUP BY ALL""")
    years = sorted({r["fye"] for r in rows})
    m = {(r["data_type"], r["fye"]): r for r in rows}
    fig, ax = plt.subplots(figsize=(10, 3.6))
    data = []
    for t in TYPES:
        line = []
        for y in years:
            r = m.get((t, y))
            line.append(None if not r or not r["app"] else r["p"] / r["app"])
        data.append(line)
    import numpy as np
    arr = np.array([[np.nan if v is None else v for v in line] for line in data], dtype=float)
    im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    for i, line in enumerate(data):
        for j, v in enumerate(line):
            ax.text(j, i, "n.a." if v is None else f"{v:.0%}", ha="center", va="center", fontsize=9)
    ax.set_xticks(range(len(years)), [f"{y-1}/{str(y)[-2:]}" for y in years])
    ax.set_yticks(range(len(TYPES)), [TYPE_LABEL[t] for t in TYPES])
    ax.set_title("Share of municipalities with the data type fully present (n.a. = not yet due / source not live)",
                 fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.02)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def chart_flags(con, out: Path) -> None:
    rows = _rows(con, "SELECT detector_id, severity, count(*) AS n FROM marts.flag GROUP BY ALL")
    dets = sorted({r["detector_id"] for r in rows})
    sev = ["high", "med", "low", "info"]
    col = {"high": "#b2182b", "med": "#ef8a62", "low": "#fddbc7", "info": "#d1e5f0"}
    fig, ax = plt.subplots(figsize=(10, 3.8))
    left = [0] * len(dets)
    for s in sev:
        vals = [next((r["n"] for r in rows if r["detector_id"] == d and r["severity"] == s), 0) for d in dets]
        ax.barh(range(len(dets)), vals, left=left, color=col[s], label=s, edgecolor="grey", lw=0.3)
        for i, v in enumerate(vals):
            if v:
                ax.text(left[i] + v / 2, i, str(v), ha="center", va="center", fontsize=8)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_yticks(range(len(dets)), [d.replace("_", " ") for d in dets], fontsize=9)
    ax.invert_yaxis()
    ax.legend(title="severity", fontsize=8)
    ax.set_title("Automated red-flag indicators by detector - ALL UNREVIEWED (not findings)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ HTML
BASE_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#222;background:#fafafa}
header{background:#123;color:#fff;padding:14px 24px}header h1{margin:0;font-size:20px}header p{margin:4px 0 0;opacity:.8;font-size:13px}
main{padding:18px 24px;max-width:1280px}
.banner{background:#fff3cd;border:1px solid #e0c36b;padding:8px 12px;border-radius:6px;font-size:13px;margin-bottom:14px}
.kpis{display:flex;gap:12px;flex-wrap:wrap}.kpi{background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 14px;min-width:150px}
.kpi b{font-size:26px;display:block}.kpi span{font-size:12px;color:#555}
table{border-collapse:collapse;background:#fff;font-size:13px;width:100%}th,td{border:1px solid #e3e3e3;padding:5px 7px;text-align:left;vertical-align:top}
th{background:#f0f2f5}.sev{font-weight:600;padding:1px 6px;border-radius:4px;font-size:11px}
.sev-high{background:#b2182b;color:#fff}.sev-med{background:#ef8a62}.sev-low{background:#fddbc7}.sev-info{background:#d1e5f0}
.rev{font-size:11px;color:#8a5a00;font-weight:600}.st{display:inline-block;width:100%;text-align:center;border-radius:3px;font-size:11px}
.st-present{background:#1a9850;color:#fff}.st-partial{background:#fdae61}.st-missing{background:#d73027;color:#fff}.st-na{background:#d9d9d9}
h2{font-size:17px;margin-top:22px}img{max-width:100%;border:1px solid #ddd;background:#fff}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
small,.muted{color:#666;font-size:12px}a{color:#0b5ea8}
"""

INDEX = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Thusa MVP - SA public spending coverage & flags</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{{ css }}</style></head><body>
<header><h1>Thusa (MVP v0.1.0) - South African public spending: what we know, what we don't, what looks odd</h1>
<p>Local snapshot built {{ s.build_id }} from raw files fetched {{ fetched }} (SAST). Commit {{ s.git_commit }}.</p></header><main>
<div class="banner"><b>INTERNAL working dashboard - not for publication</b> (the public snapshot is <code>dist/public/</code>, confirmed flags only). <b>Read this first:</b> every flag below is an <b>automated, unreviewed indicator</b>, not a finding of wrongdoing.
Flags that name a supplier are <b>pending human review</b> and are not published. Blank means unknown, never zero.</div>
<h2>Coverage headline</h2>
<div class="kpis">
<div class="kpi"><b>{{ h.complete_pct }}%</b><span>municipality-years with complete core data<br>({{ h.complete }} of {{ h.applicable }}; {{ h.entities }} municipalities, {{ h.fye_min - 1 }}/{{ (h.fye_min|string)[-2:] }}-{{ h.fye_max - 1 }}/{{ (h.fye_max|string)[-2:] }})</span></div>
<div class="kpi"><b>{{ h.partial }}</b><span>partial municipality-years</span></div>
<div class="kpi"><b>{{ h.missing }}</b><span>missing municipality-years</span></div>
{% for t in types %}<div class="kpi"><b>{{ h.by_type[t].present_pct }}%</b><span>{{ labels[t] }} present</span></div>{% endfor %}
</div>
<p class="muted">Core data = budget (original + adjusted), audited actuals, unauthorised/irregular/fruitless & wasteful expenditure,
and audit opinion. The headline counts only financial years whose audits are already due (as of {{ s.as_of }}); later years appear in the
table below as budget-only. eTenders awards are shown separately and are not in the headline.</p>
<div class="grid2"><div><img src="../coverage_by_type.png" alt="coverage by data type and year"></div>
<div><img src="../flags_summary.png" alt="flags summary"></div></div>
<h2>Coverage by year</h2><table><tr><th>Financial year</th><th>Applicable municipality-years</th><th>Complete</th><th>%</th><th>Note</th></tr>
{% for y in h.by_year %}<tr><td>{{ y.fy_label }}</td><td>{{ y.applicable }}</td><td>{{ y.complete }}</td><td>{{ (100*y.complete/y.applicable)|round(1) if y.applicable else 'n.a.' }}</td><td><small>{{ '' if y.all_core_due else 'audits not yet due: budget only, excluded from headline' }}</small></td></tr>{% endfor %}</table>
<h2>Top flags (unreviewed)</h2>
<table><tr><th>Severity</th><th>Detector</th><th>Flag</th><th>Period</th><th>Status</th><th>Evidence</th></tr>
{% for f in flags %}<tr><td><span class="sev sev-{{ f.severity }}">{{ f.severity }}</span></td><td>{{ f.detector_id.split('_')[0] }}</td>
<td><b>{{ f.title }}</b><br><small>{{ f.explanation }}</small></td><td>{{ f.period_label }}</td>
<td><span class="rev">{{ f.review_status }}</span></td>
<td>{% for e in f.evidence %}{% if e.url %}<a href="{{ e.url }}">{{ e.label }}</a>{% else %}{{ e.label }}{% endif %}{% if e.locator %} <small>({{ e.locator }})</small>{% endif %}<br>{% endfor %}</td></tr>{% endfor %}</table>
<h2>Sources in this build</h2><table><tr><th>Source</th><th>Last status</th><th>Files</th><th>Fetched (UTC)</th><th>Notes</th></tr>
{% for r in runs %}<tr><td>{{ r.source_id }}</td><td>{{ r.status }}</td><td>{{ r.files }}</td><td>{{ r.ended_at_utc }}</td><td><small>{{ r.errors }} {{ r.notes }}</small></td></tr>{% endfor %}</table>
<h2>Municipality drill-downs</h2><p>{% for m in munis %}<a href="muni/{{ m.demarcation_code }}.html">{{ m.name }}</a>{{ ' · ' if not loop.last }}{% endfor %}</p>
<h2>Coverage map (all municipalities)</h2><img src="../coverage_heatmap.png" alt="coverage heatmap">
</main></body></html>"""

MUNI = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{{ m.name }} - Thusa</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{{ css }}</style></head><body>
<header><h1>{{ m.long_name }} ({{ m.demarcation_code }}, {{ m.body_type }})</h1><p><a style="color:#9cf" href="../index.html">&larr; overview</a> ·
<a style="color:#9cf" href="https://municipalmoney.gov.za/profiles/municipality-{{ m.demarcation_code }}/">Municipal Money profile</a></p></header><main>
<div class="banner">Automated snapshot. Blank / "unknown" = not published in the loaded sources; it is never shown as zero. Flags are unreviewed.</div>
<h2>Coverage</h2><table><tr><th>Data type</th>{% for y in years %}<th>{{ y.fy_label }}</th>{% endfor %}</tr>
{% for t in types %}<tr><td>{{ labels[t] }}</td>{% for y in years %}{% set c = cov.get((t, y.fye)) %}
<td><span class="st st-{{ 'na' if c.state == 'n.a.' else c.state }}" title="{{ c.reason_code }}">{{ c.state }}</span></td>{% endfor %}</tr>{% endfor %}</table>
<h2>Budget vs audited (operating, all items)</h2><table><tr><th>Year</th><th>Original budget exp.</th><th>Adjusted budget exp.</th><th>Audited exp.</th><th>Audited revenue</th><th>Basis</th></tr>
{% for r in fin %}<tr><td>{{ r.fy_label }}</td><td>{{ rand(r.orgb) }}</td><td>{{ rand(r.adjb) }}</td><td>{{ rand(r.auda) }}</td><td>{{ rand(r.rev) }}</td><td><small>{{ r.basis }}</small></td></tr>{% endfor %}</table>
<h2>Unauthorised, irregular, fruitless & wasteful (reported)</h2><table><tr><th>Year</th><th>Unauthorised</th><th>Irregular</th><th>Fruitless & wasteful</th><th>Audit opinion</th></tr>
{% for r in uifw %}<tr><td>{{ r.fy_label }}</td><td>{{ rand(r.u) }}</td><td>{{ rand(r.i) }}</td><td>{{ rand(r.f) }}</td><td>{% if r.report_url %}<a href="{{ r.report_url }}">{{ r.opinion_label }}</a>{% else %}{{ r.opinion_label or 'unknown' }}{% endif %}</td></tr>{% endfor %}</table>
<h2>Flags ({{ flags|length }}, unreviewed)</h2><table><tr><th>Severity</th><th>Flag</th><th>Status</th><th>Evidence</th></tr>
{% for f in flags %}<tr><td><span class="sev sev-{{ f.severity }}">{{ f.severity }}</span></td><td><b>{{ f.title }}</b><br><small>{{ f.explanation }}</small></td><td><span class="rev">{{ f.review_status }}</span></td>
<td>{% for e in f.evidence %}{% if e.url %}<a href="{{ e.url }}">{{ e.label }}</a>{% else %}{{ e.label }}{% endif %}<br>{% endfor %}</td></tr>{% else %}<tr><td colspan=4>No flags.</td></tr>{% endfor %}</table>
<h2>eTenders awards matched to this municipality</h2><p>{{ aw.n }} award-supplier rows, {{ aw.valued }} with a usable value, total known value {{ rand(aw.total) }}.</p>
<p class="muted">Lineage: every number above comes from curated tables carrying source, file, sha256 and fetch time (see warehouse).</p>
</main></body></html>"""


def render(paths: Paths, screenshot: bool = True) -> dict:
    dist = paths.dist
    site = dist / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "muni").mkdir(parents=True)
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    s = json.loads(con.execute("SELECT summary FROM ops.build").fetchone()[0])
    h = headline(con)
    chart_coverage_heatmap(con, dist / "coverage_heatmap.png")
    chart_coverage_by_type(con, dist / "coverage_by_type.png")
    chart_flags(con, dist / "flags_summary.png")
    env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))
    env.globals["rand"] = rand
    flags = _rows(con, """SELECT * FROM marts.flag ORDER BY
        CASE severity WHEN 'high' THEN 0 WHEN 'med' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, score DESC""")
    for f in flags:
        f["evidence"] = json.loads(f["evidence_json"])
    top = []  # balanced: top per detector so one detector cannot crowd out the rest
    for det in sorted({f["detector_id"] for f in flags}):
        top += [f for f in flags if f["detector_id"] == det and f["severity"] != "info"][:6] or \
               [f for f in flags if f["detector_id"] == det][:4]
    top.sort(key=lambda f: (SEV_ORDER[f["severity"]], -(f["score"] or 0)))
    runs = _rows(con, """SELECT * FROM ops.ingest_run QUALIFY row_number() OVER (PARTITION BY source_id ORDER BY ended_at_utc DESC) = 1
                         ORDER BY source_id""")
    fetched = con.execute("SELECT strftime(max(fetched_at_utc) AT TIME ZONE 'Africa/Johannesburg', '%Y-%m-%d %H:%M') FROM ops.raw_file").fetchone()[0]
    munis = _rows(con, """SELECT g.* FROM curated.gov_body g WHERE sphere='local' AND gov_body_id IN
        (SELECT gov_body_id FROM marts.coverage_entity_year WHERE core_state <> 'n.a.') ORDER BY name""")
    (site / "index.html").write_text(env.from_string(INDEX).render(
        css=BASE_CSS, s=s, h=h, types=TYPES, labels=TYPE_LABEL, flags=top, runs=runs, munis=munis, fetched=fetched))
    years = _rows(con, "SELECT DISTINCT fye, fy_label FROM marts.coverage_cell ORDER BY fye")
    tpl = env.from_string(MUNI)
    for m in munis:
        gid = m["gov_body_id"]
        cov = {(c["data_type"], c["fye"]): c for c in _rows(con, "SELECT * FROM marts.coverage_cell WHERE gov_body_id=?", [gid])}
        fin = _rows(con, """SELECT fy_label, max(total_expenditure_cents) FILTER (WHERE amount_type='ORGB') orgb,
            max(total_expenditure_cents) FILTER (WHERE amount_type='ADJB') adjb, max(total_expenditure_cents) FILTER (WHERE amount_type='AUDA') auda,
            max(total_revenue_cents) FILTER (WHERE amount_type='AUDA') rev, string_agg(DISTINCT expenditure_basis, ', ') basis
            FROM curated.muni_total WHERE gov_body_id=? GROUP BY fy_label ORDER BY fy_label""", [gid])
        uifw = _rows(con, """SELECT u.fy_label, max(amount_cents) FILTER (WHERE uifw_type='unauthorised') u,
            max(amount_cents) FILTER (WHERE uifw_type='irregular') i, max(amount_cents) FILTER (WHERE uifw_type='fruitless_wasteful') f,
            any_value(a.opinion_label) opinion_label, any_value(a.report_url) report_url
            FROM curated.uifw_line u LEFT JOIN curated.audit_outcome a USING (gov_body_id, fye) WHERE u.gov_body_id=? AND u.fye >= 2016
            GROUP BY u.fy_label ORDER BY u.fy_label""", [gid])
        mf = [f for f in flags if f["gov_body_id"] == gid]
        aw = _rows(con, """SELECT count(*) n, count(*) FILTER (WHERE value_cents IS NOT NULL AND value_note IS NULL) valued,
            sum(value_cents) FILTER (WHERE value_note IS NULL) total FROM curated.award WHERE buyer_gov_body_id=?""", [gid])[0]
        (site / "muni" / f"{m['demarcation_code']}.html").write_text(tpl.render(
            css=BASE_CSS, m=m, years=years, types=TYPES, labels=TYPE_LABEL, cov=cov, fin=fin, uifw=uifw, flags=mf, aw=aw))
    featured = _rows(con, """SELECT g.demarcation_code, g.name FROM marts.flag f JOIN curated.gov_body g ON g.gov_body_id=f.gov_body_id
        WHERE g.sphere='local' AND f.severity IN ('high','med') GROUP BY ALL ORDER BY count(*) DESC, g.name LIMIT 1""")
    con.close()
    out = {"site": str(site / "index.html"), "pngs": [str(dist / n) for n in
           ("coverage_heatmap.png", "coverage_by_type.png", "flags_summary.png")], "headline": h,
           "featured_muni": featured[0] if featured else None}
    from thusa.publish import render_public   # public snapshot: confirmed flags only (ADR-0008)
    out["public"] = render_public(paths)
    if screenshot:
        out["screenshots"] = screenshots(site, dist, featured[0]["demarcation_code"] if featured else None)
    (dist / "summary.json").write_text(json.dumps({"build": s, "report": out}, indent=1, default=str))
    return out


def screenshots(site: Path, dist: Path, muni_code: str | None) -> list[str]:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        return []
    shots = [("screenshot_dashboard.png", site / "index.html", "1400,2600")]
    if muni_code:
        shots.append((f"screenshot_muni_{muni_code}.png", site / "muni" / f"{muni_code}.html", "1400,1900"))
    done = []
    for name, page, size in shots:
        subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={size}", f"--screenshot={dist / name}", page.as_uri()],
                       capture_output=True, timeout=120)
        if (dist / name).exists():
            done.append(str(dist / name))
    return done
