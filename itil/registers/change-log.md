# Change log
| ID | Date (SAST) | Type | Summary | PR/commit | Outcome |
|---|---|---|---|---|---|
| CHG-2026-001 | 2026-10-19 | Standard | Initialise repo with landscape report, design, ITIL artefacts, ADRs | initial commits | Successful |
| CHG-2026-002 | 2026-10-19 | Normal-high | MVP data pipeline, coverage model, detectors D1/D3/D4/D5/D8, local dashboard (v0.1.0) — itil/changes/CHG-2026-002-mvp-pipeline.md | branch feat/mvp-pipeline → [PR #1](https://github.com/farwaters/publicfunds-sa/pull/1) (unmerged) | Awaiting review |
| CHG-2026-003 | 2026-10-19 | Normal-high | Review app: flag review queue with four-eyes, append-only audit trail, reviewer auth, coverage browser, `pf` CLI for the bot, public snapshot = confirmed flags only (v0.2.0) — itil/changes/CHG-2026-003-review-app.md | branch feat/review-app, stacked on feat/mvp-pipeline (PR base feat/mvp-pipeline, unmerged) | Awaiting review |

**CHG-2026-001 update (19 Oct 2026):** the local repo is committed (6 commits on `main`). The remote is **not yet created**:
- `gh` is not logged in.
- Origin `create_repository` was refused ("Attenuated sessions cannot create repositories with an ensured personal Origin namespace").
- No git credential helper is configured.

Next step: the owner runs `gh auth login` (or connects GitHub), then creates the private `publicfunds-sa` repo and runs `git push -u origin main` once. Tracked as D-02.

**CHG-2026-001 closed (19 Oct 2026, 09:16 SAST):** GitHub sign-in completed as `farwaters`; private remote created at https://github.com/farwaters/publicfunds-sa and `main` pushed. Open decision D-02 resolved.
