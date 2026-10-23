"""CHG-2026-015: municipality report card shows only published data (no hidden leads, no AGSA annexure data, no score)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-dashboard" / "index.html"


def card_src() -> str:
    html = APP.read_text()
    a = html.index("/* ---------------------------------------------------------------- report card")
    return html[a:html.index("/* ---------------------------------------------------------------- router */")]


def test_route_and_link():
    html = APP.read_text()
    assert "#\\/m\\/(.+)\\/card$/" in html
    assert html.index("\\/card$/") < html.index("[/^#\\/m\\/(.+)$/")   # card route matched before the page route
    assert '"/card"' in html


def test_card_never_reads_hidden_or_unpublished_data():
    src = card_src()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("/*"))
    assert "hidden_leads" not in code and "names_a_supplier" not in code
    assert "agsa_annexures" not in code and "load(\"manifest.json\")" not in code
    assert re.search(r"score|grade", code, re.I) is None or "no overall grade or score" in code
    never = yaml.safe_load((ROOT / "config" / "publication.yaml").read_text())["flags"]["never_publish"]
    shown = json.loads(re.search(r"CARD_NEVER_PUBLISH = (\[[^\]]*\])", src).group(1))
    assert sorted(shown) == sorted(never)
    assert "unknown, never zero" in src and "#/glossary" in src
    assert not re.search(r"farwaters|github", src, re.I)


def test_agsa_annexures_still_unpublished():
    """The card says AGSA annexure figures are not yet published; that must stay true of the data."""
    chk = (ROOT / "docs" / "legal" / "agsa-wording-review-checklist.md").read_text()
    pub = ROOT / "public-data" / "v1"
    if "Nothing from the AGSA annexures is published yet" in chk:
        for p in ("municipalities.json", "flags.json", "coverage.json"):
            assert "agsa_annexures" not in (pub / p).read_text()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_card_logic_filters_flags_and_counts_coverage():
    src = card_src()
    js = src[src.index("const CARD_NEVER"):src.index("async function vCard")] + """
const f = {confirmed: [{gov_body_id: "MUN:X", detector_id: "D1_overspend_vs_budget"}, {gov_body_id: "MUN:X", detector_id: "D16_repeat_awards"},
  {gov_body_id: "MUN:Y", detector_id: "D1_overspend_vs_budget"}], hidden_leads: {total: 99}};
const c = cardCompleteness({c: {budget: "PPpm-", uifw: "PP?--"}});
console.log(JSON.stringify({flags: cardFlags(f, "MUN:X").length, n: c.n, total: c.total, gaps: c.gaps.length, none: cardCompleteness(undefined).total}));
"""
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out == {"flags": 1, "n": {"P": 4, "p": 1, "m": 1}, "total": 6, "gaps": 2, "none": 0}
