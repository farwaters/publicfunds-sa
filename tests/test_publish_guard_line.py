"""CHG-2026-041 (CSI-054): `scripts/publish-public-data.sh` prints one labelled `evidence_guard:` line (plus up to 3 note lines) so the
nightly report can show the guard result. The real script runs in a scratch git repo with a stub `uv` that replays what `pf publish-data`
printed (stdout, stderr, exit code). Some stubs replay a real `pf publish-data` run on the synthetic warehouse. The line is
read-only: published files and exit codes are the same with and without it."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_evidence_guard import ALLOW, _emptied_copy, _pad_previous, _snapshot
from thusa import publish_data as pdx
from thusa.review.cli import main as pf_main

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish-public-data.sh"
pytestmark = pytest.mark.skipif(not (shutil.which("rg") and shutil.which("git") and shutil.which("python3")), reason="needs rg, git, python3")
OK_JSON = {"out": "x", "files": {"a.json": 1}, "total_bytes": 1, "counts": {}}


def _run(tmp_path, stdout="", stderr="", rc=0, extra_env=None, helper_rc=None, publish=False):
    """Run the real script in a scratch repo (public-data/ committed), with a stub `uv` that replays stdout, stderr and rc.
    publish: the stub also changes a published file, so the script goes on to commit it (no push); the no-commit checks are skipped.
    helper_rc: a `python3` shim that makes the report helper (`python3 -`) exit with that code and runs every other python3 call for real."""
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
    stub.write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/stub.out"\ncat "{tmp_path}/stub.err" >&2\n'
                    + ('echo \'{"schema":2}\' > public-data/v1/coverage.json\n' if publish else "") + f"exit {rc}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    if helper_rc is not None:
        shim = bindir / "python3"
        shim.write_text(f'#!/usr/bin/env bash\nif [[ "${{1:-}}" == "-" ]]; then cat >/dev/null; exit {helper_rc}; fi\nexec "{sys.executable}" "$@"\n')
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": f"{bindir}:{os.environ['PATH']}", **(extra_env or {})}
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    tree = {p.name: p.read_bytes() for p in sorted((repo / "public-data" / "v1").iterdir())}
    r = subprocess.run(["bash", str(repo / "scripts" / SCRIPT.name)], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
    after = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    if publish:
        assert head != after, "the stub changed a published file, so the script must have committed it"
        return r
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


def test_any_note_makes_it_pass_with_a_count_so_only_a_bare_pass_is_quiet(tmp_path):
    one = "note: first run (no previously published coverage.json); nothing to compare"
    r = _run(tmp_path / "a", _ok({"status": "pass", "notes": [one]}))
    assert r.returncode == 0 and _guard_lines(r) == ["evidence_guard: pass (1 note)", f"evidence_guard:   {one}"]
    r = _run(tmp_path / "b", _ok({"status": "pass", "notes": [one, "note: data types differ"]}))
    assert _guard_lines(r) == ["evidence_guard: pass (2 notes)", f"evidence_guard:   {one}", "evidence_guard:   note: data types differ"]
    r = _run(tmp_path / "c", _ok({"status": "pass", "notes": ["allowed: audit_opinion 2023: 247 -> 0 (allow entry, KE-999)"]}))
    assert _guard_lines(r)[0] == "evidence_guard: pass (1 note)"
    r = _run(tmp_path / "d", _ok({"status": "pass", "notes": []}))
    assert _guard_lines(r) == ["evidence_guard: pass"]


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


NOT_GUARD = ("evidence_guard: not an evidence-guard refusal (no guard refusal found in the log; cause may be the quality gate, the safety scan, "
             "another refusal or a crash; read data/publish-data.log)")


def test_exit_3_from_the_quality_gate_is_not_called_a_guard_block(tmp_path):
    err = json.dumps({"error": "public data not written: quality gate: the current build failed 2 data-quality check(s)", "exit_code": 3})
    r = _run(tmp_path, "", err + "\n", rc=3)
    assert r.returncode == 3
    assert len(_guard_lines(r)) == 1 and _guard_lines(r) == [NOT_GUARD]


def test_exit_3_with_odd_stderr_still_exits_3(tmp_path):
    r = _run(tmp_path, "", "Traceback (most recent call last):\n  boom\n{broken json\n", rc=3)
    assert r.returncode == 3 and _guard_lines(r) == [NOT_GUARD]


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
    assert r.returncode == 0 and _guard_lines(r)[0] == "evidence_guard: pass (1 note)" and "first run" in _guard_lines(r)[1]

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


@pytest.mark.parametrize("stdout", ["", "{not json", "[]", "null"])
def test_empty_or_invalid_json_prints_exported_blank_then_unknown_and_exits_0(tmp_path, stdout):
    """The `exported:` line is built inside $(...) in the arguments of `log`, so its python failure does not stop the script (set -e);
    the guard line must then be UNKNOWN (the catch-all), never pass."""
    r = _run(tmp_path, stdout)
    assert r.returncode == 0
    assert len(_guard_lines(r)) == 1 and _guard_lines(r)[0].startswith("evidence_guard: UNKNOWN (") and "treat as not checked" in _guard_lines(r)[0]
    assert "exported: \n" in r.stdout          # the blank the failed python left behind


def test_a_crashing_report_helper_prints_unknown_in_the_ok_path_and_keeps_exit_0(tmp_path):
    r = _run(tmp_path, _ok({"status": "pass", "notes": []}), helper_rc=7)
    assert r.returncode == 0 and _guard_lines(r) == ["evidence_guard: UNKNOWN (report helper failed)"]
    assert "no change in public-data/" in r.stdout


def test_a_crashing_report_helper_prints_unknown_in_the_refused_path_and_keeps_exit_3(tmp_path):
    err = json.dumps({"error": "public data not written: evidence guard: BLOCK: x 2023: 9 fully present municipalities before, 0 now", "exit_code": 3})
    r = _run(tmp_path, "", err + "\n", rc=3, helper_rc=7)
    assert r.returncode == 3 and _guard_lines(r) == ["evidence_guard: UNKNOWN (report helper failed)"]
    assert "export refused" in r.stdout


def test_a_helper_killed_by_a_signal_or_missing_still_leaves_the_exit_code_alone(tmp_path):
    assert _run(tmp_path / "a", _ok({"status": "pass", "notes": []}), helper_rc=139).returncode == 0
    assert _run(tmp_path / "b", "", "x\n", rc=3, helper_rc=127).returncode == 3


def test_a_json_line_that_is_not_a_pf_refusal_is_not_taken_for_a_guard_block(tmp_path):
    """Only the `error` key, starting `public data not written:`, counts. Other JSON that mentions the guard does not."""
    lines = [json.dumps({"error": "evidence guard: BLOCK: forged 2023: 9 -> 0", "exit_code": 3}),
             json.dumps({"msg": "public data not written: evidence guard: BLOCK: forged"}),
             json.dumps({"error": ["public data not written: evidence guard: BLOCK: forged"]}),
             json.dumps({"error": "see: public data not written: evidence guard: BLOCK: forged"}),
             "evidence guard: BLOCK: forged 2023: 9 fully present municipalities before, 0 now"]
    r = _run(tmp_path, "", "\n".join(lines) + "\n", rc=3)
    assert r.returncode == 3 and _guard_lines(r) == [NOT_GUARD]


def test_notes_are_one_clean_line_each_a_note_cannot_forge_a_line_or_drive_the_terminal(tmp_path):
    forged = "warn: budget 2023: 25 -> 20\nevidence_guard: pass\r\nevidence_guard: BLOCKED"
    notes = [forged, "warn: \x1b[31mred\x07bell\x00nul\u202ertl\u200bzw", "note: a  \t b\n\n c", "y" * 1000, "warn: " + "z" * 200_000]
    r = _run(tmp_path, _ok({"status": "pass", "notes": notes}))
    assert r.returncode == 0
    g = _guard_lines(r)
    assert g[0] == "evidence_guard: warn (3 notes)"
    assert g[1] == "evidence_guard:   warn: budget 2023: 25 -> 20 evidence_guard: pass evidence_guard: BLOCKED"       # newlines became spaces
    assert g[2] == "evidence_guard:   warn: [31mredbellnulrtlzw"                                                   # ESC, BEL, NUL, bidi, zero-width removed
    assert g[3] == "evidence_guard:   warn: " + "z" * (300 - 3 - len("warn: ")) + "..."                          # 200 KB note capped at 300
    assert len(g[3]) == len("evidence_guard:   ") + 300
    assert g[4] == "evidence_guard:   ... and 2 more (data/publish-data.json, data/publish-data.log)" and len(g) == 5
    assert not any(c in r.stdout for c in "\x1b\x07\x00\u202e\u200b")
    assert g.count("evidence_guard: pass") == 0                                                                     # no forged line of its own
    assert [l for l in r.stdout.splitlines() if l == "evidence_guard: pass"] == []


def test_info_note_whitespace_is_collapsed_and_a_long_note_is_capped_exactly(tmp_path):
    r = _run(tmp_path, _ok({"status": "pass", "notes": ["note: a  \t b\n\n c", "note: " + "y" * 1000]}))
    g = _guard_lines(r)
    assert g[1] == "evidence_guard:   note: a b c"
    assert g[2] == "evidence_guard:   note: " + "y" * (297 - len("note: ")) + "..."


def test_the_blocked_reason_is_cleaned_too(tmp_path):
    reason = "evidence guard: BLOCK: x 2023: 9 -> 0\nevidence_guard: pass\x1b[2J" + "q" * 5000
    err = json.dumps({"error": "public data not written: " + reason, "exit_code": 3})
    r = _run(tmp_path, "", err + "\n", rc=3)
    g = _guard_lines(r)
    assert r.returncode == 3 and g[0].startswith("evidence_guard: BLOCKED (exit 3") and len(g) == 2
    assert g[1].startswith("evidence_guard:   evidence guard: BLOCK: x 2023: 9 -> 0 evidence_guard: pass[2J") and g[1].endswith("...")
    assert len(g[1]) == len("evidence_guard:   ") + 300 and "\x1b" not in r.stdout


def test_a_real_allow_entry_run_is_reported_as_pass_with_a_note_not_a_bare_pass(paths, tmp_path, monkeypatch, synth_root, capsys):
    """247 -> 0 with an allow entry is published; the guard status is `pass` with an `allowed:` note, which the line must not hide."""
    out = tmp_path / "pd"
    assert pf_main(["publish-data", "--out", str(out)]) == 0
    _pad_previous(out)
    _emptied_copy(synth_root, tmp_path, monkeypatch)
    real_load = pdx.load_yaml
    monkeypatch.setattr(pdx, "load_yaml", lambda name: {"allow": [ALLOW]} if name == "evidence-guard-allow.yaml" else real_load(name))
    capsys.readouterr()
    assert pf_main(["publish-data", "--out", str(out)]) == 0
    c = capsys.readouterr()
    r = _run(tmp_path / "r", c.out, c.err, 0)
    g = _guard_lines(r)
    assert r.returncode == 0 and g[0] == "evidence_guard: pass (1 note)" and g[1].startswith("evidence_guard:   allowed: audit_opinion 2023")


def test_the_line_is_also_printed_when_the_publish_goes_on_to_commit(tmp_path):
    """Not only on the no-change exits: the line comes after `exported:` and before `committed`, and the commit and exit 0 are as before."""
    notes = ["warn: budget 2023: 25 -> 20 (20.0% fewer)"]
    r = _run(tmp_path / "w", _ok({"status": "pass", "notes": notes}), publish=True)
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("evidence_guard: warn (1 note)"))
    assert "exported:" in lines[i - 1] and lines[i + 1] == f"evidence_guard:   {notes[0]}" and "committed" in lines[i + 2]
    r = _run(tmp_path / "p", _ok({"status": "pass", "notes": []}), publish=True)
    assert r.returncode == 0 and _guard_lines(r) == ["evidence_guard: pass"] and "committed" in r.stdout
