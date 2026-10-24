# CAB decisions

## 2026-10-23 14:17 SAST: nightly refresh publish (standing change)

- Environment: PROD (https://publicfunds.grokforum.site/)
- Change: the routine "PublicFunds nightly refresh and publish" (03:00 SAST), existing data refresh only.
- Decision: GO, as a standing pre-approved change. Owner's words, relayed by Cavus: "Keep it as a standing approved change".
- Scope: data refresh and publish only, when the quality gate passes. Any code or product change to the live site still needs its own RFC and GO.
- Rollback: git history on main (revert the publish commit).

## 2026-10-23 14:23 SAST: PR #9 (CHG-2026-013 glossary) to PROD and PR #10 to main

- Decision: GO. Owner's words: "GO on both".
- Scope: PR #9 / CHG-2026-013 glossary merged to main (PROD, https://publicfunds.grokforum.site/); PR #10 (STATUS.md, this CAB decision log) merged to main.
- Rollback: git revert of each merge commit.
- Gate: locks again after the merge; further code or product changes need their own RFC and GO.

## 2026-10-23 15:07 SAST: PR #12 (CHG-2026-015 municipality report card) to PROD

- Decision: GO. Owner's words: "GO".
- Scope: PR #12 / CHG-2026-015 municipality report card (branch feat/report-card) merged to main (PROD, https://publicfunds.grokforum.site/).
- Rollback: git revert of the merge commit.
- Gate: locks again after the merge; further code or product changes need their own RFC and GO.

## 2026-10-23 15:30 SAST: PR #13 (CHG-2026-016) ratified after the fact
- Environment: PROD (main).
- Facts: PR #13 was merged at about 15:22 SAST without a quoted owner GO, so it was a PROD change made without a GO.
- Decision: ratified by the owner, "fix it" (15:30 SAST, relayed by Cavus). Keep it merged, no revert. The same quote is the GO to merge only branch docs/status-pr13-no-go.
- Rule: every merge to main needs the owner's quoted GO for that PR; the only standing exception is the nightly data refresh. The gate locks again after this merge.

## 2026-10-23 15:54 SAST: PR #15 (CHG-2026-017, Known unknowns v2) to PROD
- Environment: PROD (main).
- Decision: GO. Owner's words, quoted: "GO" (23 Oct 2026 15:54 SAST, PublicFunds chat). Covers merging PR #15 to main plus one follow-up doc commit (change-log row, STATUS line).
- Rollback: `git revert -m 1 <merge commit>` of the PR #15 merge (git history is the rollback; no .bkp files).
- Review: independent reviewer runs the four checks (expert, shadow, charter, drift) and popia-review before merge; any failure stops the merge.
- The gate locks again after this merge.

## 2026-10-23 16:09 SAST: PR #16 (CHG-2026-018, IMF CPI) to PROD
- Owner's GO: "GO on live site", given in the PublicFunds chat at 16:09 SAST in reply to "Is it a go for PR #16 on the live site?".
- Checks (TEAM-PROTOCOL): Validator gave expert PASS and charter PASS; Scout gave shadow PASS (third review, at 7e95067) and drift PASS.
- Rollback: git revert -m 1 of the merge commit. The gate locks again after the merge.

## 2026-10-23 17:01 SAST: PR #17 (CHG-2026-019, fuel decimal-comma fix) to PROD
- Owner's GO: "GO", given at 17:01 SAST on 23 Oct 2026.
- Checks (TEAM-PROTOCOL): Scout gave shadow PASS and drift PASS; Validator gave expert PASS and charter PASS; popia-review PASS.
- Rollback: `git revert -m 1 52940de` (merge commit of PR #17). The gate locks again after the merge.

## 2026-10-23 17:44 SAST: PR #18 (CHG-2026-020, fuel LRP 93 label) to PROD
- Owner's GO: "GO", given at 17:44 SAST on 23 Oct 2026.
- Checks (TEAM-PROTOCOL): Validator gave expert PASS (re-check at 969890d) and charter PASS; Scout gave shadow PASS and drift PASS; popia-review PASS.
- Rollback: `git revert -m 1 ecdac4d` (merge commit of PR #18). The gate locks again after the merge.

## 2026-10-23 17:51 SAST: PR #19 (CHG-2026-021, Coast 95 LRP label) to PROD
- Owner's GO: "GO", given at 17:51 SAST on 23 Oct 2026.
- Checks (TEAM-PROTOCOL): Validator gave expert PASS and charter PASS; Scout gave shadow PASS and drift PASS; popia-review PASS.
- Rollback: `git revert -m 1 d54e362` (merge commit of PR #19). The gate locks again after the merge.

## 2026-10-23 19:03 SAST: PR #20 (CHG-2026-022, Sept 2022 fuel row) to PROD
- Owner's GO: "GO on both", given at 19:03 SAST on 23 Oct 2026 (asked in Cavus's chat: "Merge both PublicFunds PRs to the live site?"; verified).
- Checks (TEAM-PROTOCOL): Validator gave expert PASS and charter PASS; Scout gave shadow PASS and drift PASS; popia-review PASS.
- Rollback: `git revert -m 1 65bc8dd` (merge commit of PR #20). The gate locks again after the merge.

## 2026-10-23 19:03 SAST: PR #21 (CHG-2026-023, Inland 95 ULP label) to PROD
- Owner's GO: "GO on both", given at 19:03 SAST on 23 Oct 2026 (asked in Cavus's chat: "Merge both PublicFunds PRs to the live site?"; verified).
- Checks (TEAM-PROTOCOL): Validator gave expert PASS and charter PASS; Scout gave shadow PASS and drift PASS; popia-review PASS.
- Rollback: `git revert -m 1 74456bc` (merge commit of PR #21). The gate locks again after the merge.

## 2026-10-24 10:39 SAST: PRs #22, #24, #26, #25 and #27 to PROD, in sequence
- Environment: PROD (main). The live data files change only at the next nightly publish.
- Owner's GO, quoted (24 Oct 2026 10:39 SAST): "There is no cost associated with publicfunds - it's a free service. GO on natural and logical sequence". It covers the approved sequence only: #22, then #24, then #26, then #25 and #27 together. It does not cover PR #23, which stays open and unmerged.
- Checks: Validator PASS and Scout PASS at the reviewed heads #22 df6a370, #24 d95a862, #26 8a2da10, #25 c567ba7, #27 aa6f2f0. Each PR head was confirmed to be exactly that SHA before its merge. For #24, #26 and #27 the only change after review is a merge of origin/main into the branch (conflicts in `itil/registers/change-log.md`, and `itil/knowledge/known-errors.md` for #26, resolved by keeping every row, KE-014 before KE-015); pushed heads #24 959e415, #26 e13bd12, #27 0444dfc.
- Merges (merge commits) and snapshot tags:
  - PR #22 (CHG-2026-024, KE-014): `5dac17c`, tag `snapshot-2026-10-24-1040`. Rollback: `git revert -m 1 5dac17c`.
  - PR #24 (CHG-2026-026, KE-012 known_gaps): `f6ea633`, tag `snapshot-2026-10-24-1041`. Rollback: `git revert -m 1 f6ea633`.
  - PR #26 (CHG-2026-028, KE-015): `a758e58`, tag `snapshot-2026-10-24-1042`. Rollback: `git revert -m 1 a758e58`.
  - PRs #25 (CHG-2026-027, fuel 2025-12 workbook) and #27 (CHG-2026-029, public wording) together: `7e2127c` (#25 head c567ba7 is contained; GitHub shows #25 as merged), tag `snapshot-2026-10-24-1045`. Rollback: `git revert -m 1 7e2127c`.
- Checks after the merges: pytest with THUSA_ROOT unset 166 passed, 60 skipped after #22, #24 and #26, and 196 passed, 61 skipped after #25 and #27; `scripts/dashboard_check.py` problems []; no file under `public-data/` changed in any merge; PDF fingerprint 80bc13d78db54047 over 581 rows and combined fingerprint b7f3d278d8c12246 over 588 rows (data copy; the December 2025 workbook fetched into the copy only).
- Not done: no nightly run, no publish, no change to `public-data/`. The first nightly after these merges must fetch the December 2025 workbook; verify it with the PROD checklist in the CHG-2026-027 RFC (7 rows for 2025-12, `counts.fuel_rows` 658) and report immediately if it fails.
- The gate locks again after the merge of #27. Further changes need their own RFC and GO.

## 2026-10-24 11:07 SAST: PR #28 (this CAB record) and PR #23 (CHG-2026-025) to PROD
- Environment: PROD (main).
- Owner's GO, quoted (24 Oct 2026 11:07 SAST): "GO on 28 and 23". It covers merging PR #28 and PR #23 only, in that order, and nothing else.
- Scope: PR #28 is this docs-only record; PR #23 is CHG-2026-025 (head e4d8d88, docs only: the RFC and a change-log row).
- Rollback: `git revert -m 1 <merge commit>` of each PR; the merge commits and the snapshot tags are in the git history.
- The gate locks again after the merge of #23. Further changes need their own RFC and GO.
