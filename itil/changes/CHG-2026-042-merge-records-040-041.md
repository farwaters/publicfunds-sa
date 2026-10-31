# CHG-2026-042: Record the merges of #39 and #40 and update the CHG-040/041 and CSI-053/054 status (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-31 |
| Environment | DEV for build; the merge to main is PROD. Docs only: nothing is built, run or published |
| Type | Standard (`itil/change-enablement.md`: "Docs/copy"); only markdown status wording under `itil/` changes, same as CHG-2026-038 |
| CIs affected | `itil/registers/change-log.md` (CHG-2026-040 and -041 rows, one new row), `itil/registers/csi-register.md` (CSI-053 and CSI-054 status cells), review and `Result:` lines of `itil/changes/CHG-2026-041-guard-report.md`, the `Result:` line of `itil/changes/CHG-2026-040-evidence-guard.md`, this record |
| Linked records | PRs #39 and #40; CHG-2026-040, CHG-2026-041; CSI-053, CSI-054 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback) |

## Problem
PR #39 (CHG-2026-040) was merged as `143c1be` on 25 Oct 2026 (tag `snapshot-2026-10-25-1755`) and PR #40 (CHG-2026-041) as `571d2d5` on 26 Oct 2026 (tag `snapshot-2026-10-26-1728`), but the change-log, CSI register and CHG-2026-041 RFC still say both are open and not merged.

## Change
1. Change-log rows CHG-2026-040 and -041: status set to merged (merge commit, date, tag). The -041 row also records that appendices A (the live refresh skill's publish guard line) and B (the nightly routine's report line) were applied outside the repo on 26 Oct 2026 17:33 SAST with the owner's approval, as reported.
2. CSI-053 and CSI-054 status cells: delivered/merged, same facts.
3. CHG-2026-041 RFC: "No review of this change exists yet" now says Validator and Scout reviewed it, as reported to the author (PublicFunds); `Result:` line set to the merged state and the appendices note.
4. CHG-2026-040 RFC: `Result:` line set to the merged state (`143c1be`, 2026-10-25, tag `snapshot-2026-10-25-1755`).
5. New change-log row for this change. No new CSI row: docs-only record changes (e.g. CHG-2026-038) add none.

## Not changed
Code, data, config, `public-data/`, tests; the rest of the CHG-2026-040 RFC text; the live skill and routine.

## Testing
`git diff --stat origin/main` shows only markdown. `uv run pytest` on the branch (result in the PR).

## Risk
Low: wording only. No published output changes.

## Facts and how they were checked
Merge commits and tags read from git (`git log`, `git tag --points-at`). **Not verifiable from the repo:** the application of appendices A and B outside the repo and the owner's approval for it, and the Validator and Scout reviews; these are as reported to the author (PublicFunds). A reviewer PASS is not an owner approval.

## POPIA review
Process records only; no personal information.

## How to revert
`git revert -m 1 <merge commit of this PR>`.

Result: PR open, not merged.
