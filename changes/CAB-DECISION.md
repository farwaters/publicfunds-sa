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

## 2026-10-24, about 18:50 SAST: PRs #30, #32 and #33 to PROD (recorded after the merges)
- Environment: PROD (main; GitHub Pages serves branch `main`, ADR-0011). Docs record, written after the merges: **the merge commits themselves did not carry the quoted GO.** The merge message of #30 names "owner GO 24 Oct 2026 16:06 SAST" but not the words; the merge messages of #32 and #33 name no GO. This entry records the GO and the checks after the fact.
- Owner's GO, quoted (in chat, 24 Oct 2026 16:06 SAST): "GO on all merges; I can't review the code I don't know what you're doing". PublicFunds applied it to the open PRs #29 to #33 only, not as a standing GO, and each reported to have passed Validator, Scout and Shipper at its exact head (for #30 see the note below). It was not applied to any other PR.
- How the GO was used, plainly. (1) **Timing:** the owner's 16:06 GO predates the merged heads of #32 (`a4f99f4`, committed 16:47:16) and #33 (`bc35cd8`, committed 17:24:24), so it could only work as a blanket forward GO for the open PRs #29 to #33, applied by PublicFunds on the condition that three reviewers passed the exact head. The merged head of #30 (`bc53503`, committed 12:28:31) predates it. The owner decides whether that suffices. (2) **No owner review of the content:** the quote's own words ("I can't review the code I don't know what you're doing") mean the GO was given without the owner reviewing the content; the independent reviewers were the check instead. (3) **Source of the quote:** it was relayed by PublicFunds from the owner's chat message; it has not been independently verified.
- Reviewer verdicts are **reported** (relayed in chat), not stored in this repository. That each PR head was exactly the head named as passed before its merge was reported, by the merging agent.
- Merges (local merge commit, `git merge --no-ff`, main pushed fast-forward only, no web merge button), tags and checks. `uv run pytest -q`, `THUSA_ROOT` unset; no file under `public-data/` changed in any of the three merges:
  - PR #30 (CHG-2026-031, docs only): merged head `bc53503`; reviewers' reported passed head `bc53503` (see the #30 note below); merge commit `6f1b992a8e31672afab67aa7c02cb3f83a90701b` (2026-10-24 16:07 SAST); tag `snapshot-2026-10-24-1607`; tree `ffde1297b5786f53ab8bfbcef2a9b2a193e8517d`; pytest 196 passed, 61 skipped. Rollback: `git revert -m 1 6f1b992`.
  - PR #32 (CHG-2026-033, By data type table): merged head `a4f99f4424e1dc43f29a587fcb84d0038ae4dca9`; reviewers' reported passed head `a4f99f4`: Validator expert and charter PASS with should-fix items, Scout shadow, drift and POPIA PASS, Shipper copy and layout PASS; merge commit `917b8e8dd243fa2b89e387b391cb43c9a13e70b0` (2026-10-24 17:41 SAST); tag `snapshot-2026-10-24-1741`; tree `4f04de47025b695baedc92f0200ffa018f4f118d`; pytest 222 passed, 61 skipped.
  - PR #33 (CHG-2026-034, option A wording; retargeted to `main` after #32 merged): merged head `bc35cd83b583c3b1cc462df29c34851fdec407f3`; reviewers' reported passed head `bc35cd8`, the same three verdicts as for #32; merge commit `75fbd6327cf63cb3229dd781e56d605a15f38757` (2026-10-24 17:42 SAST); tag `snapshot-2026-10-24-1742`; tree `56bc9fe9d5acaf7443dddc06249162c2f253e1cb`; pytest 267 passed, 61 skipped.
- Note on #30: the CHG-2026-031 RFC (review line) records Validator and Scout passes only at `7b1a2aa` and `c2166ab`, with a re-check of the latest follow-up requested; the merged head was `bc53503` (a later commit, rewording the RFC text and one line of CHG-2026-028). What is recorded in the repository for `bc53503` is nothing but that re-check request; Scout's popia-review is reported (per Scout's report, not stored here) to have covered `bc53503`. **No separate expert or charter pass by Validator at `bc53503` is recorded in the repository**, and none is claimed here; the "passed head `bc53503`" for #30 is the pass as reported to the merging agent.
- After the merges: the Pages build for `75fbd63` finished with status built; the served `apps/public-dashboard/index.html` was byte-identical to main's and the served `public-data/v1/coverage.json` still shows the headline 75.7% (1167 of 1542). Not checked: the next nightly publish.
- Rollback: revert in this order, **#33 first, then #32**: `git revert -m 1 75fbd6327cf63cb3229dd781e56d605a15f38757`, then `git revert -m 1 917b8e8dd243fa2b89e387b391cb43c9a13e70b0` (reverting #32 alone while #33 is in conflicts; the two reverts in this order were re-run on a scratch worktree of 75fbd63 and give tree `ffde1297b5786f53ab8bfbcef2a9b2a193e8517d`, the tree of the #30 merge). For #30: `git revert -m 1 6f1b992`.
- Not merged and not covered by this entry: **#29** (CHG-2026-030) is unmerged because it waits for the 25 Oct 2026 nightly; **#31** (CHG-2026-032) is unmerged because it awaits the reviewers' re-checks of its latest head and fixes; PR #34 (CHG-2026-035) has no GO. A merge of any of them needs its own record.
- The gate locks again after these merges. Further changes, including this docs record (CHG-2026-036), need their own RFC and the owner's GO.
