"""CHG-2026-041 (CSI-054): `scripts/publish-public-data.sh` prints one labelled `evidence_guard:` line (plus up to 3 note lines) so the
nightly report can show the guard result. The real script runs in a scratch git repo with a stub `uv` that replays what `pf publish-data`
printed (stdout, stderr, exit code). Some stubs replay a real `pf publish-data` run on the synthetic warehouse. The line is
read-only: published files and exit codes are the same with and without it."""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from tests.test_evidence_guard import _emptied_copy, _pad_previous, _snapshot
from thusa.review.cli import main as pf_main

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish-public-data.sh"
pytestmark = pytest.mark.skipif(not (shutil.which("rg") and shutil.which("git") and shutil.which("python3")), reason="needs rg, git, python3")
OK_JSON = {"out": "x", "files": {"a.json": 1}, "total_bytes": 1, "counts": {}}


def _run(tmp_path, stdout="", stderr="", rc=0, extra_env=None):
    """Run the real script in a scratch repo (public-data/ committed), with a stub `uv` that replays stdout, stderr and rc."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "public-data" / "v1").mkdir(parents=True)
    shutil.copy(SCRIPT, repo / "scripts" / SCRIPT.name)
    (repo / "public-data" / "v1" / "manifest.json").write_text('{"build":{"id":"B1"}}\n')
    (repo / "public-data" / "v1" / "coverage.json").write_text('{"schema":1}\n')
    sh = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], check=True,
                                   capture_output=True)
    sh("init", "-q", "-b", "main"); sh("add", "-A"); sh("commit", "-q", "-m", "base")
    bindir = tmp_path / "bin"; bindir.mkdir()
    (tmp_path / "stub.out").write_text(stdout); (tmp_path / "stub.err").write_text(stderr)
    stub = bindir / "uv"
    stub.write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/stub.out"\ncat "{tmp_path}/stub.err" >&2\nexit {rc}\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", **(extra_env or {})}
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    tree = {p.name: p.read_bytes() for p in sorted((repo / "public-data" / "v1").iterdir())}
    r = subprocess.run(["bash", str(repo / "scripts" / SCRIPT.name)], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
    after = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    assert head == after, "the script must not commit in these cases"
    assert tree == {p.name: p.read_bytes() for p in sorted((repo / "public-data" / "v1").iterdir())}
    return r


def _guard_lines(r):
    return [l for l in r.stdout.splitlines() if l.startswith("evidence_guard:")]


def _ok(guard):
    return json.dumps(OK_JSON | ({"evidence_guard": guard} if guard is not None else {}))


def test_pass_prints_one_line_and_exits_0(tmp_path):
    r = _run(tmp_path, _ok({"status": "pass", "notes": []}))
    assert r.returncode == 0 and _guard_lines(r) == ["evidence_guard: pass"]
    assert "no change in public-data/" in r.stdout


def test_warn_prints_the_count_and_up_to_three_notes_then_a_more_line(tmp_path):
    notes = [f"warn: budget {y}: 25 -> 20 (20.0% fewer)" for y in (2021, 2022, 2023, 2024, 2025)]
    r = _run(tmp_path, _ok({"status": "pass", "notes": notes}))
    assert r.returncode == 0
    assert _guard_lines(r) == ["evidence_guard: warn (5 notes)", *[f"evidence_guard:   {n}" for n in notes[:3]],
                               "evidence_guard:   ... and 2 more (data/publish-data.json, data/publish-data.log)"]


def test_one_warn_is_singular_and_warns_come_before_info_notes(tmp_path):
    r = _run(tmp_path, _ok({"status": "pass", "notes": ["note: years differ", "warn: budget 2023: 25 -> 20 (20.0% fewer)"]}))
    assert _guard_lines(r)[:2] == ["evidence_guard: warn (1 note)", "evidence_guard:   warn: budget 2023: 25 -> 20 (20.0% fewer)"]
    assert _guard_lines(r)[2] == "evidence_guard:   note: years differ"


def test_info_notes_only_is_still_a_pass_and_the_note_is_shown(tmp_path):
    r = _run(tmp_path, _ok({"status": "pass", "notes": ["note: first run (no previously published coverage.json); nothing to compare"]}))
    assert _guard_lines(r) == ["evidence_guard: pass", "evidence_guard:   note: first run (no previously published coverage.json); nothing to compare"]


def test_block_exit_3_prints_blocked_and_the_reason_and_keeps_exit_3(tmp_path):
    err = json.dumps({"error": "public data not written: evidence guard: BLOCK: audit_opinion 2023: 247 fully present municipalities before, 0 now "
                               "(published files left as they are; see itil/changes/CHG-2026-040-evidence-guard.md)", "exit_code": 3})
    r = _run(tmp_path, "", "evidence guard: BLOCK: audit_opinion 2023: 247 fully present municipalities before, 0 now\n" + err + "\n", rc=3)
    assert r.returncode == 3
    g = _guard_lines(r)
    assert g[0] == "evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)"
    assert g[1].startswith("evidence_guard:   evidence guard: BLOCK: audit_opinion 2023: 247")
    assert "export refused" in r.stdout


def test_guard_could_not_run_is_also_blocked(tmp_path):
    err = json.dumps({"error": "public data not written: evidence guard could not run (nothing was written): YAMLError: x", "exit_code": 3})
    r = _run(tmp_path, "", err + "\n", rc=3)
    assert r.returncode == 3 and _guard_lines(r)[0].startswith("evidence_guard: BLOCKED (exit 3")
    assert "could not run" in _guard_lines(r)[1]


def test_exit_3_from_the_quality_gate_is_not_called_a_guard_block(tmp_path):
    err = json.dumps({"error": "public data not written: quality gate: the current build failed 2 data-quality check(s)", "exit_code": 3})
    r = _run(tmp_path, "", err + "\n", rc=3)
    assert r.returncode == 3
    assert len(_guard_lines(r)) == 1 and _guard_lines(r)[0].startswith("evidence_guard: not the cause (exit 3")


def test_exit_3_with_odd_stderr_still_exits_3(tmp_path):
    r = _run(tmp_path, "", "Traceback (most recent call last):\n  boom\n{broken json\n", rc=3)
    assert r.returncode == 3 and _guard_lines(r)[0].startswith("evidence_guard: not the cause")


@pytest.mark.parametrize("stdout", [_ok(None), _ok({"status": "fail", "notes": ["BLOCK: x"]}), _ok({"notes": []}),
                                    _ok({"status": "pass", "notes": "oops"}), _ok("text")])
def test_missing_or_unusable_key_is_unknown_not_pass_and_the_run_still_exits_0(tmp_path, stdout):
    r = _run(tmp_path, stdout)
    assert r.returncode == 0
    assert len(_guard_lines(r)) == 1 and _guard_lines(r)[0].startswith("evidence_guard: UNKNOWN (")
    assert "exported:" in r.stdout


def test_other_exit_codes_are_unchanged(tmp_path):
    """A normal run is still exit 0, and any failure of pf is still exit 3 whatever it printed."""
    (tmp_path / "a").mkdir()
    assert _run(tmp_path / "a", _ok({"status": "pass", "notes": []})).returncode == 0
    r = _run(tmp_path, "", "x\n", rc=7)          # any other failure of pf is still reported as exit 3 by the script
    assert r.returncode == 3


def test_a_real_pass_a_real_warn_and_a_real_block_through_pf_publish_data(paths, tmp_path, monkeypatch, synth_root, capsys):
    """Replay what `pf publish-data` really printed on the synthetic warehouse (stdout/stderr/exit code) through the real script."""
    out = tmp_path / "pd"
    capsys.readouterr()
    assert pf_main(["publish-data", "--out", str(out)]) == 0                        # first run: pass with a note
    c = capsys.readouterr()
    r = _run(tmp_path / "p", c.out, c.err, 0)
    assert r.returncode == 0 and _guard_lines(r)[0] == "evidence_guard: pass" and "first run" in _guard_lines(r)[1]

    _pad_previous(out, 25)                                                           # a drop over 10 %: warn, still published
    capsys.readouterr()
    assert pf_main(["publish-data", "--out", str(out)]) == 0
    c = capsys.readouterr()
    r = _run(tmp_path / "w", c.out, c.err, 0)
    g = _guard_lines(r)
    assert g[0] == "evidence_guard: warn (1 note)" and "audit_opinion 2023" in g[1] and "fewer" in g[1]

    out2 = tmp_path / "pd2"
    assert pf_main(["publish-data", "--out", str(out2)]) == 0
    _pad_previous(out2)
    before = _snapshot(out2)
    _emptied_copy(synth_root, tmp_path, monkeypatch)
    capsys.readouterr()
    assert pf_main(["publish-data", "--out", str(out2)]) == 3                        # a block: exit 3, nothing written
    c = capsys.readouterr()
    r = _run(tmp_path / "b", c.out, c.err, 3)
    assert r.returncode == 3 and _snapshot(out2) == before
    assert _guard_lines(r)[0].startswith("evidence_guard: BLOCKED (exit 3") and "BLOCK: audit_opinion 2023" in _guard_lines(r)[1]
