# STATUS (as of 2026-10-23)

- PROD: the nightly 03:00 SAST data refresh and publish is a standing pre-approved change. Owner's words: "Keep it as a standing approved change" (see changes/CAB-DECISION.md).
- PROD: CHG-2026-013, the glossary (#/glossary), is live. Merged PR #9 on 2026-10-23 with the owner's GO ("GO on both").
- Gate: locked again after the merge. Any further code or product change needs its own RFC and GO.
- PROD: CHG-2026-015, the municipality report card (#/m/<id>/card), is live. Merged PR #12 on 2026-10-23 with the owner's GO ("GO").
- Shelved: the cPanel hosting move.
- DEV/local: CHG-2026-016, the case referral pack (`pf case export`), is merged via PR #13 on 2026-10-23 after independent review (expert/shadow/charter/drift PASS, POPIA PASS). No public dashboard or public-data change, so no PROD GO was needed. Packs are written to gitignored data/cases/ and deleted after use.
