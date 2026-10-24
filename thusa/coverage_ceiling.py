"""CHG-2026-033: reference model for the 'By data type' table on #/unknowns. Pure functions of the published
public-data/v1/coverage.json and municipalities.json; no pandas, no file I/O. The page code (ceilingModel in
apps/public-dashboard/index.html, between the ceiling:begin and ceiling:end markers) must give exactly the same output;
tests/test_unknowns_by_type_constant.py runs both on real and mutated data and compares them, and
scripts/dashboard_check.py uses the same functions for the expected texts, so no check imports from a test module.

DEFINITION (descriptive, no cause): a window year is EMPTY for a data type when no municipality has a fully present ('P') cell
for it in coverage.json. The most a province can reach with today's data is (applicable cells outside empty years) / (all applicable cells).
Nothing here says WHY a year is empty (source lag, a failed load, never published): that is not in coverage.json.
"""
from __future__ import annotations

import math
import re

# Types for which an empty year is assessed. Tender awards are left out on the reviewers' advice (CHG-2026-033, decision 3): the one
# empty year the rule found for them (2020/21, 13 partly loaded awards) made a ceiling of ~100% sit next to a share of ~7%.
# To restore it, add "procurement" here and in the CEILING_TYPES constant of the page block (the parity test fails until both agree).
CEILING_TYPES = ("budget", "actual_audited", "uifw", "audit_opinion")
LABEL = {"budget": "budget", "actual_audited": "audited actuals", "uifw": "irregular & wasteful spending",
         "audit_opinion": "audit opinion", "procurement": "tender awards"}
# CHG-2026-034 (option A): the four types the headline counts ("complete core data"). Tender awards are outside the headline.
CORE = ("budget", "actual_audited", "uifw", "audit_opinion")
FORBIDDEN_PUBLIC_WORDS = ("KE-", "cube", "MFMA", "eTenders", "Treasury", "AGSA", "uifwexp", "components_missing", "not_in_loaded", "publish")

# Static strings the by-type view shows (the page copy is in the ceiling:begin..end block; parity-tested, jargon-tested).
HEADERS = {"budget": "Budget data available (original + adjusted)", "actual_audited": "Audited actuals data available",
           "uifw": "Irregular & wasteful spending data available", "audit_opinion": "Audit opinion available",
           "procurement": "Tender award data available (with a value)"}
CAPTION = "Share of municipality-years for which the data is available, per province and data type. This is not how much was spent or lost."
LEGEND = "Under each percentage, 'x of y' counts municipality-years (one municipality in one financial year), not municipalities."
SCROLL_HINT = "Swipe or scroll sideways to see all the data types \u2192"      # shown only while the table is wider than its box
HOW_TO_READ = ("How to read this: a municipality-year counts as available when all the data for that data type and year is in the data "
               "PublicFunds loads, as partly available when only some of it is, and as missing when none was found. A gap is not evidence of "
               "wrongdoing: often the audit is not yet due, or the data is not in the data PublicFunds loads. Tender awards before 2021/22 are "
               "not counted for most municipalities; most counted municipality-years have no award records loaded, and some awards have no value.")
TENDER_CAPTION = ("Tender awards: years before 2021/22 are not counted for most municipalities, so N is about four years per municipality, "
                  "not six. Most counted municipality-years have no award records loaded, and some awards have no value.")


def jargon(text):
    """Internal ids and words that must never reach a public string: the list above (case-insensitive) and any KE-nnn id."""
    low = text.lower()
    return [w for w in FORBIDDEN_PUBLIC_WORDS if (w in text if w == "KE-" else w.lower() in low)] + (["KE-nnn"] if re.search(r"KE-\d", text) else [])


def pct(a, b):
    return math.floor(1000 * a / b + 0.5) / 10 if b else None      # same rounding as the page's Math.round


def window(cov):
    h = cov["headline"]
    return [k for k, y in enumerate(cov["years"]) if h["fye_min"] <= y <= h["fye_max"]]


def empty_years(cov, dt):
    """Window year indexes in which no municipality has a fully present cell for `dt` (only for CEILING_TYPES; [] for the others)."""
    if dt not in CEILING_TYPES:
        return []
    return [k for k in window(cov) if not any(e["c"][dt][k] == "P" for e in cov["entities"])]


def missing_budget_part(cov, mun, k):
    """'adjusted budget' / 'original budget' when one part is published for some municipalities and the other for none; else None."""
    fye = str(cov["years"][k])
    ys = [m["years"].get(fye) or {} for m in mun["municipalities"]]
    nb, na = sum(1 for y in ys if y.get("budget")), sum(1 for y in ys if y.get("adjusted"))
    if nb and not na:
        return "adjusted budget"
    if na and not nb:
        return "original budget"
    return None


def province_order(cov, mun):
    """Province codes in the order the page lists them: lowest overall share (all types, window) first; ties keep first-seen order
    in coverage.json (JS sort is stable). Same counting as by_province, '-' and '?' skipped."""
    prov = {m["id"]: m["province"] for m in mun["municipalities"]}
    ks = window(cov)
    tot: dict = {}
    for e in cov["entities"]:
        p = prov.get(e["id"])
        if p is None:
            continue
        t = tot.setdefault(p, [0, 0])
        for dt in cov["data_types"]:
            for k in ks:
                st = e["c"][dt][k]
                if st not in ("-", "?"):
                    t[1] += 1
                    t[0] += st == "P"
    return sorted(tot, key=lambda p: pct(*tot[p]) if tot[p][1] else 101)


def by_province(cov, mun):
    """{province: {data type: {P, n, n_empty}}} over the window, skipping '-' and '?' cells (same rule as the page)."""
    prov = {m["id"]: m["province"] for m in mun["municipalities"]}
    ks = window(cov)
    emp = {dt: set(empty_years(cov, dt)) for dt in cov["data_types"]}
    out: dict = {}
    for e in cov["entities"]:
        p = prov.get(e["id"])
        if p is None:
            continue
        for dt in cov["data_types"]:
            c = out.setdefault(p, {}).setdefault(dt, {"P": 0, "n": 0, "n_empty": 0})
            for k in ks:
                st = e["c"][dt][k]
                if st in ("-", "?"):
                    continue
                c["n"] += 1
                c["P"] += st == "P"
                c["n_empty"] += k in emp[dt]
    return out


def ceiling(c):
    return pct(c["n"] - c["n_empty"], c["n"])


def dec(x):
    """One decimal with a decimal comma, as the page's num() shows percentages (83,3%)."""
    return f"{x:.1f}".replace(".", ",")


def range_text(vals):
    a, b = dec(min(vals)), dec(max(vals))
    return a + "%" if a == b else f"{a}–{b}% depending on the province"


def _join(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def model(cov, mun):
    """The complete expected page content for the table: per type {empty, ceiling, note}, the banner lines and the n-of-N cells."""
    bp = by_province(cov, mun)
    out: dict = {"cells": {p: {dt: {"P": c["P"], "n": c["n"]} for dt, c in sorted(d.items())} for p, d in sorted(bp.items())}}
    banner: dict = {}
    for dt in cov["data_types"]:
        emp = empty_years(cov, dt)
        ceil = {p: ceiling(bp[p][dt]) for p in sorted(bp) if bp[p][dt]["n"]} if dt in CEILING_TYPES else {}
        parts = []
        for k in emp:
            fy = cov["fy_labels"][k]
            part = missing_budget_part(cov, mun, k) if dt == "budget" else None
            parts.append(f"no municipality has the {part} for {fy}" if part else f"no municipality has complete data for {fy}")
            banner.setdefault(fy, []).append(("the " + part) if part else LABEL[dt])
        out[dt] = {"empty": [cov["fy_labels"][k] for k in emp], "ceiling": ceil,
                   "note": (f"At most {range_text(list(ceil.values()))} with the data PublicFunds loads today "
                            f"({'; '.join(parts)}).") if emp else None}
    hp = {p: {dt: (f"(at most {dec(ceil_p[dt])}% with the data loaded today)" if out[dt]["empty"] and dt in ceil_p else None) for dt in cov["data_types"]}
          for p, ceil_p in ((p, {dt: out[dt]["ceiling"][p] for dt in cov["data_types"] if p in out[dt]["ceiling"]}) for p in sorted(bp))}
    out["_text"] = {"headers": dict(HEADERS), "caption": CAPTION, "legend": LEGEND, "scroll_hint": SCROLL_HINT, "how_to_read": HOW_TO_READ, "tender_caption": TENDER_CAPTION, "in_cell": hp}
    out["_banner"] = [f"{fy}: no municipality has complete data for {_join(ts)} in the data PublicFunds loads today."
                      for fy, ts in banner.items()]
    return out


def core_gap_lines(cov):
    """CHG-2026-034 (option A): one line per headline-window year in which no municipality has complete data for at least one of
    the four core types (CORE), for the home headline, the coverage page and the report card. Descriptive, no cause. The count is the
    headline's own `by_year` entry (complete of applicable); when that entry is absent the clause is left out. The headline itself,
    its window and its computation are not touched: the year stays counted as a gap."""
    by_year = {y["fye"]: y for y in cov["headline"].get("by_year", [])}
    emp = {dt: set(empty_years(cov, dt)) for dt in CORE if dt in cov["data_types"]}
    lines = []
    for k in window(cov):
        types = [LABEL[dt] for dt in emp if k in emp[dt]]
        if not types:
            continue
        y = by_year.get(cov["years"][k])
        so = f", so {y['complete']} of {y['applicable']} municipalities have complete core data for that year" if y else ""
        lines.append(f"{cov['fy_labels'][k]}: no municipality has complete data for {_join(types)} in the data PublicFunds loads today"
                     f"{so}. The headline counts the year as a gap.")
    return lines


def _tenths(c, a):
    """c / a as a percentage with one decimal, rounded half up with integer arithmetic (same in Python and the page)."""
    return f"{(2000 * c + a) // (2 * a) / 10:.1f}"


def _span(labels):
    return labels[0] if len(labels) == 1 else f"{labels[0]} to {labels[-1]}"


def headline_context_lines(cov):
    """Beside the home headline (CHG-2026-034, option A), computed from coverage.json only; the headline, its window and its computation are
    not touched. Only when a window year is a gap year (core_gap_lines): the same measure over the window's other years, and, while the
    next year is not yet counted (all_core_due false), a labelled prediction for the day it enters. It stops by itself when the data changes."""
    h = cov["headline"]
    by_year = {y["fye"]: y for y in h.get("by_year", [])}
    gap = {k for dt in CORE if dt in cov["data_types"] for k in empty_years(cov, dt)}
    win = window(cov)
    gaps = [k for k in win if k in gap]
    rest = [k for k in win if k not in gap]
    if not gaps or not rest or any(cov["years"][k] not in by_year for k in win):
        return []
    labels = lambda ks: [cov["fy_labels"][k] for k in ks]
    c = sum(by_year[cov["years"][k]]["complete"] for k in rest)
    a = sum(by_year[cov["years"][k]]["applicable"] for k in rest)
    alone = _span(labels(rest)) if rest == list(range(rest[0], rest[-1] + 1)) else _join(labels(rest))
    lines = [f"Includes {_join(labels(gaps))}, for which no municipality has complete data in what PublicFunds has loaded. "
             f"{alone} alone: {_tenths(c, a)}% ({c} of {a})."]
    nxt = by_year.get(h["fye_max"] + 1)
    if nxt and nxt.get("all_core_due") is False:
        hc, ha = h["complete"], h["applicable"] + nxt["applicable"]
        lines.append(f"Prediction, not a result: from the first data update on or after 1 December {nxt['fye']}, the year {nxt['fy']} counts in "
                     f"the headline. If it then looks like {cov['fy_labels'][gaps[-1]]} does today (no municipality with complete data), "
                     f"the headline would fall to about {_tenths(hc, ha)}% ({hc} of {ha}).")
    return lines
