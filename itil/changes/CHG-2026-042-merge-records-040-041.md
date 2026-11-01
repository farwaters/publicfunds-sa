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
3. CHG-2026-041 RFC: "No review of this change exists yet" now names the reviewer heads and verdicts, as reported to the author (PublicFunds): Reviewer A `57208e9` expert conditional PASS with should-fix, charter CONDITIONAL; `572d6bb` delta EXPERT PASS, CHARTER CONDITIONAL; Reviewer B reviewer PASS at `57208e9` (full) and `572d6bb` (delta); neither fills a human slot, no GO. The CHG-2026-040 RFC review list names Reviewer A `4f8ee75`, `3b91a78`, `3536d9a` and `0300aa8` the same way; `Result:` line set to the merged state and the appendices note.
4. CHG-2026-040 RFC: `Result:` line set to the merged state (`143c1be`, 2026-10-25, tag `snapshot-2026-10-25-1755`).
5. New change-log row for this change. No new CSI row: docs-only record changes (e.g. CHG-2026-038) add none.

## Sign-off basis (review round 2)
The change-log rows and `Result:` lines of CHG-2026-040 and -041 now record the sign-off basis: the owner GOs quoted verbatim from the merge commit messages (not independently verified by reviewers). #39: "GO to merge PR #39 (CHG-2026-040, head 0300aa8e4a774562f421ebd295c68d66e9cad185) into main (PROD). I confirm the tier as Normal-high, accept [Reviewer A] and [Reviewer B] as the second reviewer, and confirm option A for X1 and BLOCK_MIN_PREVIOUS=5." #40: "Go and keep going" (a chat reply to a question naming PR #40 at head 572d6bb; the author read it as the GO for that PR and head). No human second reviewer and no 24 h cooling-off is evidenced (#39 about 54 min from open to merge, #40 about 72 min). For #39: Flag for the owner: `itil/change-enablement.md` (Rules) says "A bot approval never fills a human slot", which conflicts with accepting the bots as the second reviewer; the Normal-high second-reviewer or 24 h cooling-off requirement is not recorded as met. For #40: the GO ("Go and keep going") gave no second-reviewer basis at all. The #40 GO names no RFC by itself; it binds to PR #40 / CHG-2026-041 at head 572d6bb only through the question it answered, as recorded by the author (PublicFunds). The requirement is not recorded as met for #40 either. The stale "none recorded" wording is replaced by "see status". Also: CSI-054 status reads "Delivered (merged); acceptance on a nightly report not yet evidenced"; GitHub mergedAt times added; the CHG-2026-041 appendix header points to the Result line.

## Not changed
Code, data, config, `public-data/`, tests; the CHG-2026-040 RFC text other than its review list line (reviewer heads and verdicts) and its `Result:` line; the live skill and routine.

## Testing
`git diff --stat origin/main` shows only markdown. `uv run pytest` on the branch (result in the PR).

## Risk
Low: wording only. No published output changes.

## Facts and how they were checked
Merge commits and tags read from git (`git log`, `git tag --points-at`). **Not verifiable from the repo:** the application of appendices A and B outside the repo and the owner's approval for it, and the Reviewer A and Reviewer B reviews; these are as reported to the author (PublicFunds). A reviewer PASS is not an owner approval.

## POPIA review
Process records only; no personal information.

## How to revert
`git revert -m 1 <merge commit of this PR>`.

Result: Merged as PR #41 (merge commit `139e18c`, GitHub mergedAt 31 Oct 2026 18:26:05 SAST, tag `snapshot-2026-10-31-1826`). The owner gave the GO in chat: "merge #41 GO". This record quotes the GO. Reviewers did not check the GO independently. No cooling-off record exists. Recorded by CHG-2026-043.

## Retro review (after merge)
The reviewer wrote this note after the merge. The note is quoted word for word. Source: Reviewer D, 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds).

> Reviewed after merge, head 1b8556df, FAIL as a gate. No human second reviewer. Cooling-off was not shown. Sign-off was quoted, and the reviewer did not re-check it. This note does not authorize the merge, and it does not undo it.

This note is not an owner GO. Reviewer D is now the pre-merge reviewer, as reported to the author (PublicFunds). Recorded by CHG-2026-043.
