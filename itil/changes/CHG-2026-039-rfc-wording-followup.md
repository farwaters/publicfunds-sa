# CHG-2026-039: Wording follow-up to the merged CHG-2026-031 RFC: who did which review check (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-25, from the backlog (wording draft of 2026-10-24, re-checked against main `26b0b61`). **Owner GO for this change (CHG-2026-039): none. No merge GO is given** |
| Environment | DEV for build. Docs only: nothing is built, run or published; PROD is affected only by the merge itself (markdown under `itil/`) |
| Type | Standard (`itil/change-enablement.md`: "docs/copy") |
| CIs affected | `itil/changes/CHG-2026-031-rfc-records-wording.md` (review and POPIA lines, one Change bullet, the Result line), `itil/registers/change-log.md` (CHG-2026-031 row, one new row), this record |
| Linked records | PR #30 (CHG-2026-031, merge `6f1b992`); `changes/CAB-DECISION.md` (note on #30); CHG-2026-030 (same wording, already merged) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). Only text in the CHG-2026-031 RFC and change-log is touched, so reverting it alone is clean |

## Problem
The merged CHG-2026-031 RFC still says "re-check of the latest follow-up commit requested" and "no PASS is claimed", although #30 merged at `bc53503`. Its review lines name no reviewer or check, and its POPIA line covers `c2166ab` only. `changes/CAB-DECISION.md` already records what is and is not recorded for `bc53503`: nothing in the repository except the re-check request, Scout's popia-review reported to cover it, and no Validator expert or charter pass. The RFC should say the same.

## Change
Text only:
1. CHG-2026-031 RFC, Change section, last bullet: names who did which check (Validator expert and charter, Scout shadow and drift), says the results are as reported to the author and not stored in the repository, that Scout's independent popia-review is reported to cover `c2166ab` and `bc53503`, and that no Validator pass at `bc53503` is recorded. The "re-check requested" sentence becomes "applied in `bc53503`, the head that was merged".
2. CHG-2026-031 RFC, POPIA review: Scout's independent popia-review at `c2166ab` and `bc53503` (as reported), each PASS covers only the head it names, no Validator popia-review is recorded, a reviewer PASS is not an owner GO.
3. CHG-2026-031 RFC, Review section and the last `Review:` line: the same attribution.
4. CHG-2026-031 RFC, Result line: "the header table above and the review lines are left as drafted" becomes "the header table above is left as drafted; the review lines were reworded afterwards by CHG-2026-039".
5. `itil/registers/change-log.md`: the CHG-2026-031 row says the sweep results are as reported by Validator and Scout, not repeated by the author, and that Scout's sweep detail is not reproducible from the record (the same statement the CHG-2026-028 RFC already makes); one new row for this change.

## Dropped from the 2026-10-24 draft (stale)
The draft had two patches. The CHG-2026-030 patch (`135f2b8`) is dropped whole: that wording is already on main (merged through PR #29, then replaced by `b2d9139` and CHG-2026-038), so applying it would re-introduce older text. The CHG-2026-031 patch is applied with two changes: it said Scout re-checked shadow and drift PASS at `bc53503` and gave Validator's results without a head; the CAB record says only Scout's popia-review is reported for `bc53503` and no Validator pass is recorded there, so the text now says that.

## Not changed
Any code, data, config, tests, `public-data/`, `STATUS.md`, `changes/CAB-DECISION.md`, other RFCs; the live skill file; `/workspace/publicfunds`; the nightly. The header table of the CHG-2026-031 RFC is left as drafted.

## Data identical before/after
Yes. Only markdown under `itil/` changes.

## Tests
`git diff --stat origin/main` shows only markdown under `itil/`. `uv run pytest -q`, `THUSA_ROOT` unset: 617 passed, 61 skipped, unchanged from main `26b0b61`.

## POPIA review
Author review, independent re-check not yet run. Process records only; no personal information, IDs, contacts, accounts or credentials.

## Review
Not yet reviewed: reviewers have not been asked and none has run. Validator does expert and charter; Scout does shadow, drift and the independent popia-review. A reviewer PASS is never an owner GO. Merge needs the owner's quoted GO naming CHG-2026-039. None has been given.

Result: Draft; unreviewed; no GO.
