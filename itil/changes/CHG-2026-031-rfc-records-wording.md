# CHG-2026-031: Merged RFC records: stale "Result" lines and three wording fixes (docs only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-24 11:14 (carte blanche), with Scout's three wording fixes from the CHG-2026-025 to -029 review. **Owner GO: none. No merge GO is given** |
| Environment | DEV (docs only). Nothing is built, run or published; PROD is affected only by the merge itself (markdown under `itil/`) |
| Type | Standard (`itil/change-enablement.md`: "docs/copy") |
| CIs affected | `itil/changes/CHG-2026-019` to `-029` (Result line of each), `-027` (preconditions, one sentence), `-028` (coverage paragraph), `-029` (one sentence), `itil/registers/change-log.md`, this record |
| Linked records | `changes/CAB-DECISION.md` (source of every merge fact below); PRs #17-#27 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files) |

## Problem
1. Eleven merged RFCs (CHG-2026-019 to -029, PRs #17-#27) still end with "Result: ... awaiting review", although each was reviewed and merged (the CAB record has the GO, the checks and the merge commit).
2. CHG-2026-028 says Scout's "81 of 83" could not be reproduced. It can: 2019-01 to 2025-11 is 83 months (7 x 12 - 1), minus the two 404 months (2023-02, 2023-06) is 81 workbooks; with 2025-12 it is 84 months and 82 workbooks. The record should say that 82 workbooks were opened (Validator's and Scout's independent sweeps), that 81 could be compared with the history PDFs, that 2025-12 has no PDF counterpart, and that the two numbers are two ranges.
3. CHG-2026-027's "Merge and PROD preconditions" do not name #22 and #26, although #27 (merged together with #25) names KE-014 and KE-015, which exist only in those PRs.
4. "A GO for #22-#26 or #28 does not cover this change" (CHG-2026-027) read literally excludes the PRs the owner did approve in the sequence. It should say "any other PR".

## Change
Text only, one line each unless stated:
- `Result:` line of each of the 11 RFCs: merge facts only, each checked against `changes/CAB-DECISION.md` and `gh pr view` (PR number, merge commit, merge time in SAST, where the GO and checks are quoted). PROD state only where verified: CHG-2026-019 to -023 are live (the 2026-10-24 03:05 SAST data refresh, commit 15c55e7: the recovered months and the three grade labels are in `public-data/v1` on origin/main); CHG-2026-024 to -029 are merged but **not yet published** (at 11:22 SAST on 24 Oct 2026, main was 6abd695; these lines describe the state before the nightly publish of 25 Oct 2026 and a later docs record will update them). CHG-2026-025's Result keeps "skill change applied" and adds the merge of the record (docs only).
- CHG-2026-028: the coverage paragraph (item 2 above). The sweep results (82 workbooks opened, 81 compared with the history PDFs, 2025-12 without a PDF counterpart, same 82 x 200 and 2 x 404 in Scout's sweep) are the Validator's and Scout's reports; **I did not repeat the sweeps**, and the paragraph now says plainly that Scout's sweep detail is reported by Scout and is not reproducible from the record. The arithmetic (83 months, two 404, 81) is mine and was checked.
- CHG-2026-027: precondition (i) now names #22 and #26 and the reason (item 3); the GO sentence says "any other PR".
- CHG-2026-029: the same GO sentence (it said "A GO for #22 to #28 does not cover this change"); same defect, same fix. This was not on Scout's list; drop it from the PR if the owner prefers the minimum.
- `itil/registers/change-log.md`: one row for this change, and the Status cell of CHG-2026-024 to -029 (they still read "Pending review" / "Awaiting review" / "PR open") now says Merged with the PR number and date, matching the Result lines.
- Validator and Scout passed with should-fix items at 7b1a2aa, and re-checked PASS at c2166ab. Their should-fix items from 7b1a2aa were applied in one follow-up commit (c2166ab): coverage wording in CHG-2026-028, the stray ".." in CHG-2026-019 to -023, the dated "main was 6abd695" wording, the CHG-2026-027 merge-commit sentence (7e2127c is the merge on main; 832bf5c is a merge inside #27's branch), the change-log status cells and the trailing ` |` of this row. A further small fix list at c2166ab (wording only) is applied in one more commit: the review and POPIA wording of this record and the plain statement about Scout's sweep detail in CHG-2026-028. Re-check of that commit is requested; no PASS is claimed for it until both reviewers have re-checked.

## Not changed
Any code, data, config, `public-data/`, `STATUS.md`, other RFC text. The "Owner GO: none" lines in the header tables of the merged RFCs are left as written (they record the state when the RFC was drafted; the CAB record holds the GOs). Not touched: the live skill file, `/workspace/publicfunds`, the nightly.

## Data identical before/after
Yes. Only files under `itil/` change.

## Tests
`git diff --stat` shows only `itil/` markdown; `uv run pytest -q` with `THUSA_ROOT` unset is unchanged (see Result). Facts re-checked before writing: merge commits and times from `gh pr list --state merged`; heads and GO texts from `changes/CAB-DECISION.md`; the months and labels from `public-data/v1/prices.json` on origin/main; "origin/main still 6abd695" from `git ls-remote origin main`.

## POPIA review
PASS by me (PublicFunds, the author), which is not an independent review. Process records only; no personal information, IDs, contacts, accounts or credentials. Independent popia-review: Scout (an independent reviewer, not the author) passed head c2166ab with no personal information found. That is a reviewer PASS, not an owner GO, and it covers c2166ab only: the delta in the follow-up commit (wording only) needs a re-check, which is requested.

## Review
Four checks and popia-review by someone other than the author before merge. Merge needs the owner's quoted GO for CHG-2026-031.

Result: merged as PR #30 (merged head bc53503, merge commit 6f1b992, 2026-10-24 16:07 SAST, tag snapshot-2026-10-24-1607, tree ffde1297b5786f53ab8bfbcef2a9b2a193e8517d); `uv run pytest -q`, `THUSA_ROOT` unset: 196 passed, 61 skipped; docs only under `itil/`, no `public-data/` change. The owner's GO and the reported checks (no Validator pass at bc53503 is recorded in the repo; see the CAB section) are recorded after the fact in `changes/CAB-DECISION.md` (section "PRs #30, #32 and #33 to PROD (recorded after the merges)"). The header table above and the review lines are left as drafted.

Review: Validator and Scout passed with should-fix items at 7b1a2aa, and re-checked PASS at c2166ab; re-check of the latest follow-up commit requested (see Change). `uv run pytest -q` re-run after the fixes: 196 passed, 61 skipped.
