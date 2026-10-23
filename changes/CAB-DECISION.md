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
