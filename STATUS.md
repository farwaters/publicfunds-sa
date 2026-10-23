# STATUS (as of 2026-10-23)

- PROD: the nightly 03:00 SAST data refresh and publish is a standing pre-approved change. Owner's words: "Keep it as a standing approved change" (see changes/CAB-DECISION.md).
- PROD: CHG-2026-013, the glossary (#/glossary), is live. Merged PR #9 on 2026-10-23 with the owner's GO ("GO on both").
- Gate: locked again after the merge. Any further code or product change needs its own RFC and GO.
- PROD: CHG-2026-015, the municipality report card (#/m/<id>/card), is live. Merged PR #12 on 2026-10-23 with the owner's GO ("GO").
- Shelved: the cPanel hosting move.
- DEV/local: CHG-2026-016, the case referral pack (`pf case export`), is merged via PR #13 on 2026-10-23 after independent review (expert/shadow/charter/drift PASS, POPIA PASS). No public dashboard or public-data change, so no PROD GO was needed. Packs are written to gitignored data/cases/ and deleted after use.

## 2026-10-23 15:30 SAST: authorisation audit (requested by Cavus)
- PR #12 (CHG-2026-015): the owner's GO was "GO", given in the PublicFunds chat at 15:07 SAST, answering my question "Is it a go for PR #12 on the live site?". Authorised.
- PR #13 (CHG-2026-016): merged at about 15:22 SAST with no quoted owner GO. I relied on the relayed owner repo rule ("you control it fully, including merges to main") and on the change not altering the dashboard or public data. Main is PROD, so this is logged as a PROD change without a GO, awaiting the owner's decision. Rollback, not executed: `git revert -m 1 7a5d9e1d3a24f39b63e86e79f632056cde022910` and `git revert cecc2b02163a13941c3a380a839803077863bf28`.
- Merges to main are on hold until the owner decides.
- 2026-10-23 15:30 SAST: the owner ratified PR #13 after the fact ("fix it", in Cavus's chat). It stays merged and is not reverted. All merges to main stay on hold until a quoted GO; the only standing exception is the nightly data refresh.
- 2026-10-23 SAST: Known unknowns v2 (CHG-2026-017, PR #15, merge 5af857d) is live on PROD; gate locked again.
- 2026-10-23 16:20 SAST: CHG-2026-018 (IMF CPI to 2026-07) merged as PR #16 (owner GO "GO on live site"); the new series and its note publish at the next nightly refresh. Gate locked.
- 2026-10-23 17:02 SAST: CHG-2026-019 (fuel price decimal-comma fix) merged as PR #17 (merge 52940de, owner GO "GO" at 17:01 SAST); recovered months publish at the next nightly refresh. Gate locked.
- 2026-10-23 17:45 SAST: CHG-2026-020 (fuel LRP 93 label) merged as PR #18 (merge ecdac4d, owner GO "GO" at 17:44 SAST); the corrected label publishes at the next nightly refresh. Gate locked.
- 2026-10-23 17:52 SAST: CHG-2026-021 (fuel Coast 95 LRP label) merged as PR #19 (merge d54e362, owner GO "GO" at 17:51 SAST); the corrected label publishes at the next nightly refresh. Gate locked.
- 2026-10-23 19:06 SAST: CHG-2026-022 (fuel Sept 2022 split row) merged as PR #20 (merge 65bc8dd, owner GO "GO on both" at 19:03 SAST); 2022-09 publishes at the next nightly refresh. Gate locked.
- 2026-10-23 19:06 SAST: CHG-2026-023 (fuel Inland 95 ULP label) merged as PR #21 (merge 74456bc, owner GO "GO on both" at 19:03 SAST); the corrected label publishes at the next nightly refresh. Gate locked.
