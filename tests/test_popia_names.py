"""POPIA guard (CHG-2026-049): protected names must not appear in tracked files.

The names are stored only as sha256 hashes (tests/popia_names.sha256), so this
file does not list them. An optional gitignored file `.popia-names.local`
(one plain name per line) adds more names on the owner's computer.
public-data/ is source-agency data and is out of scope. Allowed two-word
public names (place or supplier) are in tests/popia_allow.sha256.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"[^\W_]+(?:👀[^\W_]+)?", re.UNICODE)
EXCLUDE = ("public-data/",)


def _h(s: str) -> str:
    return hashlib.sha256(s.lower().encode("utf-8")).hexdigest()


def _load(name: str) -> set[str]:
    out = set()
    for line in (ROOT / "tests" / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def _names() -> set[str]:
    names = _load("popia_names.sha256")
    local = ROOT / ".popia-names.local"
    if local.exists():
        for line in local.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                names.add(_h(line.strip()))
    return names


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [p for p in out.stdout.decode().split("\0") if p and not p.startswith(EXCLUDE)]


def find_hits(text: str, names: set[str], allow: set[str]) -> list[int]:
    """Return token offsets of protected names; skip allowed two-word names."""
    toks = [m.group(0) for m in TOKEN.finditer(text)]
    hits = []
    for i, t in enumerate(toks):
        if _h(t) in names:
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if _h(f"{t} {nxt}") in allow:
                continue
            hits.append(i)
    return hits


def test_hash_file_is_not_empty():
    assert len(_load("popia_names.sha256")) >= 10


def test_detector_finds_a_planted_name():
    names = {_h("zqxplanted")}
    assert find_hits("Reviewed by Zqxplanted today.", names, set()) == [2]
    assert find_hits("Zqxplanted Town", names, {_h("zqxplanted town")}) == []


def test_no_protected_names_in_tracked_files():
    names, allow = _names(), _load("popia_allow.sha256")
    bad = []
    for rel in _tracked():
        p = ROOT / rel
        for label, text in ((rel, rel),):
            if find_hits(text, names, allow):
                bad.append(f"path: {rel}")
        try:
            data = p.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            continue
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if find_hits(line, names, allow):
                bad.append(f"{rel}:{n}")
    # Report locations only, never the matched word.
    assert not bad, "protected names found (see CHG-2026-049):\n" + "\n".join(bad[:50])
