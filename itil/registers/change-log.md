# Change log
| ID | Date (SAST) | Type | Summary | PR/commit | Outcome |
|---|---|---|---|---|---|
| CHG-2026-001 | 2026-10-19 | Standard | Initialise repo with landscape report, design, ITIL artefacts, ADRs | initial commits | Successful |
| CHG-2026-002 | 2026-10-19 | Normal-high | MVP data pipeline, coverage model, detectors D1/D3/D4/D5/D8, local dashboard (v0.1.0) — itil/changes/CHG-2026-002-mvp-pipeline.md | branch feat/mvp-pipeline → [PR #1](https://github.com/farwaters/publicfunds-sa/pull/1) (unmerged) | Awaiting review |
| CHG-2026-003 | 2026-10-19 | Normal-high | Review app: flag review queue with four-eyes, append-only audit trail, reviewer auth, coverage browser, `pf` CLI for the bot, public snapshot = confirmed flags only (v0.2.0) — itil/changes/CHG-2026-003-review-app.md. Amended 11:21 SAST: Grok Bot template distribution, ADR-0009 (D-03/D-14 superseded) | branch feat/review-app, stacked on feat/mvp-pipeline (PR base feat/mvp-pipeline, unmerged) | Awaiting review |
| CHG-2026-004 | 2026-10-19 | Normal-high (retrospective record) | Repository visibility changed to **public** by the owner (~11:21 SAST) after scanning the full history for secrets (clean) — itil/changes/CHG-2026-004-repo-public.md | GitHub settings (no commit) | Successful |
| CHG-2026-005 | 2026-10-19 | Normal-high | Template packaging: 5 bot skills, template description + memory facts, `scripts/bootstrap.sh`; D-12 Parked — itil/changes/CHG-2026-005-template-packaging.md | branch feat/review-app ([PR #2](https://github.com/farwaters/publicfunds-sa/pull/2), unmerged) | Awaiting review |
| CHG-2026-006 | 2026-10-19 | Normal-high | Public dashboard via Grok Build: `pf publish-data` public JSON export (`public-data/v1`), single-file SPA `apps/public-dashboard/`, Grok Build prompt, DMPR fuel + OECD CPI price benchmarks, refresh skill publishes data; ADR-0010 — itil/changes/CHG-2026-006-public-dashboard.md | [PR #3](https://github.com/farwaters/publicfunds-sa/pull/3), merge 2eaedb7 | **Merged 19 Oct 2026 20:29 SAST** (owner override, see note) |
| CHG-2026-007 | 2026-10-19 | Normal-high | Public dashboard on GitHub Pages (branch `main` /, root redirect, same-origin data with raw fallback; workflow deploy blocked by token scope); Grok Build deferred by owner; ADR-0011 — itil/changes/CHG-2026-007-github-pages.md | main (owner-approved direct push, 20:30 SAST) | Implemented |
| CHG-2026-008 | 2026-10-19 | Normal | Public dashboard quick wins: social cards, What's new page + `changes.json` + JSON Feed, report-an-error issue form, known-unknowns per province, accessibility/CLS fixes, axe in dashboard_check; improvement backlog — itil/changes/CHG-2026-008-quick-wins.md | branch feat/improvements-2026-10 (PR, unmerged) | Awaiting review |

**CHG-2026-001 update (19 Oct 2026):** the local repo is committed (6 commits on `main`). The remote is **not yet created**:
- `gh` is not logged in.
- Origin `create_repository` was refused ("Attenuated sessions cannot create repositories with an ensured personal Origin namespace").
- No git credential helper is configured.

Next step: the owner runs `gh auth login` (or connects GitHub), then creates the private `publicfunds-sa` repo and runs `git push -u origin main` once. Tracked as D-02.

**CHG-2026-001 closed (19 Oct 2026, 09:16 SAST):** GitHub sign-in completed as `farwaters`; private remote created at https://github.com/farwaters/publicfunds-sa and `main` pushed. Open decision D-02 resolved.

**Owner override (19 Oct 2026, 11:43 SAST):** PR #1 and PR #2 merged to `main` with owner approval only; the two-approval rule for Normal-high changes (CHG-2026-002, CHG-2026-003) was waived because the second reviewer (D-12) is parked. Reason: the PublicFunds Bot template installs from `main`.

**D-15 resolved (19 Oct 2026, 11:47 SAST):** PublicFunds Bot template published at https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi; placeholder replaced in docs (CHG-2026-005).

**Owner override (19 Oct 2026, 20:29 SAST):** PR #3 (CHG-2026-006) merged to `main` with owner approval only ("Yes, merge PR #3 and refresh the public data"); the two-approval rule for Normal-high changes was waived because the second reviewer (D-12) is parked. The same approval authorised one push of the refreshed `public-data/` via `scripts/publish-public-data.sh --push`.
| CHG-2026-010 | 2026-10-20 | Normal-high | Award-pattern detectors naming suppliers: D16 repeat awards, D17 just below MFMA/PFMA bidding threshold (cited), D6 splitting; review queue only, never published — itil/changes/CHG-2026-010-award-pattern-detectors.md | branch feat/supplier-detectors | Pending owner merge |
