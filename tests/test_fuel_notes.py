"""CSI-051 / CHG-2026-030: the fuel card shows fuel.about and the known errors it points to (selection rule, static checks)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/public-dashboard/index.html"
PUB = ROOT / "public-data/v1"


def _tools_view():
    html = APP.read_text()
    return html[html.index("async function vTools("):html.index("async function vCompare(")]


def _rule_js():
    """The id-selection lines of vTools, verbatim (from `const fuelAbout` to `const fuelKnown ...;`)."""
    v = _tools_view()
    i = v.index("const fuelAbout")
    return v[i:v.index("\n", v.index("const fuelKnown", i))]


def rule_py(about, known_gaps, known_errors):
    ids = lambda t: set(re.findall(r"KE-\d+", str(t)))
    named = set().union(*(ids(t) for t in about)) if about else set()
    seen = set(named)
    for g in known_gaps:
        if g["id"] in named:
            seen |= ids(g["text"])
    return [k["id"] for k in known_errors if k["id"] in seen]


def rule_node(fuel, man):
    js = "const fuel=%s, man=%s;\n%s\nconsole.log(JSON.stringify(fuelKnown.map(k=>k.id)));" % (json.dumps(fuel), json.dumps(man), _rule_js())
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


CASES = [
    # about names KE-012; its gap names KE-014 and KE-015; KE-001 is unrelated; KE-099 is named by a gap of an unrelated id
    ({"about": ["x (KE-012).", "y"]},
     {"known_gaps": [{"id": "KE-012", "text": "see KE-014 and KE-015"}, {"id": "KE-001", "text": "KE-099"}],
      "known_errors": [{"id": f"KE-{n:03d}", "symptom": "s"} for n in (1, 12, 14, 15, 99)]}, ["KE-012", "KE-014", "KE-015"]),
    # one hop only: a gap of KE-014 is not followed
    ({"about": ["(KE-012)"]},
     {"known_gaps": [{"id": "KE-012", "text": "KE-014"}, {"id": "KE-014", "text": "KE-015"}],
      "known_errors": [{"id": f"KE-{n:03d}", "symptom": "s"} for n in (12, 14, 15)]}, ["KE-012", "KE-014"]),
    # ...whatever the order of the gaps
    ({"about": ["(KE-012)"]},
     {"known_gaps": [{"id": "KE-014", "text": "KE-015"}, {"id": "KE-012", "text": "KE-014"}],
      "known_errors": [{"id": f"KE-{n:03d}", "symptom": "s"} for n in (12, 14, 15)]}, ["KE-012", "KE-014"]),
    # an id named but not in known_errors is not invented
    ({"about": ["(KE-012)"]}, {"known_gaps": [], "known_errors": [{"id": "KE-001", "symptom": "s"}]}, []),
    # about missing, about as a string, known_gaps missing
    ({}, {"known_errors": [{"id": "KE-012", "symptom": "s"}]}, []),
    ({"about": "text (KE-012)"}, {"known_errors": [{"id": "KE-012", "symptom": "s"}]}, ["KE-012"]),
]


@pytest.mark.parametrize("fuel,man,want", CASES)
def test_rule_python_reference(fuel, man, want):
    assert rule_py(fuel.get("about") or [] if not isinstance(fuel.get("about"), str) else [fuel["about"]],
                   man.get("known_gaps") or [], man.get("known_errors") or []) == want


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("fuel,man,want", CASES)
def test_rule_in_the_page_matches_the_reference(fuel, man, want):
    assert rule_node(fuel, man) == want


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_rule_on_published_data_shows_ke012_and_only_known_errors():
    pr = json.loads((PUB / "prices.json").read_text())
    man = json.loads((PUB / "manifest.json").read_text())
    got = rule_node(pr["fuel"], man)
    published = {k["id"] for k in man["known_errors"]}
    assert "KE-012" in got and set(got) <= published


def test_block_is_static_text_only_and_has_no_hardcoded_ids():
    v = _tools_view()
    assert 'id: "fuel-known"' in v and 'id: "fuel-about"' in v and "How to read these prices" in v
    assert "innerHTML" not in v and 'html:' not in v
    block = v[v.index("const fuelAbout"):]
    assert not re.findall(r'"KE-\d+"', block.replace("(KE-\\d+", ""))        # ids come from the data, never typed in
    assert "load(" not in _rule_js()                                         # no new request


def test_fuel_details_order_keeps_the_csv_check_working():
    """dashboard_check clicks the first `details summary` on #/tools; that must stay the 'All loaded official prices' one."""
    v = _tools_view()
    assert v.index("All loaded official prices") < v.index("How to read these prices")
    assert v.count("el(\"details\"") == 2
