"""CHG-2026-040 (CSI-053): nightly evidence guard. Pure function tests, the X1 case on the real published file, and the wiring in
`pf publish-data` on a real synthetic build: a normal run passes, a run that empties a data type + year is refused with exit 3 and
leaves every published file byte for byte as it was."""
import copy
import json
import shutil
from datetime import date

import duckdb
import pytest

from thusa import evidence_guard as eg
from thusa import publish_data as pdx
from thusa.evidence_guard import EvidenceGuardError, evidence_guard, present_counts
from thusa.review.cli import main as pf_main
from thusa.settings import REPO_ROOT, get_paths, load_yaml

TYPES = ["budget", "actual_audited", "uifw", "audit_opinion", "procurement"]
REAL = json.loads((REPO_ROOT / "public-data/v1/coverage.json").read_text())
ALLOW = {"data_type": "audit_opinion", "year": 2023, "reason": "KE-999: test only", "date": "2026-11-02"}


def cov(n_by_type_year, years=(2021, 2022, 2023), n_ent=30):
    """A coverage document with n_by_type_year[(type, year)] fully present entities (default 0); the rest are 'm'."""
    ents = []
    for i in range(n_ent):
        c = {t: "".join("P" if i < n_by_type_year.get((t, y), 0) else "m" for y in years) for t in TYPES}
        ents.append({"id": f"MUN:T{i:02d}", "c": c, "r": {t: "0" * len(years) for t in TYPES}})
    return {"years": list(years), "data_types": TYPES, "entities": ents}


BASE = {(t, y): 25 for t in TYPES for y in (2021, 2022, 2023)}


def test_unchanged_passes_with_no_notes():
    r = evidence_guard(cov(BASE), cov(BASE))
    assert r == {"status": "pass", "empty": [], "allowed": [], "drops": [], "stale_allow": [], "notes": []}


def test_first_run_without_previous_file_passes_with_a_note():
    r = evidence_guard(None, cov(BASE))
    assert r["status"] == "pass" and r["empty"] == [] and "first run" in r["notes"][0]


def test_a_type_and_year_that_becomes_fully_empty_fails():
    r = evidence_guard(cov(BASE), cov(BASE | {("audit_opinion", 2022): 0}))
    assert r["status"] == "fail"
    assert r["empty"] == [{"data_type": "audit_opinion", "year": 2022, "before": 25, "after": 0}]
    assert r["notes"] == ["BLOCK: audit_opinion 2022: 25 fully present municipalities before, 0 now"]


def test_one_left_is_not_empty():
    r = evidence_guard(cov(BASE), cov(BASE | {("audit_opinion", 2022): 1}))
    assert r["status"] == "pass" and r["empty"] == []


def test_a_type_and_year_that_was_already_empty_is_not_a_failure():
    b = BASE | {("uifw", 2023): 0}
    assert evidence_guard(cov(b), cov(b))["status"] == "pass"


def test_partial_cells_do_not_count_as_present():
    prev, cand = cov(BASE), cov(BASE)
    for e in cand["entities"]:
        e["c"]["budget"] = e["c"]["budget"][:2] + "p"          # 2023 becomes partial for everyone
    r = evidence_guard(prev, cand)
    assert r["status"] == "fail" and [(d["data_type"], d["year"]) for d in r["empty"]] == [("budget", 2023)]


def test_a_year_missing_from_the_candidate_counts_as_empty_and_a_new_year_is_not_a_failure():
    r = evidence_guard(cov(BASE), cov({k: v for k, v in BASE.items() if k[1] != 2021}, years=(2022, 2023)))
    assert r["status"] == "fail" and {d["year"] for d in r["empty"]} == {2021}
    assert len(r["empty"]) == len(TYPES)
    grown = evidence_guard(cov(BASE), cov(BASE | {(t, 2024): 5 for t in TYPES}, years=(2021, 2022, 2023, 2024)))
    assert grown["status"] == "pass" and grown["notes"] == []


def test_a_type_missing_from_the_candidate_counts_as_empty():
    cand = cov(BASE)
    cand["data_types"] = [t for t in TYPES if t != "procurement"]
    for e in cand["entities"]:
        del e["c"]["procurement"]
    r = evidence_guard(cov(BASE), cand)
    assert r["status"] == "fail" and {d["data_type"] for d in r["empty"]} == {"procurement"}


def test_each_empty_pair_is_listed_not_only_the_first():
    r = evidence_guard(cov(BASE), cov(BASE | {("uifw", 2021): 0, ("budget", 2023): 0}))
    assert [(d["data_type"], d["year"]) for d in r["empty"]] == [("uifw", 2021), ("budget", 2023)]


# --- allow list -------------------------------------------------------------------------------------------------------------
def test_allow_entry_lets_that_loss_through_and_only_that_loss():
    cand = cov(BASE | {("audit_opinion", 2023): 0})
    r = evidence_guard(cov(BASE), cand, [ALLOW])
    assert r["status"] == "pass" and r["empty"] == []
    assert r["allowed"] == [{"data_type": "audit_opinion", "year": 2023, "before": 25, "after": 0, "reason": "KE-999: test only"}]
    assert r["notes"] == ["allowed: audit_opinion 2023: 25 before, 0 now (KE-999: test only)"]
    other = evidence_guard(cov(BASE), cov(BASE | {("audit_opinion", 2023): 0, ("budget", 2023): 0}), [ALLOW])
    assert other["status"] == "fail" and [(d["data_type"], d["year"]) for d in other["empty"]] == [("budget", 2023)]
    wrong_year = evidence_guard(cov(BASE), cand, [ALLOW | {"year": 2022}])
    assert wrong_year["status"] == "fail"
    wrong_type = evidence_guard(cov(BASE), cand, [ALLOW | {"data_type": "budget"}])
    assert wrong_type["status"] == "fail"


def test_allow_entry_no_longer_needed_is_a_warning_not_a_failure():
    r = evidence_guard(cov(BASE), cov(BASE), [ALLOW])
    assert r["status"] == "pass" and r["stale_allow"] == [{"data_type": "audit_opinion", "year": 2023,
                                                           "reason": "KE-999: test only", "after": 25}]
    assert r["notes"] == ["warn: allow entry audit_opinion 2023 is no longer needed (25 present again): remove it"]


def test_allow_entry_is_stale_as_soon_as_one_municipality_is_present_again():
    one = evidence_guard(cov(BASE | {("audit_opinion", 2023): 0}), cov(BASE | {("audit_opinion", 2023): 1}), [ALLOW])
    assert one["status"] == "pass" and [d["after"] for d in one["stale_allow"]] == [1]
    none = evidence_guard(cov(BASE), cov(BASE | {("audit_opinion", 2023): 0}), [ALLOW])
    assert none["stale_allow"] == []                  # still empty: the entry is doing its job


@pytest.mark.parametrize("bad", [
    {k: v for k, v in ALLOW.items() if k != "reason"}, ALLOW | {"reason": "  "}, ALLOW | {"reason": None},
    {k: v for k, v in ALLOW.items() if k != "date"}, ALLOW | {"date": "02/11/2026"}, ALLOW | {"date": "2026-13-45"},
    ALLOW | {"date": 20261102}, ALLOW | {"data_type": "flags"}, ALLOW | {"data_type": None}, ALLOW | {"year": "2023"},
    ALLOW | {"year": True}, ALLOW | {"year": None}, "audit_opinion 2023"])
def test_malformed_allow_entry_is_refused(bad):
    with pytest.raises(EvidenceGuardError):
        evidence_guard(cov(BASE), cov(BASE), [bad])


def test_duplicate_allow_entry_is_refused_and_a_yaml_date_is_accepted():
    with pytest.raises(EvidenceGuardError):
        evidence_guard(cov(BASE), cov(BASE), [ALLOW, ALLOW])
    assert evidence_guard(cov(BASE), cov(BASE), [ALLOW | {"date": date(2026, 11, 2)}])["status"] == "pass"


def test_repository_allow_list_is_pinned_empty():
    """Adding an entry needs an RFC row and the owner's GO: this pin makes the edit visible in review."""
    assert load_yaml("evidence-guard-allow.yaml") == {"allow": []}


# --- WARN only: a drop in the count never blocks ---------------------------------------------------------------------------
def test_drop_over_the_share_warns_but_does_not_block():
    r = evidence_guard(cov(BASE), cov(BASE | {("budget", 2023): 20}))          # 25 -> 20 = 20% fewer
    assert r["status"] == "pass" and r["empty"] == []
    assert r["drops"] == [{"data_type": "budget", "year": 2023, "before": 25, "after": 20, "share": 0.2}]
    assert r["notes"] == ["warn: budget 2023: 25 -> 20 (20.0% fewer)"]


def test_drop_exactly_at_the_share_is_not_reported_and_just_over_is():
    b = {(t, y): 20 for t in TYPES for y in (2021, 2022, 2023)}
    assert evidence_guard(cov(b), cov(b | {("budget", 2023): 18}), warn_share=0.10)["drops"] == []   # exactly 10%
    assert len(evidence_guard(cov(b), cov(b | {("budget", 2023): 17}), warn_share=0.10)["drops"]) == 1  # 15%


def test_a_rise_is_never_reported():
    assert evidence_guard(cov(BASE), cov(BASE | {("budget", 2023): 30}))["notes"] == []


def test_small_previous_counts_are_not_assessed_for_drops():
    b = {(t, y): 19 for t in TYPES for y in (2021, 2022, 2023)}
    assert evidence_guard(cov(b), cov(b | {("budget", 2023): 1}), min_previous=20)["drops"] == []
    assert len(evidence_guard(cov(b), cov(b | {("budget", 2023): 1}), min_previous=19)["drops"]) == 1


def test_default_constants_are_pinned():
    assert eg.WARN_DROP_SHARE == 0.10 and eg.WARN_MIN_PREVIOUS == 20
    assert evidence_guard(cov(BASE), cov(BASE | {("budget", 2023): 23}))["drops"] == []         # 8% fewer: below the default
    assert len(evidence_guard(cov(BASE), cov(BASE | {("budget", 2023): 22}))["drops"]) == 1     # 12% fewer: above it


def test_a_drop_to_empty_is_a_failure_and_not_also_a_drop():
    r = evidence_guard(cov(BASE), cov(BASE | {("budget", 2023): 0}))
    assert r["status"] == "fail" and r["drops"] == []


@pytest.mark.parametrize("bad", [{}, {"years": [1], "data_types": TYPES}, {"years": [2021], "data_types": ["budget"],
                                                                         "entities": [{"id": "x", "c": {"budget": "PP"}}]},
                                 {"years": [2021], "data_types": ["budget"], "entities": [{"id": "x"}]},
                                 {"years": [2021], "data_types": ["budget"], "entities": [{"id": "x", "c": {"budget": None}}]},
                                 None])
def test_malformed_coverage_is_refused_for_either_side(bad):
    with pytest.raises(EvidenceGuardError):
        present_counts(bad)
    with pytest.raises(EvidenceGuardError):
        evidence_guard(cov(BASE), bad)
    if bad is not None:                               # None as the previous file means "first run", not malformed
        with pytest.raises(EvidenceGuardError):
            evidence_guard(bad, cov(BASE))


# --- the real published file -----------------------------------------------------------------------------------------------
def _emptied(doc, dt, year, n=None):
    """Copy of `doc` with the first n (default all) fully present cells of dt for year turned to 'm'."""
    out, i, left = copy.deepcopy(doc), doc["years"].index(year), n
    for e in out["entities"]:
        s = e["c"][dt]
        if s[i] == "P" and (left is None or left > 0):
            e["c"][dt] = s[:i] + "m" + s[i + 1:]
            left = None if left is None else left - 1
    return out


def test_real_published_file_passes_against_itself():
    assert evidence_guard(REAL, copy.deepcopy(REAL)) == {"status": "pass", "empty": [], "allowed": [], "drops": [],
                                                         "stale_allow": [], "notes": []}


def test_every_guarded_pair_of_the_real_file_blocks_when_emptied():
    counts, n = present_counts(REAL), 0
    for (dt, y), c in counts.items():
        if c >= 1:
            r = evidence_guard(REAL, _emptied(REAL, dt, y))
            assert r["status"] == "fail" and [(d["data_type"], d["year"]) for d in r["empty"]] == [(dt, y)], (dt, y)
            n += 1
    assert n >= 20                                    # 28 on 25 Oct 2026: a file with fewer guarded pairs means the data shrank


def test_x1_scratch_100_opinion_cells_for_2022_23_on_the_real_file():
    """X1 of the CHG-2026-033 review: 100 of the opinion cells for 2022/23 emptied. Under the agreed rule this is NOT a block
    (the other fully present municipalities remain): it is a WARN with the share. Emptying all of them is a block."""
    before = present_counts(REAL)[("audit_opinion", 2023)]
    assert before >= 100
    r = evidence_guard(REAL, _emptied(REAL, "audit_opinion", 2023, 100))
    assert r["status"] == "pass" and r["empty"] == []
    assert r["drops"] == [{"data_type": "audit_opinion", "year": 2023, "before": before, "after": before - 100,
                           "share": round(100 / before, 3)}]
    assert evidence_guard(REAL, _emptied(REAL, "audit_opinion", 2023))["status"] == "fail"


# --- wiring in pf publish-data, on a real synthetic build ------------------------------------------------------------------
def _snapshot(d):
    return {p.name: p.read_bytes() for p in sorted(d.iterdir())}


def _emptied_copy(synth_root, tmp_path, monkeypatch, where="data_type = 'audit_opinion' AND fye = 2023"):
    root = tmp_path / "wh2"
    shutil.copytree(synth_root, root)
    con = duckdb.connect(str(get_paths(root).warehouse))
    n = con.execute(f"UPDATE marts.coverage_cell SET state = 'missing', reason_code = 'opinion_outstanding' "
                    f"WHERE state = 'present' AND {where}").fetchone()[0]
    con.close()
    assert n >= 1
    monkeypatch.setenv("THUSA_ROOT", str(root))
    return get_paths(root)


def test_normal_run_passes_and_a_second_run_changes_nothing(paths, tmp_path, capsys):
    out = tmp_path / "pd"
    first = pdx.export(paths, out)
    assert first["evidence_guard"]["status"] == "pass" and "first run" in first["evidence_guard"]["notes"][0]
    snap = _snapshot(out)
    capsys.readouterr()
    second = pdx.export(paths, out)
    assert second["evidence_guard"] == {"status": "pass", "notes": []}
    assert "evidence guard" not in capsys.readouterr().err          # nothing to say on a normal run
    assert {k: v for k, v in _snapshot(out).items() if k not in pdx.META_FILES} == \
        {k: v for k, v in snap.items() if k not in pdx.META_FILES}


def test_emptied_type_and_year_is_refused_and_published_files_are_untouched(paths, tmp_path, monkeypatch, synth_root):
    out = tmp_path / "pd"
    pdx.export(paths, out)
    before = _snapshot(out)
    assert present_counts(json.loads(before["coverage.json"]))[("audit_opinion", 2023)] >= 1
    bad = _emptied_copy(synth_root, tmp_path, monkeypatch)
    with pytest.raises(pdx.UnsafeExport, match=r"evidence guard: BLOCK: audit_opinion 2023: \d+ fully present municipalities before, 0 now"):
        pdx.export(bad, out)
    assert _snapshot(out) == before                   # no file changed, none added (no .part left behind), none removed


def test_cli_exits_3_on_a_block_and_0_on_a_normal_run(paths, tmp_path, monkeypatch, synth_root, capsys):
    out = tmp_path / "pd"
    assert pf_main(["publish-data", "--out", str(out)]) == 0
    before = _snapshot(out)
    _emptied_copy(synth_root, tmp_path, monkeypatch)
    capsys.readouterr()
    assert pf_main(["publish-data", "--out", str(out)]) == 3
    err = capsys.readouterr().err
    assert "public data not written" in err and "evidence guard: BLOCK: audit_opinion 2023" in err
    assert _snapshot(out) == before
    monkeypatch.setenv("THUSA_ROOT", str(synth_root))
    assert pf_main(["publish-data", "--out", str(out)]) == 0      # back to the normal data: published again


def test_allow_entry_lets_the_export_through_and_a_bad_entry_blocks_it(paths, tmp_path, monkeypatch, synth_root):
    out = tmp_path / "pd"
    pdx.export(paths, out)
    bad = _emptied_copy(synth_root, tmp_path, monkeypatch)
    real_load = pdx.load_yaml

    def with_allow(entries):
        return lambda name: {"allow": entries} if name == "evidence-guard-allow.yaml" else real_load(name)
    before = _snapshot(out)
    monkeypatch.setattr(pdx, "load_yaml", with_allow([{k: v for k, v in ALLOW.items() if k != "reason"}]))
    with pytest.raises(pdx.UnsafeExport, match="evidence guard could not run"):
        pdx.export(bad, out)
    assert _snapshot(out) == before
    monkeypatch.setattr(pdx, "load_yaml", with_allow([ALLOW]))
    res = pdx.export(bad, out)
    assert res["evidence_guard"]["status"] == "pass" and res["evidence_guard"]["notes"][0].startswith("allowed: audit_opinion 2023")
    assert present_counts(json.loads((out / "coverage.json").read_text()))[("audit_opinion", 2023)] == 0


@pytest.mark.parametrize("content", ["{not json", "[]", '{"years":[2023]}', ""])
def test_unreadable_previous_file_blocks_and_writes_nothing(paths, tmp_path, content):
    out = tmp_path / "pd"
    out.mkdir()
    (out / "coverage.json").write_text(content)
    with pytest.raises(pdx.UnsafeExport, match="evidence guard could not run"):
        pdx.export(paths, out)
    assert sorted(p.name for p in out.iterdir()) == ["coverage.json"] and (out / "coverage.json").read_text() == content


def test_missing_allow_file_blocks(paths, tmp_path, monkeypatch):
    real_load = pdx.load_yaml

    def load(name):
        if name == "evidence-guard-allow.yaml":
            raise FileNotFoundError(name)
        return real_load(name)
    monkeypatch.setattr(pdx, "load_yaml", load)
    with pytest.raises(pdx.UnsafeExport, match="evidence guard could not run"):
        pdx.export(paths, tmp_path / "pd")
    assert not (tmp_path / "pd").exists()


def test_drop_warning_is_printed_but_does_not_block(paths, tmp_path, capsys, monkeypatch):
    """A drop over the share is a WARN: the export goes ahead and the note reaches stderr (data/publish-data.log)."""
    out = tmp_path / "pd"
    pdx.export(paths, out)
    prev = json.loads((out / "coverage.json").read_text())
    i = prev["years"].index(2023)
    for k in range(25):          # the previous file had 25 more fully present audit opinions for 2022/23 than the new build
        c = {t: "-" * len(prev["years"]) for t in prev["data_types"]}
        c["audit_opinion"] = "-" * i + "P" + "-" * (len(prev["years"]) - i - 1)
        prev["entities"].append({"id": f"MUN:PAD{k}", "c": c, "r": prev["entities"][0]["r"]})
    (out / "coverage.json").write_text(json.dumps(prev))
    capsys.readouterr()
    res = pdx.export(paths, out)
    assert res["evidence_guard"]["status"] == "pass"
    assert any(n.startswith("warn: ") and "fewer" in n for n in res["evidence_guard"]["notes"])
    assert "evidence guard: warn:" in capsys.readouterr().err
