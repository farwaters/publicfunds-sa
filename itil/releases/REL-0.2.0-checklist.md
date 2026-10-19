# REL-0.2.0 checklist: review app (draft, prepared 19 Oct 2026)

Release v0.2.0 = v0.1.0 (CHG-2026-002, PR #1) + the review app (CHG-2026-003). **Not yet released:** both PRs are
unmerged, and nothing is hosted (D-03).

| Gate | Status 19 Oct 2026 (SAST) | Evidence |
|---|---|---|
| PRs merged with approvals | ✗ PR #1 and the review-app PR are open; each needs 2 approvals (Normal-high) | GitHub |
| `uv run pytest -q` | ✓ 156 passed (99 existing + 57 new) | PR description |
| `thusa build` DQ | ✓ 49 pass, 0 fail, 1 warn (build B20261019T090303Z, after the KE-011 fix) | `/tmp/build3.log` on the box; `ops.dq_result` |
| Public snapshot = confirmed only | ✓ `dist/public/flags.json` has 0 flags (no decisions yet; policy `exclude`) | `thusa report` output |
| Audit chain | ✓ `pf review verify` ok, 0 decisions | `/healthz` |
| Reviewers | ✗ only 1 (`lootty`, admin). **Four-eyes cannot complete until a second reviewer exists** (CSI-016) | `pf reviewer list` |
| Review DB backup | ✗ backup target D-05 is not decided | RB-10 |
| Exposure | ✓ localhost only (127.0.0.1:8765) | RB-08 |
| Screenshots | ✓ dist/screenshot_review_queue.png, screenshot_review_flag_detail.png, screenshot_review_coverage.png, screenshot_review_coverage_kzn_uifw.png, screenshot_review_mobile_queue.png | `scripts/review_screenshots.py` |
| Legal review before publishing named flags (D-09) | ✗ open | — |
