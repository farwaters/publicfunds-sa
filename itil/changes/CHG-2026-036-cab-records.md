# CHG-2026-036: Record the owner's GO and the results for the merges of #30, #32 and #33 (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-24 18:46, after a review finding that no record names the owner's GO for the merges of #30, #32 and #33. **Owner GO for #35 itself (this change): none yet. No merge GO is given. Merging #35 does not retroactively approve the merges of #30, #32 or #33; it only records them** |
| Environment | DEV (docs only). Nothing is built, run or published; PROD is affected only by the merge itself (markdown under `itil/` and `changes/`) |
| Type | Standard (`itil/change-enablement.md`: "docs/copy") |
| CIs affected | `changes/CAB-DECISION.md` (one new section), `itil/registers/change-log.md` (status cells of CHG-2026-031, -033 and -034, one new row), the `Result:` line of `itil/changes/CHG-2026-031-rfc-records-wording.md`, `CHG-2026-033-by-type-n-of-n.md` and `CHG-2026-034-option-a-headline-and-wording.md`, this record |
| Linked records | PRs #30, #32 and #33; `changes/CAB-DECISION.md` |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files) |

## Problem
The last entry in `changes/CAB-DECISION.md` is the 24 Oct 2026 11:07 SAST GO ("GO on 28 and 23"). Nothing records the owner's GO of 24 Oct 2026 16:06 SAST for the merges of #30 (merge commit 6f1b992), #32 (917b8e8) and #33 (75fbd63), and the change-log rows and RFC `Result:` lines for CHG-2026-031, -033 and -034 still say the PRs are open, "Awaiting review" or "Draft, not reviewed, no GO".

## Change
1. A new section in `changes/CAB-DECISION.md`, in the file's format: the owner's quoted GO, how it was applied (to the open PRs #29 to #33 only, not as a standing GO, each only after Validator, Scout and Shipper passed its exact head), and per merge the merged head, the passed head, merge commit, time, tag, tree, test counts and revert command. It says that the merge commits did not carry the quoted GO (the message of #30 names the GO time but not the words) and that this entry records it after the fact, and that #29 and #31 are not merged (#29 only after the 25 Oct nightly).
2. Change-log: the Outcome cells of CHG-2026-031, -033 and -034 now say merged, with PR, merge commit, time and tag; one new row for this change. Rows for CHG-2026-030, -032 and -035 are not touched (not merged). No CSI row said "PR open" for these changes; CSI-053 stays Proposed.
3. `Result:` lines of the three RFCs set to the merged state with the facts above. The header tables ("Owner GO: none ...") and the review lines are left as drafted, as CHG-2026-031 did for the earlier RFCs.

## What the recorded GO is, and is not
- The owner's quote (chat, 24 Oct 2026 16:06 SAST): "GO on all merges; I can't review the code I don't know what you're doing". It was relayed by PublicFunds from the owner's chat message; the reviewers did not independently verify it.
- It predates the merged heads of #32 (`a4f99f4`, committed 16:47:16) and #33 (`bc35cd8`, committed 17:24:24), so it worked only as a blanket forward GO for the open PRs #29 to #33, applied by PublicFunds on the condition that three reviewers passed the exact head. The owner decides whether that suffices. The merged head of #30 (`bc53503`, committed 12:28:31) predates the GO.
- The quote's own words mean the GO was given without the owner reviewing the content; the independent reviewers were the check instead. The owner later endorsed that at 16:24 (chat): "this is why we have independent reviewers...".
- Reviewer verdicts are **reported** (relayed in chat), not stored in the repository. For #30 the CHG-2026-031 RFC records Validator and Scout passes only at `7b1a2aa` and `c2166ab` (re-check of the latest commit requested); the merged head was `bc53503`. Scout's popia-review is reported to have covered `bc53503`; no separate expert or charter pass by Validator at `bc53503` is recorded in the repository, and none is claimed.
- Tree ids of the merges: #30 `ffde1297b5786f53ab8bfbcef2a9b2a193e8517d`; #32 `4f04de47025b695baedc92f0200ffa018f4f118d`; #33 `56bc9fe9d5acaf7443dddc06249162c2f253e1cb`.
- #29 (CHG-2026-030) is unmerged because it waits for the 25 Oct 2026 nightly; #31 (CHG-2026-032) is unmerged because it awaits the reviewers' re-checks of its latest head and fixes.

## Not changed
Any code, data, config, `public-data/`, `STATUS.md`; the CHG-2026-031 wording patch (branch `chg-2026-031-review-wording-note` stays separate); the wording "relayed by Cavus" in CHG-2026-034; rows 030, 032 and 035.

## Data identical before/after
Yes. Only markdown under `itil/` and `changes/` changes.

## Tests
`git diff --stat origin/main` shows only markdown. `uv run pytest -q`, `THUSA_ROOT` unset, expected 267 passed, 61 skipped (unchanged from main 75fbd63).

## Facts and how they were checked
Merge commits, trees and tags read from git (`git rev-parse <tag>^{commit}` and `^{tree}`); PR heads and merge state from `gh pr view`; test counts from the runs made at each merge (196/61 for main 6f1b992 re-run in a separate worktree). **Not independently checked:** the reviewers' verdicts (Validator, Scout, Shipper per head) are reported, relayed in chat; the review reports are not in the repository, and this record says so.

## POPIA review
Author review, independent re-check requested. Process records only; no personal information, IDs, contacts, accounts or credentials.

## Review
Four checks and popia-review by someone other than the author before merge. Merge needs the owner's quoted GO naming CHG-2026-036 (PR #35). None has been given. Merging #35 does not retroactively approve #30, #32 or #33.

Result: Draft, not reviewed, no GO.
