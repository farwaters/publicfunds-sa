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
2. CHG-2026-028 says Scout's "81 of 83" could not be reproduced. It can: 2019-01 to 2025-11 is 83 months (7 x 12 - 1), minus the two 404 months (2023-02, 2023-06) is 81 workbooks; with 2025-12 it is 84 months and 82 workbooks. The record should say that all 82 workbooks were opened and compared (Validator's sweep) and that the two numbers are two ranges.
3. CHG-2026-027's "Merge and PROD preconditions" do not name #22 and #26, although #27 (merged together with #25) names KE-014 and KE-015, which exist only in those PRs.
4. "A GO for #22-#26 or #28 does not cover this change" (CHG-2026-027) read literally excludes the PRs the owner did approve in the sequence. It should say "any other PR".

## Change
Text only, one line each unless stated:
- `Result:` line of each of the 11 RFCs: merge facts only, each checked against `changes/CAB-DECISION.md` and `gh pr view` (PR number, merge commit, merge time in SAST, where the GO and checks are quoted). PROD state only where verified: CHG-2026-019 to -023 are live (the 2026-10-24 03:05 SAST data refresh, commit 15c55e7: the recovered months and the three grade labels are in `public-data/v1` on origin/main); CHG-2026-024 to -029 are merged but **not yet published** (origin/main is still 6abd695 at 2026-10-24 11:22 SAST; the next nightly publishes them). CHG-2026-025's Result keeps "skill change applied" and adds the merge of the record (docs only).
- CHG-2026-028: the coverage paragraph (item 2 above). The statement "all 82 workbooks were opened and compared" is the Validator's report; **I did not repeat the 82-workbook sweep** and the paragraph says so. The arithmetic (83 months, two 404, 81) is mine and was checked.
- CHG-2026-027: precondition (i) now names #22 and #26 and the reason (item 3); the GO sentence says "any other PR".
- CHG-2026-029: the same GO sentence (it said "A GO for #22 to #28 does not cover this change"); same defect, same fix. This was not on Scout's list; drop it from the PR if the owner prefers the minimum.
- `itil/registers/change-log.md`: one row.

## Not changed
Any code, data, config, `public-data/`, `STATUS.md`, other RFC text. The "Owner GO: none" lines in the header tables of the merged RFCs are left as written (they record the state when the RFC was drafted; the CAB record holds the GOs). Not touched: the live skill file, `/workspace/publicfunds`, the nightly.

## Data identical before/after
Yes. Only files under `itil/` change.

## Tests
`git diff --stat` shows only `itil/` markdown; `uv run pytest -q` with `THUSA_ROOT` unset is unchanged (see Result). Facts re-checked before writing: merge commits and times from `gh pr list --state merged`; heads and GO texts from `changes/CAB-DECISION.md`; the months and labels from `public-data/v1/prices.json` on origin/main; "origin/main still 6abd695" from `git ls-remote origin main`.

## POPIA review
PASS. Process records only; no personal information, IDs, contacts, accounts or credentials.

## Review
Four checks and popia-review by someone other than the author before merge. Merge needs the owner's quoted GO for CHG-2026-031.

Result: docs-only DEV change; awaiting review. No merge GO. `uv run pytest -q`, `THUSA_ROOT` unset: 196 passed, 61 skipped (unchanged from main 6abd695). 12 files changed, all under `itil/`; no `public-data/`, code, data or config touched.
