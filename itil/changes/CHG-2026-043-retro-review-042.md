# CHG-2026-043: Record the merge of #41 and the retro review of CHG-2026-042 (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-31 |
| Environment | DEV for build. The merge to main is PROD. Docs only. Nothing is built, run or published |
| Type | Standard. `itil/change-enablement.md` lists "Docs/copy" as Standard. This change edits only markdown records |
| CIs affected | `itil/changes/CHG-2026-042-merge-records-040-041.md` (`Result:` line, new "Retro review" section), `itil/registers/change-log.md` (CHG-2026-042 row, one new row), this record |
| Linked records | PR #41, CHG-2026-042 |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Problem
PR #41 (CHG-2026-042) is merged. The records still say "PR open, not merged". A reviewer wrote a retro review note after the merge. No record contains the note.

## Change
1. The CHG-2026-042 RFC `Result:` line gives the merge: commit `139e18c`, GitHub mergedAt 31 Oct 2026 18:26:05 SAST, tag `snapshot-2026-10-31-1826`. It quotes the owner chat GO: "merge #41 GO".
2. A new "Retro review" section in the CHG-2026-042 RFC quotes the note word for word. Source: Cassian (Build), relayed by Cavus, 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds).
3. The CHG-2026-042 change-log row gets the same facts.
4. The records say that Cassian is now the pre-merge reviewer, as relayed by Cavus.
5. A new change-log row for this change.

The quoted note:

> Reviewed after merge, head 1b8556df, FAIL as a gate. No human second reviewer. Cooling-off was not shown. Sign-off was quoted, and the reviewer did not re-check it. This note does not authorize the merge, and it does not undo it.

## Not changed
This change adds no cooling-off record. It adds no CSI row, because docs-only record changes add none. Code, data, config and `public-data/` do not change.

## Facts and how they were checked
The merge commit and the tag come from git. The mergedAt time comes from `gh pr view 41`. The owner GO and the review note are as reported to the author (PublicFunds). Reviewers did not check them independently. A reviewer note is not an owner GO.

## Testing
`git diff --stat origin/main` shows only markdown. Run `uv run pytest`. The result is in the PR.

## Risk
Low. Only record wording changes.

## POPIA review
Process records only. The names are reviewer role names. No personal information.

## How to revert
Run `git revert -m 1 <merge commit of this PR>`.

Result: PR open, not merged.
