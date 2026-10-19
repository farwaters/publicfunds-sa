"""Public static snapshot (ADR-0003) with the publication policy of ADR-0008 / config/publication.yaml.

Only flags whose review status is `confirmed` on the CURRENT evidence are published as findings-to-date. Everything
else is excluded (default) or, with `unconfirmed: label`, listed as an unreviewed lead - except flags that name a
supplier or person, which are never shown until confirmed (ADR-0005). Reviewer names and notes are never published.
Output: dist/public/index.html, flags.json, flags.csv, coverage.json.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
from datetime import datetime, timezone

import duckdb
from jinja2 import Environment, select_autoescape

from thusa.review.service import Service, _csv_safe
from thusa.review.store import SAST
from thusa.settings import Paths, publication_config

PUBLIC_COLS = ["flag_id", "publication_label", "detector_id", "detector_version", "severity", "title", "explanation",
               "gov_body_id", "body_name", "period_label", "confirmed_at_sast", "review_reason", "evidence_urls"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Thusa - public snapshot</title>
<style>body{font:15px/1.5 system-ui,sans-serif;max-width:960px;margin:0 auto;padding:1rem;color:#1d2329}
.banner{background:#fff7e0;border:1px solid #f0d68a;padding:.6rem .8rem;border-radius:6px}
.card{border:1px solid #dde1e6;border-radius:8px;padding:.8rem 1rem;margin:.8rem 0}
.lead{border-style:dashed;background:#fafbfc}.lbl{font-size:.78rem;font-weight:600;text-transform:uppercase;color:#5d6670}
small{color:#5d6670}</style></head><body>
<h1>Thusa: South African public-spending data - public snapshot</h1>
<p class="banner">Generated {{ generated }} from build {{ build_id }}. Coverage: <b>{{ h.complete_pct }}%</b> of
municipality-years have complete core data ({{ h.complete }} of {{ h.applicable }}; {{ h.entities }} municipalities).
Flags are automated indicators checked by people; a published flag means reviewers confirmed the data pattern is real,
<b>not</b> that anyone acted unlawfully.</p>
<h2>Confirmed flags ({{ confirmed|length }})</h2>
{% for f in confirmed %}<div class="card"><div class="lbl">Confirmed by review · {{ f.detector_id.split('_')[0] }} · {{ f.severity }}</div>
<b>{{ f.title }}</b><p>{{ f.explanation }}</p>{% if f.review_reason %}<p><small>Review note: {{ f.review_reason }}</small></p>{% endif %}
<small>Confirmed {{ f.confirmed_at_sast }} · evidence: {% for u in f.evidence_urls %}<a href="{{ u }}" rel="nofollow noopener">source {{ loop.index }}</a> {% endfor %}</small></div>
{% else %}<p>No flags have been confirmed by review yet.</p>{% endfor %}
{% if leads %}<h2>Unreviewed leads ({{ leads|length }}) - not findings</h2>
<p><small>These automated indicators have not been confirmed by a reviewer. They may be data errors. Indicators that
name a supplier or person are never shown here.</small></p>
{% for f in leads %}<div class="card lead"><div class="lbl">Unreviewed lead · {{ f.detector_id.split('_')[0] }}</div>
{{ f.title }}<br><small>{% for u in f.evidence_urls %}<a href="{{ u }}" rel="nofollow noopener">source {{ loop.index }}</a> {% endfor %}</small></div>{% endfor %}
{% endif %}
<p><small>Data: flags.json, flags.csv, coverage.json in this folder. Policy: unconfirmed flags {{ policy }}.</small></p>
</body></html>"""


def public_flags(paths: Paths, policy: dict | None = None) -> tuple[list[dict], list[dict], dict]:
    policy = policy or publication_config()["flags"]
    mode = policy.get("unconfirmed", "exclude")
    if mode not in ("exclude", "label"):
        raise ValueError(f"publication.yaml flags.unconfirmed must be exclude or label, not {mode!r}")
    svc = Service(paths)
    flags = svc.list_flags()
    decs: dict[str, list[dict]] = {}
    for d in svc.store.decisions():
        decs.setdefault(d["flag_id"], []).append(d)
    confirmed, leads = [], []
    for f in flags:
        urls = [e["url"] for e in f["evidence"] if isinstance(e.get("url"), str) and e["url"].startswith("https://")]
        base = {"flag_id": f["flag_id"], "detector_id": f["detector_id"], "detector_version": f["detector_version"],
                "severity": f["severity"], "title": f["title"], "explanation": f["explanation"],
                "gov_body_id": f["gov_body_id"], "body_name": f["body_name"], "period_label": f["period_label"],
                "evidence_urls": urls}
        if f["publishable"]:
            last = decs[f["flag_id"]][-1]
            confirmed.append({**base, "publication_label": "confirmed by review",
                              "confirmed_at_sast": last["decided_at_sast"],
                              "review_reason": last["reason"] if policy.get("show_review_reason", True) else None})
        elif mode == "label" and not f["names_supplier"] and f["status"] != "rejected":
            leads.append({**base, "publication_label": "unreviewed lead - not a finding", "explanation": None,
                          "confirmed_at_sast": None, "review_reason": None})
    return confirmed, leads, {"unconfirmed": mode}


def render_public(paths: Paths, policy: dict | None = None) -> dict:
    from thusa.report import headline
    confirmed, leads, pol = public_flags(paths, policy)
    out = paths.dist / "public"
    tmp = paths.dist / "public.building"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    con = duckdb.connect(str(paths.warehouse), read_only=True)
    try:
        h = headline(con)
        bid = con.execute("SELECT build_id FROM ops.build ORDER BY 1 DESC LIMIT 1").fetchone()[0]
    finally:
        con.close()
    gen = datetime.now(timezone.utc).astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")
    env = Environment(autoescape=select_autoescape(default=True))
    (tmp / "index.html").write_text(env.from_string(PAGE).render(
        confirmed=confirmed, leads=leads, h=h, build_id=bid, generated=gen, policy=pol["unconfirmed"]),
        encoding="utf-8")
    rows = confirmed + leads
    (tmp / "flags.json").write_text(json.dumps({"generated": gen, "build_id": bid, "policy": pol, "flags": rows},
                                               indent=1, ensure_ascii=False), encoding="utf-8")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=PUBLIC_COLS)
    w.writeheader()
    for r in rows:
        w.writerow({k: _csv_safe(" ".join(r[k]) if k == "evidence_urls" else r[k]) for k in PUBLIC_COLS})
    (tmp / "flags.csv").write_text(buf.getvalue(), encoding="utf-8")
    (tmp / "coverage.json").write_text(json.dumps(h, indent=1, default=str), encoding="utf-8")
    shutil.rmtree(out, ignore_errors=True)
    tmp.replace(out)
    return {"public_dir": str(out), "confirmed": len(confirmed), "leads": len(leads), "policy": pol}
