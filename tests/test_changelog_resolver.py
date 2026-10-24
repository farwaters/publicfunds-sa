"""The change-log merge resolver in the merge notes of itil/changes/CHG-2026-032-live-site-check.md (CHG-2026-032).

The command is extracted from that file, not retyped here, and run through bash in throwaway git repos with real merge
conflicts, so the documented text is the tested text. No network, nothing outside a temporary directory is touched."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RFC = Path(__file__).resolve().parents[1] / "itil" / "changes" / "CHG-2026-032-live-site-check.md"
CL = "itil/registers/change-log.md"
pytestmark = pytest.mark.skipif(shutil.which("git") is None or shutil.which("bash") is None, reason="needs git and bash")


def documented_command() -> str:
    """The code block of the merge notes that starts with the python3 heredoc (its first line carries the && chain)."""
    text = RFC.read_text(encoding="utf-8")
    notes = text[text.index("## Merge notes"):]
    blocks = re.findall(r"```\n(.*?)\n```", notes, flags=re.S)
    found = [b for b in blocks if b.startswith("python3 - <<'PY'")]
    assert len(found) == 1, "expected exactly one resolver block in the merge notes"
    return found[0] + "\n"


ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_MERGE_AUTOEDIT": "no",
       "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, env=ENV, capture_output=True)
    if check:
        assert r.returncode == 0, r.stderr.decode()
    return r


def row(n, text="x"):
    return f"| CHG-2026-{n:03d} | 2026-10-24 | Normal | {text} | branch b{n} | PR open |"


HEAD = ["# Change log", "", "| id | date | type | what | where | status |", "|---|---|---|---|---|---|"]
PROSE = ["", "Some prose between the rows.", ""]


def log(rows_before, prose=PROSE, rows_after=(), eol="\n", tail=""):
    return eol.join(HEAD + list(rows_before) + list(prose) + list(rows_after)) + eol + tail


def make_repo(tmp_path, base, ours, theirs):
    """main = base; branch 'ours' and branch 'theirs' change the change-log; 'ours' is checked out and 'theirs' merged (no commit)."""
    repo = tmp_path / "repo"
    (repo / "itil" / "registers").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.autocrlf", "false")
    (repo / CL).write_bytes(base.encode())
    (repo / "other.txt").write_text("unrelated\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    for name, content in (("theirs", theirs), ("ours", ours)):
        git(repo, "checkout", "-q", "-b", name, "main")
        (repo / CL).write_bytes(content.encode())
        git(repo, "commit", "-q", "-am", name)
    merge = git(repo, "merge", "--no-ff", "theirs", check=False)
    assert merge.returncode == 1 and b"CONFLICT" in merge.stdout, (merge.stdout, merge.stderr)
    return repo


def resolve(repo):
    return subprocess.run(["bash", "-c", documented_command()], cwd=repo, env=ENV, capture_output=True)


def head(repo):
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def rows_of(text):
    return [l for l in text.replace("\r", "").split("\n") if l.startswith("| CHG-")]


BASE_ROWS = [row(1), row(2, "old wording")]
BASE = log(BASE_ROWS, rows_after=[row(3)])


def assert_stopped(repo, before_head, conflicted, message):
    """A stop: exit 1 with the message, the file is exactly as git left it (markers included), nothing staged or committed."""
    r = resolve(repo)
    assert r.returncode == 1, (r.returncode, r.stderr.decode())
    assert message in r.stderr.decode()
    assert (repo / CL).read_bytes() == conflicted and b"<<<<<<<" in conflicted
    assert head(repo) == before_head
    assert (repo / ".git" / "MERGE_HEAD").exists()
    assert CL in git(repo, "diff", "--name-only", "--diff-filter=U").stdout.decode()
    assert not any(l.startswith("M ") or l.startswith("A ") for l in git(repo, "status", "--short").stdout.decode().split("\n") if CL in l)


def run_stop(tmp_path, ours, theirs, message):
    repo = make_repo(tmp_path, BASE, ours, theirs)
    assert_stopped(repo, head(repo), (repo / CL).read_bytes(), message)
    return repo


def happy(tmp_path, swap, base_rows=BASE_ROWS, rows_after=(row(3),)):
    # ours: a new row at the end of the table block; theirs: an edited older row and a different new row at the same place
    base = log(base_rows, rows_after=rows_after)
    ours = log([*base_rows, row(4, "ours")], rows_after=rows_after)
    theirs = log([row(1), row(2, "edited by them"), row(5, "theirs")], rows_after=rows_after)
    if swap:
        ours, theirs = theirs, ours
    repo = make_repo(tmp_path, base, ours, theirs)
    before = head(repo)
    r = resolve(repo)
    assert r.returncode == 0, r.stderr.decode()
    assert head(repo) != before and not (repo / ".git" / "MERGE_HEAD").exists()
    assert len(git(repo, "rev-list", "--parents", "-n1", "HEAD").stdout.split()) == 3, "a merge commit"
    text = (repo / CL).read_text(encoding="utf-8")
    ids = [l.split(" |")[0] for l in rows_of(text)]
    assert sorted(ids) == sorted(set(ids)) and len(ids) == len(base_rows) + len(rows_after) + 2, ids
    assert "<<<<<<<" not in text and ">>>>>>>" not in text and "\n=======\n" not in text
    assert text.endswith("\n") and all(l.endswith(" |") for l in rows_of(text))
    assert "Some prose between the rows." in text
    assert row(2, "edited by them") in text and row(4, "ours") in text and row(5, "theirs") in text
    assert all(r in text for r in rows_after)
    assert row(2, "old wording") not in text
    return text


@pytest.mark.parametrize("swap", [False, True])
def test_happy_path_keeps_every_row_and_commits(tmp_path, swap):
    happy(tmp_path, swap)


def test_happy_path_has_the_same_rows_in_either_order(tmp_path):
    texts = []
    for i, swap in enumerate((False, True)):
        sub = tmp_path / str(i)
        sub.mkdir()
        texts.append(happy(sub, swap))
    assert sorted(rows_of(texts[0])) == sorted(rows_of(texts[1]))


def test_with_the_rows_in_id_order_the_whole_file_is_the_same_in_either_order(tmp_path):
    # where a row goes is decided by id, not by side; with a layout in id order the two orders give the same file.
    # (Where the existing rows are out of id order, the same rows are kept but may sit in a different place.)
    texts = []
    for i, swap in enumerate((False, True)):
        sub = tmp_path / str(i)
        sub.mkdir()
        texts.append(happy(sub, swap, rows_after=()))
    assert texts[0] == texts[1]


def test_a_new_row_before_a_larger_id_goes_in_front_of_it(tmp_path):
    base = log([row(1), row(9)])
    ours = log([row(1), row(4, "ours"), row(9)])
    theirs = log([row(1), row(5, "theirs"), row(9)])
    repo = make_repo(tmp_path, base, ours, theirs)
    assert resolve(repo).returncode == 0
    assert [l.split(" |")[0][-3:] for l in rows_of((repo / CL).read_text(encoding="utf-8"))] == ["001", "004", "005", "009"]


def test_duplicate_id_is_a_clean_message_not_a_traceback(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours"), row(4, "ours again")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    r = resolve(repo)
    err = r.stderr.decode()
    assert r.returncode == 1
    assert "our side has the id CHG-2026-004 twice: resolve by hand" in err
    assert "Traceback" not in err and "AssertionError" not in err
    assert b"<<<<<<<" in (repo / CL).read_bytes() and (repo / ".git" / "MERGE_HEAD").exists()


def test_duplicate_id_on_their_side_names_their_side(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs"), row(5, "again")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    r = resolve(repo)
    assert r.returncode == 1 and "their side has the id CHG-2026-005 twice" in r.stderr.decode()
    assert "Traceback" not in r.stderr.decode()


def test_change_outside_the_table_rows_stops(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], prose=["", "Prose edited by them.", ""], rows_after=[row(3)])
    repo = run_stop(tmp_path, ours, theirs, "they changed lines other than table rows: resolve by hand")
    assert b"Some prose between the rows." in (repo / CL).read_bytes() or b"Prose edited by them." in (repo / CL).read_bytes()


def test_prose_changed_only_on_our_side_is_kept(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], prose=["", "Prose edited by us.", ""], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    assert resolve(repo).returncode == 0
    text = (repo / CL).read_text(encoding="utf-8")
    assert "Prose edited by us." in text and row(4, "ours") in text and row(5, "theirs") in text


def test_both_sides_changing_one_row_stops_and_drops_nothing(tmp_path):
    ours = log([row(1), row(2, "ours wording"), row(4, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "their wording"), row(5, "theirs")], rows_after=[row(3)])
    repo = run_stop(tmp_path, ours, theirs, "both sides changed row CHG-2026-002: resolve by hand")
    marked = (repo / CL).read_text(encoding="utf-8")
    for needed in (row(2, "ours wording"), row(2, "their wording"), row(4, "ours"), row(5, "theirs")):
        assert needed in marked, "git's conflict file keeps both sides; the script must not touch it"


def test_both_sides_adding_the_same_id_with_different_text_stops(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(4, "theirs")], rows_after=[row(3)])
    run_stop(tmp_path, ours, theirs, "both sides changed row CHG-2026-004: resolve by hand")


def test_same_row_added_identically_by_both_sides_is_kept_once(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "same"), row(6, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(4, "same"), row(7, "theirs")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    assert resolve(repo).returncode == 0
    ids = [l.split(" |")[0] for l in rows_of((repo / CL).read_text(encoding="utf-8"))]
    assert ids.count("| CHG-2026-004") == 1 and len(ids) == 6


def test_a_row_deleted_by_one_side_and_untouched_by_the_other_is_deleted(tmp_path):
    ours = log([row(1), row(4, "ours")], rows_after=[row(3)])  # ours removed row 2
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    assert resolve(repo).returncode == 0
    ids = [l.split(" |")[0][-3:] for l in rows_of((repo / CL).read_text(encoding="utf-8"))]
    assert "002" not in ids and {"001", "003", "004", "005"} <= set(ids)


def test_crlf_line_endings_are_kept(tmp_path):
    base = log(BASE_ROWS, rows_after=[row(3)], eol="\r\n")
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)], eol="\r\n")
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)], eol="\r\n")
    repo = make_repo(tmp_path, base, ours, theirs)
    assert resolve(repo).returncode == 0
    data = (repo / CL).read_bytes()
    assert data.count(b"\n") == data.count(b"\r\n") and data.endswith(b"\r\n")
    assert b"CHG-2026-004" in data and b"CHG-2026-005" in data


def test_trailing_blank_lines_are_kept(tmp_path):
    base = log(BASE_ROWS, rows_after=[row(3)], tail="\n\n")
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)], tail="\n\n")
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)], tail="\n\n")
    repo = make_repo(tmp_path, base, ours, theirs)
    assert resolve(repo).returncode == 0
    data = (repo / CL).read_bytes()
    assert data.endswith(row(5, "theirs").encode() + b"\n\n\n"), data[-80:]


def test_the_unconflicted_other_file_is_untouched(tmp_path):
    ours = log([row(1), row(2, "old wording"), row(4, "ours")], rows_after=[row(3)])
    theirs = log([row(1), row(2, "old wording"), row(5, "theirs")], rows_after=[row(3)])
    repo = make_repo(tmp_path, BASE, ours, theirs)
    assert resolve(repo).returncode == 0
    assert (repo / "other.txt").read_text() == "unrelated\n"
    assert git(repo, "diff", "--name-only", "main", "HEAD").stdout.decode().split() == [CL]
