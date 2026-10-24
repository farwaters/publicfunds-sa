# CHG-2026-037: Record the merges of #35 and #31 and update the status cells (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-24 21:43, after the merges of #35 and #31. **Owner GO for this change (CHG-2026-037): none yet. No merge GO is given** |
| Environment | DEV (docs only). Nothing is built, run or published; PROD is affected only by the merge itself (markdown under `itil/` and `changes/`) |
| Type | Standard (`itil/change-enablement.md`: "docs/copy") |
| CIs affected | `changes/CAB-DECISION.md` (one new section, two wording fixes), `itil/registers/change-log.md` (status cells of CHG-2026-032 and -036, one new row), `itil/registers/csi-register.md` (CSI-036 row), the `Result:` line of `itil/changes/CHG-2026-032-live-site-check.md` and `CHG-2026-036-cab-records.md`, one wording fix in `CHG-2026-036-cab-records.md`, this record |
| Linked records | PRs #35 and #31; `changes/CAB-DECISION.md`; CHG-2026-032, CHG-2026-036 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). This change edits only text that #35 and #31 added or that this change adds, so reverting it alone is clean |

## Problem
#35 (CHG-2026-036, merge commit `2a89609`) and #31 (CHG-2026-032, merge commit `8708c77`) were merged on the owner's GO "GO on all merges" (24 Oct 2026 21:39 SAST). A merge does not touch the records, so on main: no entry in `changes/CAB-DECISION.md` names this GO or these merges; the change-log rows of CHG-2026-032 and -036 still read "PR open, not merged (no merge GO)"; the CSI-036 row says "PR open, not merged"; the `Result:` lines of the CHG-2026-032 and -036 RFCs say "not merged" and "Draft, not reviewed, no GO". Two items from the Validator's review of #35 were also still in the merged text: a line that gives the trial-merge tree "33a8276b (35 rows)" as the expected result (that trial included #29, which is not merged; #31 was merged alone and gives a different tree), and a redundant "reported (reported by Scout, not stored here)".

## Change
1. `changes/CAB-DECISION.md`: a new section "2026-10-24 21:39 SAST: PRs #35 and #31 to PROD" with the quoted GO, the heads it named, per merge the merge commit, tag, tree and test count (267 passed, 61 skipped for #35; 570 passed, 61 skipped for #31), the revert commands and the revert order (measured on scratch worktrees), and what is not covered (#29, #34).
2. `itil/registers/change-log.md`: the Outcome cells of CHG-2026-032 and -036 now say merged, with PR, merge commit, time and tag; one new row for this change (CHG-2026-037 is the next free id; CHG-2026-035 exists only on PR #34's branch and is not changed here).
3. `itil/registers/csi-register.md`: the CSI-036 status text now says merged as PR #31. It stays "In progress": the nightly step and D-08 are open.
4. `Result:` lines of the CHG-2026-032 and -036 RFCs set to the merged state; the header tables and review lines are left as drafted, as CHG-2026-031 and -036 did for earlier RFCs.
5. Two wording fixes in the merged #35 text: the "same tree 33a8276b (35 rows)" sentence (in `changes/CAB-DECISION.md` and in `CHG-2026-036-cab-records.md`) now says the trial was reported, included #29, is not measured here, and that #31 alone gives tree `cbca57cb38d5735bc363ab0c343017d587319dc6` with 34 rows (measured); "reported (reported by Scout, not stored here)" becomes "reported by Scout (not stored here)".

## Not changed
Any code, data, config, `public-data/`, `STATUS.md`; the live skill file; `/workspace/publicfunds`; the nightly. **CHG-2026-030 (#29)**: it is open, awaiting the 25 Oct 2026 nightly; main has no row for it (its row is added by that PR), so nothing is set to merged. **CSI-051**: its row does not say "PR open" and the fuel.about rendering belongs to #29, so it is not changed. CHG-2026-031: its change-log row and `Result:` line already say merged (PR #30), so nothing to change. The dated statements in the earlier CAB section and in the CHG-2026-036 text that say #31 was "unmerged" at the time of writing are left as written; the new section supersedes them. No rows for CHG-2026-030 or -035. No review lines, no header tables.

## Data identical before/after
Yes. Only markdown under `itil/` and `changes/` changes.

## Tests
`git diff --stat origin/main` shows only markdown. `uv run pytest -q`, `THUSA_ROOT` unset, expected 570 passed, 61 skipped (unchanged from main 8708c77). `tests/test_changelog_resolver.py` reads the resolver from the CHG-2026-032 RFC; that text is not changed.

## Facts and how they were checked
Merge commits, trees and tags read from git (`git rev-parse <tag>^{commit}` and `^{tree}`; annotated tags `snapshot-2026-10-24-2140` and `-2142`); PR state from `gh pr view`; test counts from the runs made at each merge; the revert results from `git revert -m 1` on scratch worktrees of `8708c77` (#31 alone: clean, tree `18db737f1bdb8cd9f714cd4ecf1e35f358a524c2`; #35 alone: conflicts; #31 then #35: clean, tree `56bc9fe9d5acaf7443dddc06249162c2f253e1cb`); the served page and the headline from the live site after the Pages build for `8708c77`. The owner's GO is quoted as relayed by PublicFunds. **Not independently checked:** the reviewers' verdicts for the exact merged heads `4bb020b` and `883ef4b`; they are not in the repository, and the CAB section says so.

## POPIA review
Author review, independent re-check requested. Process records only; no personal information, IDs, contacts, accounts or credentials.

## Review
Four checks and popia-review by someone other than the author before merge. Merge needs the owner's quoted GO naming CHG-2026-037. None has been given.

Result: Draft, not reviewed, no GO.
