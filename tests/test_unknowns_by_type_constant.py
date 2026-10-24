"""CHG-2026-033: checks for the 'By data type' table on #/unknowns.

Replays the page rule on the committed public-data/v1/coverage.json and municipalities.json using the reference model
thusa/coverage_ceiling.py (window fye_min..fye_max from the headline, cells '-' and '?' skipped), and checks:

1. PARITY. The page code (the ceiling:begin..ceiling:end block, extracted from the page file and run in node) gives exactly the
   reference output (per-province P and n, the empty years, the ceilings, the notes, the banner) on the real data and on mutated
   data. This is the test that can fail when the page code is wrong; the reference is not derived from itself.
2. PIN OF EMPTY YEARS. The window years in which no municipality has a fully present cell for a type are pinned per type
   (EXPECTED_EMPTY). Red = a year became empty or stopped being empty: review it (new source year loaded, a partial load, or a
   failed load) before editing the pin. The definition is descriptive and gives no cause, so a failed load that empties a year is
   shown truthfully ("no municipality has complete data for 2022/23") and is caught here, not explained away on the page.
3. UNEXPLAINED CONSTANT. A data-type column with the same share for every province must be listed in ALLOWED_CONSTANT, pinned to
   its window and exact per-municipality state string. Going red when FYE 2025 arrives is INTENDED.
4. PUBLIC TEXT. The generated notes and banner AND the static strings (headers, caption, how-to-read card, tender caption) AND the
   in-cell "(at most x% with the data loaded today)" text carry no internal ids, jargon, KE-nnn id or the word "published".

node: the parity tests FAIL if node is missing. Opt-out for a machine without node: PF_SKIP_NODE_PARITY=1 (the tests are then reported
as skipped, with that reason, so the missing check stays visible in the pytest summary).
"""
import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from thusa.coverage_ceiling import (HEADERS, by_province, ceiling, empty_years, jargon, model, pct, window)

ROOT = Path(__file__).resolve().parents[1]
COV = json.loads((ROOT / "public-data/v1/coverage.json").read_text())
MUN = json.loads((ROOT / "public-data/v1/municipalities.json").read_text())
PAGE_JS = ROOT / "apps/public-dashboard/index.html"      # the page file; the block between the ceiling markers is run in node

WINDOW = (2020, 2025)                            # headline fye_min, fye_max today; red on 1 Dec 2026 when FYE 2026 falls due: intended
# Pinned: FYE of the window years with no fully present cell for the type.
EXPECTED_EMPTY = {"budget": [2025], "actual_audited": [], "uifw": [2025], "audit_opinion": [2025], "procurement": []}   # procurement: not assessed (CEILING_TYPES)

ALLOWED_CONSTANT = {
    "uifw": {
        "window": WINDOW,
        "pattern": "PPPPPm",             # the ONLY per-municipality state string in the window
        "source": "uifwexp",             # must be read by thusa/connectors/muni_api.py
        "missing_fye": [2025],           # must equal the FYEs where `pattern` has 'm'
        "known_error": "KE-006",         # must exist in itil/knowledge/known-errors.md
        "reason": ("Treasury Municipal Money cube uifwexp has FYE 2012-2024 only (checked by a live read-only GET on 2026-10-24): every "
                   "municipality has all 3 UIFW items for FYE 2020-2024 and none for FYE 2025 (5 of 6 years); FYE 2025 is not loaded"),
    },
}


def pin_violations(cov, expected=None):
    exp = EXPECTED_EMPTY if expected is None else expected
    got = {dt: [cov["years"][k] for k in empty_years(cov, dt)] for dt in cov["data_types"]}
    return {dt: {"pinned": exp.get(dt), "now": got[dt]} for dt in cov["data_types"] if got[dt] != exp.get(dt)}


BASELINE_OK = (COV["headline"]["fye_min"], COV["headline"]["fye_max"]) == WINDOW and not pin_violations(COV)
needs_baseline = pytest.mark.skipif(not BASELINE_OK, reason="committed data already differs from the pins: test_empty_years_are_pinned_per_type reports it")


# ------------------------------------------------------------------ mutations (also used by the parity tests)
def _set(cov, dt, fye, state, reason=None, only=None):
    c = copy.deepcopy(cov)
    k = c["years"].index(fye)
    for i, e in enumerate(c["entities"]):
        if e["c"][dt][k] in "-?" or (only is not None and i not in only):
            continue
        e["c"][dt] = e["c"][dt][:k] + state + e["c"][dt][k + 1:]
        e["r"][dt] = e["r"][dt][:k] + str(c["reasons"].index(reason) + 1 if reason else 0) + e["r"][dt][k + 1:]
    return c


def mutate_validator_case(cov):
    """Opinion and budget FYE 2023 (2022/23) lose every row: all cells 'm' / not_in_loaded_sources."""
    return _set(_set(cov, "audit_opinion", 2023, "m", "not_in_loaded_sources"), "budget", 2023, "m", "not_in_loaded_sources")


def mutate_partial_arrival(cov, n=200):
    """UIFW FYE 2025 arrives for only n municipalities."""
    idx = [i for i, e in enumerate(cov["entities"]) if e["c"]["uifw"][cov["years"].index(2025)] == "m"][:n]
    return _set(cov, "uifw", 2025, "P", None, only=set(idx))


def mutate_year_before_window(cov):
    """A year BEFORE the headline window (FYE 2019, every cell missing) is added in front. The committed data starts exactly at fye_min, so
    without this case dropping the lower bound of the window would go unnoticed: the year must not count anywhere."""
    c = copy.deepcopy(cov)
    c["years"].insert(0, c["years"][0] - 1)
    c["fy_labels"].insert(0, f"{c['years'][0] - 1}/{str(c['years'][0])[2:]}")
    for e in c["entities"]:
        for dt in c["data_types"]:
            e["c"][dt] = "m" + e["c"][dt]
            e["r"][dt] = "0" + e["r"][dt]
    return c


def mutate_year_arrives(cov):
    return _set(cov, "uifw", 2025, "P")


def mutate_tender_year_emptied(cov):
    """Tender awards FYE 2024 lose every row. Tender awards are not assessed (CEILING_TYPES), so no note, banner line or ceiling may appear."""
    return _set(cov, "procurement", 2024, "m", "not_in_loaded_sources")


def mutate_unknown_states_and_unmapped(cov):
    """Cells in state '?' (not applicable to count) in a window year, and an entity with no province (must be ignored)."""
    c = copy.deepcopy(cov)
    k = c["years"].index(2022)
    for e in c["entities"][:40]:
        for dt in ("budget", "uifw"):
            s = e["c"][dt]
            e["c"][dt] = s[:k] + "?" + s[k + 1:]
    c["entities"].append({"id": "MUN:NOPROVINCE", "c": {dt: "P" * len(c["years"]) for dt in c["data_types"]}, "r": {}})
    return c


def mutate_ceilings_differ_by_province(cov):
    """Not applicable ('?') cells in 2022 for some municipalities of ONE province: its ceiling differs from the others, so the note must give a range."""
    c = copy.deepcopy(cov)
    k = c["years"].index(2022)
    ec = {m["id"] for m in MUN["municipalities"] if m["province"] == "EC"}
    for e in c["entities"]:
        if e["id"] in ec:
            for dt in ("budget", "uifw"):
                x = e["c"][dt]
                e["c"][dt] = x[:k] + "?" + x[k + 1:]
    return c


# ------------------------------------------------------------------ 1. parity page code vs reference
def _page_model(cov, mun):
    if not shutil.which("node"):
        if os.environ.get("PF_SKIP_NODE_PARITY") == "1":
            pytest.skip("PF_SKIP_NODE_PARITY=1 and node is not installed: the page code was NOT checked")
        pytest.fail("node is not installed, so the page code was NOT checked against the reference model. Install node, or set "
                    "PF_SKIP_NODE_PARITY=1 to skip this check on purpose.")
    src = PAGE_JS.read_text()
    m = re.search(r"/\* ceiling:begin \*/(.*?)/\* ceiling:end \*/", src, re.S)
    assert m and src.count("/* ceiling:begin */") == 1 and src.count("/* ceiling:end */") == 1, f"{PAGE_JS}: ceiling:begin/end markers not found exactly once"
    js = m.group(1) + "\nconst d = JSON.parse(require('fs').readFileSync(0, 'utf8')); console.log(JSON.stringify(ceilingModel(d.cov, d.mun)));"
    r = subprocess.run(["node", "-e", js], input=json.dumps({"cov": cov, "mun": mun}), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@pytest.mark.parametrize("name,mutate", [("real data", lambda c: c), ("validator case: opinion+budget 2022/23 emptied", mutate_validator_case),
                                         ("partial arrival: 200 of 257 UIFW 2024/25", mutate_partial_arrival),
                                         ("UIFW 2024/25 arrives for all", mutate_year_arrives),
                                         ("a year before the window (lower bound of the window)", mutate_year_before_window),
                                         ("'?' cells and an entity with no province", mutate_unknown_states_and_unmapped),
                                         ("tender awards FYE 2024 emptied (not assessed)", mutate_tender_year_emptied),
                                         ("ceilings differ by province (range in the note)", mutate_ceilings_differ_by_province)])
def test_page_code_matches_reference(name, mutate):
    cov = mutate(COV)
    assert _page_model(cov, MUN) == model(cov, MUN), name


@needs_baseline
def test_reference_behaviour_on_mutations():
    base = model(COV, MUN)
    assert base["uifw"]["empty"] == ["2024/25"] and base["uifw"]["ceiling"]["EC"] == 83.3
    assert base["uifw"]["note"].startswith("At most 83,3% with the data PublicFunds loads today (")   # decimal comma, as the page shows
    assert base["_text"]["in_cell"]["EC"]["uifw"] == "(at most 83,3% with the data loaded today)"
    assert base["procurement"] == {"empty": [], "ceiling": {}, "note": None} and not any(base["_text"]["in_cell"][p]["procurement"] for p in base["_text"]["in_cell"])
    assert not any("tender" in line for line in base["_banner"])       # decision 3: no tender note, marker, banner line or ceiling
    v = model(mutate_validator_case(COV), MUN)
    assert v["audit_opinion"]["empty"] == ["2022/23", "2024/25"] and v["budget"]["empty"] == ["2022/23", "2024/25"]
    assert max(v["audit_opinion"]["ceiling"].values()) == 66.7            # descriptive: the page shows the real gap, with no cause
    assert "no municipality has complete data for 2022/23" in v["audit_opinion"]["note"]
    t = model(mutate_tender_year_emptied(COV), MUN)       # a tender year with no complete cell is NOT reported (not assessed)
    assert t["procurement"] == {"empty": [], "ceiling": {}, "note": None} and t["_banner"] == base["_banner"]
    p = model(mutate_partial_arrival(COV), MUN)
    assert p["uifw"]["empty"] == [] and p["uifw"]["note"] is None          # partly loaded year is not "empty": the pin below catches it
    assert model(mutate_year_arrives(COV), MUN)["uifw"]["note"] is None


# ------------------------------------------------------------------ 2. pin of empty years
def test_empty_years_are_pinned_per_type():
    h = COV["headline"]
    assert (h["fye_min"], h["fye_max"]) == WINDOW, (
        f"headline window moved to {(h['fye_min'], h['fye_max'])}: expected on 2026-12-01 (FYE 2026 falls due); review the pins, the "
        "tender caption ('four years, not six'), the notes and the RFC, then update WINDOW")
    bad = pin_violations(COV)
    assert not bad, (f"window years with no fully present cell changed: {bad}. A year arrived, was only partly loaded, or a load "
                     "failed: find out which before editing EXPECTED_EMPTY. NOTE: if even one municipality gains the year, the year is no "
                     "longer 'empty' (the note and banner disappear) while the other 256 municipalities still have nothing for it, so the "
                     "page needs a deliberate wording update, not just a pin edit")


@needs_baseline
@pytest.mark.parametrize("mutate", [mutate_validator_case, mutate_partial_arrival, mutate_year_arrives])
def test_pin_detects_the_mutations(mutate):
    assert pin_violations(mutate(COV)), "the pin did not notice the mutation"


def _mini(c, n=3):
    return {"years": [2024, 2025], "fy_labels": ["2023/24", "2024/25"], "headline": {"fye_min": 2024, "fye_max": 2025}, "data_types": ["uifw"],
            "reasons": [], "entities": [{"id": f"M{i}", "c": {"uifw": c}, "r": {"uifw": "00"}} for i in range(n)]}


def test_ceiling_is_computed_from_the_data_not_hard_coded():
    mun = {"municipalities": [{"id": f"M{i}", "province": "XX", "years": {}} for i in range(3)]}
    assert empty_years(_mini("Pm"), "uifw") == [1]
    assert empty_years(_mini("PP"), "uifw") == []
    c = by_province(_mini("Pm"), mun)["XX"]["uifw"]
    assert (c["P"], c["n"], ceiling(c)) == (3, 6, 50.0)
    assert model(_mini("PP"), mun)["uifw"]["note"] is None


# ------------------------------------------------------------------ 3. unexplained constant column
def _constant_types():
    bp = by_province(COV, MUN)
    return {dt for dt in COV["data_types"] if len({pct(bp[p][dt]["P"], bp[p][dt]["n"]) for p in bp}) == 1}


def test_no_unexplained_constant_column_across_provinces():
    unexplained = sorted(_constant_types() - set(ALLOWED_CONSTANT))
    assert not unexplained, f"column(s) {unexplained} show the same % for every province; explain in ALLOWED_CONSTANT or fix the measure"


def test_allowed_constant_entries_are_still_constant_and_justified():
    const = _constant_types()
    connector = (ROOT / "thusa/connectors/muni_api.py").read_text()
    known_errors = (ROOT / "itil/knowledge/known-errors.md").read_text()
    for dt, w in ALLOWED_CONSTANT.items():
        assert dt in const, f"{dt} is no longer constant: delete its ALLOWED_CONSTANT entry"
        assert w["source"] in connector, f"{dt}: source {w['source']!r} is not read by thusa/connectors/muni_api.py"
        assert re.search(rf"^\| {re.escape(w['known_error'])} \|", known_errors, re.M), (
            f"{dt}: no table row starting '| {w['known_error']} |' in itil/knowledge/known-errors.md (a mention in prose does not count)")
        assert w["source"] in w["reason"] and "Treasury" in w["reason"]
        for y in w["missing_fye"]:
            assert f"FYE {y}" in w["reason"], f"{dt}: reason must name FYE {y}"
        derived = [COV["years"][k] for k, ch in zip(window(COV), w["pattern"]) if ch == "m"]
        assert derived == w["missing_fye"], f"{dt}: missing_fye {w['missing_fye']} does not match pattern {w['pattern']} ({derived})"


def test_allowed_constant_is_pinned_to_window_and_exact_state_pattern():
    """INTENDED to go red when the source gains the missing year (pattern becomes PPPPPP): review pin, note wording, RFC."""
    h = COV["headline"]
    ks = window(COV)
    for dt, w in ALLOWED_CONSTANT.items():
        assert (h["fye_min"], h["fye_max"]) == w["window"], f"{dt}: window moved to {(h['fye_min'], h['fye_max'])}; review, do not just edit the pin"
        pats = {"".join(e["c"][dt][k] for k in ks) for e in COV["entities"]}
        pats = {p for p in pats if set(p) - set("-?")}
        assert pats == {w["pattern"]}, f"{dt}: state patterns are {sorted(pats)}, pinned {w['pattern']!r}: review the note, the RFC and the whitelist"


# ------------------------------------------------------------------ 4. public text
def _public_strings(m):
    """Every string the by-type view can show, as produced by the model (the page block is run in node by the parity test, which makes
    the page strings equal these): notes, banner, headers, caption, legend, how-to-read card, tender caption, in-cell '(at most x% ...)'."""
    t = m["_text"]
    return (m["_banner"] + [m[dt]["note"] for dt in COV["data_types"] if m[dt]["note"]] + list(t["headers"].values())
            + [t["caption"], t["legend"], t["how_to_read"], t["csv_note"], t["tender_caption"]] + [x for d in t["in_cell"].values() for x in d.values() if x])


@pytest.mark.parametrize("mutate", [lambda c: c, mutate_validator_case, mutate_partial_arrival])
def test_public_text_has_no_internal_jargon_or_published(mutate):
    texts = _public_strings(model(mutate(COV), MUN))
    assert len(texts) > 10 and any("at most" in t for t in texts) and any(t.startswith("How to read") for t in texts)
    for t in texts:
        assert not jargon(t), (jargon(t), t)


def test_the_jargon_check_itself_catches_the_words():
    for bad in ("see KE-006", "not published", "Treasury says", "the uifwexp cube", "eTenders", "Published by AGSA", "components_missing"):
        assert jargon(bad), bad
    assert not jargon("At most 83,3% with the data PublicFunds loads today (take-up of data)")
    assert set(HEADERS) == set(COV["data_types"])


def test_legend_gives_the_unit_of_x_of_y():
    from thusa.coverage_ceiling import LEGEND
    assert "municipality-years" in LEGEND and "not municipalities" in LEGEND and not jargon(LEGEND)


def test_how_to_read_does_not_contradict_the_lead_and_says_a_gap_is_not_wrongdoing():
    """The lead says the years shown are those whose audits are due, so the how-to-read card must not say the audit may not be due yet."""
    t = model(COV, MUN)["_text"]["how_to_read"]
    assert "A gap is not evidence of wrongdoing. It usually means the data is not in what PublicFunds has loaded." in t
    assert "not yet due" not in t and "not due yet" not in t
    page = PAGE_JS.read_text()
    assert "often the audit is not yet due" not in page and t in page


def test_csv_note_says_the_headers_changed():
    t = model(COV, MUN)["_text"]["csv_note"]
    assert "headers of the CSV download changed" in t and "irregular & wasteful spending" in t and "extra columns" in t
    assert t in PAGE_JS.read_text()


def test_the_caption_is_a_paragraph_above_the_scrolling_box_not_inside_it():
    """On a 390 px screen a <caption> inside the sideways-scrolling table is clipped; the page puts the caption in a <p> above the box."""
    page = PAGE_JS.read_text()
    assert 'captionAbove: "by-type-caption"' in page
    assert "opts.captionAbove ? null : el(" in page and 'id: opts.captionAbove}, caption)' in page


def test_a_year_before_the_window_changes_nothing():
    """The reference ignores a year before fye_min: same cells, notes and banner as without it. (The page block is held equal by the parity case.)"""
    assert model(mutate_year_before_window(COV), MUN) == model(COV, MUN)
    assert mutate_year_before_window(COV)["years"][0] == COV["years"][0] - 1
