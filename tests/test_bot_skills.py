"""Template skills: valid frontmatter, generic (no personal names), small."""
from pathlib import Path

import pytest

SKILLS = sorted((Path(__file__).parents[1] / "docs" / "bot" / "skills").glob("*/SKILL.md"))


def test_expected_skills_present():
    assert {p.parent.name for p in SKILLS} == {
        "getting-started", "publicfunds-setup", "publicfunds-refresh", "publicfunds-review", "publicfunds-itil"}


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter_and_generic(path):
    text = path.read_text()
    assert text.startswith("---\n")
    head = text.split("---\n")[1]
    fields = dict(line.split(": ", 1) for line in head.strip().splitlines())
    assert fields["name"] == path.parent.name
    assert len(fields["description"]) > 40
    assert "lootty" not in text.lower() and "/home/box" not in text
    assert len(text) < 4000
