"""Case referral pack (CHG-2026-016): one Markdown file for ONE hidden lead, for independent human checking.

POPIA: the pack carries no personal information. Columns that can hold personal data (contact points, person keys,
registration/ID numbers, emails, phones, addresses) are dropped by name; a supplier name that does not look like a
company is replaced by NATURAL_PERSON; the rendered text is then scanned and the pack is refused if an email,
phone number or 13-digit ID-like number remains. Packs are written under data/cases/ (gitignored), never committed.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from thusa.review.store import SAST

NATURAL_PERSON = "[natural person, see official record link]"
OCDS_RELEASE = "https://ocds-api.etenders.gov.za/api/OCDSReleases/release/{ocid}"
CW_REPORT = "https://www.corruptionwatch.org.za/report-corruption/"
GOV_HOTLINES = "https://www.gov.za/anti-corruption/hotlines"
HOTLINE = "0800 701 701"          # National Anti-Corruption Hotline (Public Service Commission), toll free
ALLOWED_PHONES = {re.sub(r"\D", "", HOTLINE)}

# Plain-language wording reused from the public glossary (apps/public-dashboard/index.html, CHG-2026-013).
GLOSSARY = {
    "D1": ("Overspending", "audited spending was well above the approved budget: more than 20% above it for a municipality's operating spending (not counting non-cash items such as depreciation), or any overspending of a national department's final appropriation. Budgets under R10 million are ignored."),
    "D3": ("Restricted supplier", "a tender was awarded to a name on National Treasury's restricted-supplier list while the restriction applied."),
    "D4": ("One supplier dominates", "over three years, one supplier won more than half of a buyer's tender value, and the buyer's awards were highly concentrated (Herfindahl-Hirschman index above 2 500). Only buyers with at least 10 awards worth R10 million or more in total are checked."),
    "D5": ("Missing award values", "at least half of a buyer's published awards have no value, R0, or an obviously wrong amount under R100."),
    "D8": ("Rising irregular expenditure", "reported irregular expenditure went up two years in a row and grew by at least 50% on the year before, to at least R10 million."),
    "D13": ("Fuel price too high", "a fuel payment works out at more than 20% above the highest official fuel price published by the Department of Mineral and Petroleum Resources (DMPR) for that fuel type and period."),
    "D6": ("Possible tender splitting", "one buyer gave one supplier two or more awards within 30 days, each under the competitive-bidding limit but together above it. Splitting can only be suspected from published awards, not shown."),
    "D16": ("Repeat awards", "one buyer gave the same supplier five or more awards with a known value (each to that supplier alone) within a year."),
    "D17": ("Just under the limit", "one buyer gave one supplier two or more awards within a year, each within 10% below the competitive-bidding limit."),
}
LIMITS = ("Competitive-bidding limits (glossary): municipalities R750 000 (metros), R300 000 (local), R200 000 (district), "
          "VAT incl., Municipal SCM Amendment Regulations (Gazette 49863, 14 Dec 2023); national and provincial "
          "departments R1 000 000 incl. taxes, PFMA SCM Instruction No. 02 of 2021/22.")
BASELINE = {
    "D1": "The approved budget (adjusted budget, else original budget; national: final appropriation) on the same basis, from the National Treasury Municipal Finance API / national budget data. Threshold: +20% (municipal operating), any overspend (national).",
    "D3": "The restriction window (period from / to) in National Treasury's Restricted Supplier and Tender Defaulter report: https://ocpo.treasury.gov.za/RestrictedSupplier/RestrictedSuppliersReport.pdf",
    "D4": "Thresholds: top supplier > 50% of the buyer's known award value and HHI > 2 500 over 3 years (min. 10 awards, R10 million).",
    "D5": "Threshold: at least half of the buyer's published awards have no value, R0 or under R100.",
    "D8": "The same municipality's irregular expenditure in the two previous years (AFS notes via the Municipal Finance API).",
    "D13": "The highest official DMPR fuel price for that fuel type and period; threshold +20%.",
    "D6": LIMITS, "D17": LIMITS,
    "D16": "Threshold: five or more single-supplier awards with a known value from one buyer within 365 days.",
}
ALTERNATIVES = {
    "D1": ["Budget or actuals captured on a different basis or in the wrong unit (data error at source).", "Unfunded mandates or emergencies later condoned by council.", "Audited figures restated; the adjusted budget not yet loaded."],
    "D3": ["A different entity with the same or a similar name (eTenders publishes no registration number).", "Award date is a proxy (release date), not the signing date; the real award may predate the restriction.", "Restriction lifted, set aside or suspended after the report was published."],
    "D4": ["Framework, panel or transversal contracts, or a sole provider of a specialised service.", "Few awards published by this buyer, so the share is distorted.", "Multi-supplier awards and awards without values are excluded."],
    "D5": ["The buyer captures values elsewhere or uses placeholders (data-quality gap, not spending).", "Rates-based or as-and-when contracts with no fixed value."],
    "D8": ["Closing balances reported instead of amounts incurred in the year.", "Historic irregular expenditure newly identified (better auditing), not new spending.", "One large contract re-classified."],
    "D13": ["Delivery, coastal/inland zone or wholesale vs retail price difference.", "Quantity or amount captured incorrectly."],
    "D6": ["Separate needs that happened to fall close together.", "Emergency procurement or framework call-offs."],
    "D16": ["Framework or panel call-offs, or a sole provider.", "Separate projects or regions under one buyer.", "Duplicate releases of the same award."],
    "D17": ["Prices legitimately set just below the limit by market quotes.", "Separate needs."],
}
CHECKLIST = [
    "Open every official source link below and confirm each figure, date and name matches the official record exactly.",
    "Confirm the supplier is the same legal entity in every record (use the official record; the pack deliberately omits registration numbers).",
    "Check the comparison baseline (budget, limit, register window or price) in its own official document.",
    "Check whether any innocent explanation listed below applies (AGSA report, council minutes, condonation, framework contract).",
    "Check whether the buyer or AGSA already reported or condoned the matter.",
    "Record your own conclusion independently, before comparing with the other checker.",
]
NOTICE = ("**This is not a finding of wrongdoing.** It is an automated indicator that a pattern in official public data "
          "deserves a closer look. It has not been confirmed. It may be a data error or have a lawful explanation. "
          "Do not publish it; refer it only after two independent checks hold up.")

DROP_COL = re.compile(r"person|email|e_mail|phone|tel|fax|mobile|contact|id_?num|identity|passport|cipc|reg_?no|"
                      r"registration|supplier_id|subject_id|address|is_person|path$", re.I)
NAME_COL = {"supplier_name", "name", "award_supplier", "register_name", "subject_name"}
COMPANY = re.compile(r"\b(pty|ltd|limited|cc|inc|npc|soc|jv|trust|trading|holdings|group|enterprises?|services?|"
                     r"solutions|consult\w*|construction|projects?|investments?|engineering|technolog\w*|systems|"
                     r"supplies|suppliers|advisory|office|logistics|security|motors?|civils?|properties|company|"
                     r"corporation|co|association|municipality|department|agency|bank|institute|labs?|media|energy|"
                     r"pharma\w*|medical|africa|sa|international|national|industries|partners|attorneys|contractors?|advisors?|"
                     r"assurance|insurance|ict|it|leasing|hire|rental|car|risk|multi|purpose|tourism|toerisme|events|"
                     r"management|building|catering|cleaning|transport|electrical|mining|farming|foods?|fuels?|oil|"
                     r"printing|stationery|hospital|clinic|school|college|university|council|board|fund|cooperative|"
                     r"primary|prm)\b", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<![\w./-])(?:\+27|0)\d{2}[\s-]?\d{3}[\s-]?\d{3,4}(?![\w/-])")
IDNUM = re.compile(r"(?<![\w])\d{13}(?![\w])")


class UnsafePack(Exception):
    pass


def looks_like_natural_person(name: str | None, is_person=None) -> bool:
    """Fail closed: a name counts as a company only if it carries a company/organisation word (or a number).
    Over-redaction is accepted; the checker reads the name in the linked official record."""
    if is_person in (True, 1, "1", "true", "True", "Y", "yes"):
        return True
    n = (name or "").strip()
    if re.search(r"\d| - |&", n):     # shelf-company numbers, "Province - Department", "X & Y"
        return False
    return bool(n) and not COMPANY.search(n)


def _rand(cents) -> str:
    try:
        return f"R{int(cents) / 100:,.0f}"
    except (TypeError, ValueError):
        return "unknown"


def _det(detector_id: str) -> str:
    return detector_id.split("_", 1)[0]


def _cell(col: str, v, persons: set[str]) -> str:
    if v is None or v == "":
        return "unknown" if col.endswith("cents") else ""
    if col.endswith("_cents"):
        return _rand(v)
    s = str(v)
    if col in NAME_COL and s in persons:
        return NATURAL_PERSON
    return s.replace("|", "\\|").replace("\n", " ")


def _persons(f: dict) -> set[str]:
    """Names in this flag that look like natural persons (and must not appear in the pack)."""
    found: set[str] = set()
    for _, rows in f["matched"]["tables"]:
        for r in rows:
            for c in NAME_COL & set(r):
                if r.get(c) and looks_like_natural_person(r[c], r.get("is_person")):
                    found.add(str(r[c]))
    m = f["matched"].get("match") or {}
    for c in ("award_supplier", "register_name"):
        if m.get(c) and looks_like_natural_person(m[c]):
            found.add(str(m[c]))
    if f.get("names_supplier"):
        sup = str(f.get("subject_name") or "").strip()
        if sup and looks_like_natural_person(sup.strip("()")):
            found.add(sup)
    return found


def _scrub(text: str, persons: set[str]) -> str:
    for p in sorted(persons, key=len, reverse=True):
        text = re.sub(re.escape(p), NATURAL_PERSON, text, flags=re.I)
    return text


def scan(text: str) -> list[str]:
    """Personal-information patterns left in a rendered pack (empty list = clean)."""
    hits = [f"email:{m}" for m in EMAIL.findall(text)]
    hits += [f"phone:{m}" for m in PHONE.findall(text) if re.sub(r"\D", "", m) not in ALLOWED_PHONES]
    hits += [f"id-like:{m}" for m in IDNUM.findall(text)]
    hits += ["person key" for _ in re.finditer(r"person_key", text)]
    return hits


def render(f: dict) -> str:
    d = _det(f["detector_id"])
    name, plain = GLOSSARY.get(d, (f["detector_id"], "see the detector description in config/detectors.yaml."))
    persons = _persons(f)
    supplier = None
    if f.get("names_supplier"):
        m = f["matched"].get("match") or {}
        supplier = m.get("award_supplier") or str(f.get("subject_name") or "").strip("()") or None
    now = datetime.now(timezone.utc).astimezone(SAST).strftime("%Y-%m-%d %H:%M SAST")
    L = [f"# Case referral pack: {f['flag_id']}", "", NOTICE, "",
         "| Field | Value |", "|---|---|",
         f"| Case ID | {f['flag_id']} (detector {f['detector_id']} v{f.get('detector_version', '')}) |",
         f"| Review status | {f.get('review_status') or f.get('status') or ''} (hidden lead, not published) |",
         f"| Severity / score | {f.get('severity')} / {f.get('score')} |",
         f"| Buyer entity | {f.get('body_name') or ''} ({f.get('gov_body_id')}) |",
         f"| Supplier (as in the official record) | {(NATURAL_PERSON if supplier in persons else supplier) if supplier else 'not applicable (no supplier named)'} |",
         f"| Period / dates | {f.get('period_label')} |",
         f"| Evidence hash | `{f.get('evidence_hash')}` |",
         f"| Generated | {now} |", "",
         f"## What the check found: {name}", "", f"In plain words: {plain}", "",
         f"Detector explanation: {f['explanation']}", "",
         "## Comparison baseline", "", BASELINE.get(d, "See config/detectors.yaml."), ""]
    if f["matched"].get("match"):
        m = f["matched"]["match"]
        L += [f"Match basis: {m.get('basis')} (confidence {m.get('confidence')}).", ""]
    L += ["## Evidence (with source lineage)", ""]
    for i, e in enumerate(f["evidence"], 1):
        parts = [f"{k}: {v}" for k, v in e.items() if not DROP_COL.search(k)]
        L.append(f"{i}. " + "; ".join(parts))
    L.append("")
    for title, rows in f["matched"]["tables"]:
        if not rows:
            continue
        cols = [c for c in rows[0] if not DROP_COL.search(c)]
        L += [f"### {title}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        L += ["| " + " | ".join(_cell(c, r.get(c), persons) for c in cols) + " |" for r in rows]
        L.append("")
    links: dict[str, str] = {}
    for e in f["evidence"]:
        if e.get("ocid"):
            links[OCDS_RELEASE.format(ocid=e["ocid"])] = f"eTenders OCDS release {e['ocid']}"
        if e.get("url"):
            links.setdefault(e["url"], e.get("label") or "source")
    for _, rows in f["matched"]["tables"]:
        for r in rows:
            if r.get("ocid"):
                links[OCDS_RELEASE.format(ocid=r["ocid"])] = f"eTenders OCDS release {r['ocid']}"
            for c in ("doc_url", "source_url", "report_url"):
                if r.get(c):
                    links.setdefault(r[c], c.replace("_", " "))
    raws = f.get("raw_files") or {}
    L += ["## Official source records", ""] + [f"- {lab}: {u}" for u, lab in links.items()] + [""]
    if raws:
        L += ["Raw files as fetched (lineage):", ""]
        L += [f"- {r.get('source_id')} `{r.get('name')}` sha256 `{r.get('sha256')}` fetched {r.get('fetched_at_utc')} from {r.get('url')}"
              for r in raws.values()]
        L.append("")
    L += ["## Possible innocent explanations", ""] + [f"- {a}" for a in ALTERNATIVES.get(d, ["Data error at source."])]
    L += ["", "## Checklist for the independent checker", ""] + [f"- [ ] {c}" for c in CHECKLIST]
    L += ["", "## How to refer (only after both independent checks hold up)", "",
          f"- Corruption Watch, official reporting page: {CW_REPORT}",
          f"- National Anti-Corruption Hotline (Public Service Commission): {HOTLINE} (toll free); other official hotlines (SIU, AGSA, Public Protector): {GOV_HOTLINES}",
          "- Refer conduct and the official records only. Do not add personal information about anyone.", "",
          "---", "", NOTICE, ""]
    text = _scrub("\n".join(L), persons)
    hits = scan(text)
    if hits:
        raise UnsafePack(f"personal-information patterns in the pack ({len(hits)}); not written")
    return text


def export(svc, flag_id: str, out_dir: Path, pdf: bool = False) -> dict:
    f = svc.get_flag(flag_id)
    if not f:
        raise LookupError("no such flag in the current build")
    text = render(f)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"case-{flag_id}.md"
    md.write_text(text, encoding="utf-8")
    res = {"flag_id": flag_id, "markdown": str(md), "bytes": len(text.encode()), "popia_scan": "clean"}
    if pdf:
        if shutil.which("pandoc"):
            p = md.with_suffix(".pdf")
            subprocess.run(["pandoc", str(md), "-o", str(p)], check=True)
            res["pdf"] = str(p)
        else:
            res["pdf"] = "skipped: pandoc not installed"
    return res
