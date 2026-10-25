# CHG-2026-039: Wording follow-up to the merged CHG-2026-031 RFC (who did which review check) and two stale register status cells (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-25, from the backlog (wording draft of 2026-10-24, re-checked against main `26b0b61`). **Owner GO for this change (CHG-2026-039): none. No merge GO is given** |
| Environment | DEV for build. Docs only: nothing is built, run or published; PROD is affected only by the merge itself (markdown under `itil/`) |
| Type | Standard (`itil/change-enablement.md`: "docs/copy") |
| CIs affected | `itil/changes/CHG-2026-031-rfc-records-wording.md` (review and POPIA lines, one Change bullet, the Result line), `itil/registers/change-log.md` (rows CHG-2026-031, -035, -038 and one new row), this record |
| Linked records | PR #30 (CHG-2026-031, merge `6f1b992`); PR #34 (CHG-2026-035, merge `26b0b61`); PR #37 (CHG-2026-038, merge `d1ece5d`); `changes/CAB-DECISION.md` (note on #30, unchanged by this change); CHG-2026-030 (same wording, already merged) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). Only text in the CHG-2026-031 RFC and the change log is touched, so reverting it alone is clean |

## Problem
The merged CHG-2026-031 RFC still says "re-check of the latest follow-up commit requested" and "no PASS is claimed", although #30 merged at `bc53503`. Its review lines name no reviewer or check, and its POPIA line covers `c2166ab` only. It also credits Scout's shadow/drift and popia-review on #30 as passes. Scout has since said it has no record of any shadow/drift or popia-review of #30 at `7b1a2aa`, `c2166ab` or `bc53503` (it has only a full-suite run, 196 passed and 61 skipped, and merge-order trials on base `6abd695` at `bc53503`). Those passes were reported to the author (PublicFunds) and are not stored in the repository, and the RFC must say so. `changes/CAB-DECISION.md` records no separate expert or charter pass by Validator at `bc53503`; the RFC should say the same.

Two change-log status cells are stale: CHG-2026-035 still reads "Open PR #34, awaiting the owner's GO" (merged as `26b0b61`), and CHG-2026-038 reads "PR open, not merged" (merged as `d1ece5d`).

## Change
Text only:
1. CHG-2026-031 RFC, Change section (last bullet), POPIA review, Review section and the last `Review:` line: the role split (Validator expert and charter; Scout shadow, drift and independent popia-review) is stated as reported / per the repo's role split. Each place says: "Scout's shadow/drift and popia-review at 7b1a2aa, c2166ab and bc53503 are reported to the author (PublicFunds); Scout has no record of them; not stored in the repository." Each reported pass covers only the head it names. For Validator the wording is the CAB record's own: no separate expert or charter pass by Validator at `bc53503` is recorded in the repository, beyond the reported collective pass noted in `changes/CAB-DECISION.md`. The "re-check requested" sentence becomes "applied in `bc53503`, the head that was merged".
2. `itil/registers/change-log.md`, **status cell only** of two rows, the same records-status class (merged but still shown as open): CHG-2026-035 (merged as PR #34, `26b0b61`, tag `snapshot-2026-10-25-1605`; the owner's GO of 25 Oct 2026 16:02 SAST quoted from the owner's chat message, recorded by PublicFunds, not independently verified by reviewers; Normal-high confirmed by the owner) and CHG-2026-038 (merged as PR #37, `d1ece5d`, tag `snapshot-2026-10-25-0935`; the owner's GO of 25 Oct 2026 09:33 SAST as quoted in the merge commit message, recorded by PublicFunds, not independently verified by reviewers). The description cells of those rows are not edited. The rows of PRs #29 to #36 are already merged. Every merged or stale-looking cell was checked against `gh pr list --state all`; the older rows still showing "Awaiting review" or "Pending review" (CHG-2026-002, -003, -005, -008, -014) are outside this scope and not changed.
3. CHG-2026-031 RFC, Result line: "the header table above and the review lines are left as drafted" becomes "the header table above is left as drafted; the review lines were reworded afterwards by CHG-2026-039".
4. `itil/registers/change-log.md`, CHG-2026-031 row: the sweep results are as reported to the author (PublicFunds) by Validator and Scout, not stored in the repository, not repeated by the author, and Scout's sweep detail is not reproducible from the record (the same statement the CHG-2026-028 RFC already makes). One new row for this change (kept short).

## Risk
Docs only, wording only. The risk is a wrong statement in a record, not a change in behaviour: no code, data, test, config or published file changes, and the live site is unaffected. Revert: close the PR unmerged, or after merge `git revert -m 1 <merge sha>`.

## Dropped from the 2026-10-24 draft (stale)
The draft had two patches. The CHG-2026-030 patch (`135f2b8`) is dropped whole: that wording is already on main (merged through PR #29, then replaced by `b2d9139` and CHG-2026-038), so applying it would re-introduce older text. The CHG-2026-031 patch is applied with changes: it credited Scout with shadow/drift PASS at `bc53503` and gave Validator's results without a head. `changes/CAB-DECISION.md` records only that Scout's popia-review is "reported by Scout, not stored here" and that no separate Validator expert or charter pass at `bc53503` is recorded; Scout now says it has no record of its #30 passes at all. This change records Scout's statement in the RFC and the change log; the CAB record is not edited.

## Not changed
Any code, data, config, tests, `public-data/`, `STATUS.md`, `changes/CAB-DECISION.md` (its "reported by Scout, not stored here" stays as written; it is unchanged by this change), other RFCs; the description cells of the CHG-2026-035 and -038 rows; the live skill file; `/workspace/publicfunds`; the nightly. The header table of the CHG-2026-031 RFC is left as drafted.

## Data identical before/after
Yes. Only markdown under `itil/` changes.

## Tests
`git diff --stat origin/main` shows only markdown under `itil/`. `uv run pytest -q`, `THUSA_ROOT` unset: 617 passed, 61 skipped, unchanged from main `26b0b61`.

## POPIA review
Author review, independent re-check not yet run. Process records only; no personal information, IDs, contacts, accounts or credentials.

## Review
Reviewers' reported results on PR #38, relayed to the author (PublicFunds), not stored in the repository: Validator and Scout PASS with accuracy fixes, applied in the commit after `be98cd5`; nothing here is a pass of that later commit, and no reviewer verdict is an owner GO. Per the repo's role split Validator does expert and charter; Scout does shadow, drift and the independent popia-review. Merge needs the owner's quoted GO naming CHG-2026-039. None has been given.

Result: Draft; no GO.
