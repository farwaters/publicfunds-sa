"""CHG-2026-047: the home page uses the en-ZA decimal comma (12,5%) for every decimal. CSV and JSON data keep the decimal point."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from thusa.coverage_ceiling import core_gap_lines, headline_context_lines

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "apps/public-dashboard/index.html").read_text(encoding="utf-8")
DATA = ROOT / "public-data/v1"


def _vhome() -> str:
    start = PAGE.index("async function vHome()")
    return PAGE[start:PAGE.index("\nasync function ", start + 10)]


def _dec1_src() -> str:
    return re.search(r"^function dec1\(x\) \{.*\}$", PAGE, re.M).group(0)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_dec1_gives_a_decimal_comma():
    js = _dec1_src() + "\nconsole.log(JSON.stringify([12.5, 75.7, 73, 64.94, 0.05, 100].map(dec1)));"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == ["12,5", "75,7", "73,0", "64,9", "0,1", "100,0"]


def test_home_headline_uses_dec1_not_the_raw_number():
    body = _vhome()
    assert 'dec1(c.complete_pct) + "%"' in body
    assert 'complete_pct + "%"' not in body


def test_home_code_has_no_other_point_decimal_paths():
    """vHome formats numbers only with dec1, en-ZA toLocaleString, or integers. A bare toFixed or a raw float would show a point."""
    body = _vhome()
    assert ".toFixed(" not in body
    for m in re.finditer(r"toLocaleString\(([^)]*)\)", body):
        assert m.group(1).startswith('"en-ZA"'), m.group(0)


def test_home_note_lines_use_a_decimal_comma():
    cov = json.loads((DATA / "coverage.json").read_text(encoding="utf-8"))
    for line in core_gap_lines(cov) + headline_context_lines(cov):
        assert not re.search(r"\d\.\d", line), line


def test_data_files_keep_the_decimal_point():
    """The change is page formatting only: JSON keeps numbers, so the headline is still 75.7 there."""
    man = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(man["coverage"]["complete_pct"], float)
