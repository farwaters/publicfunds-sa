# Release checklist: REL-0.1.0 (MVP pipeline, internal/local only)

Status on 2026-10-19 10:15 SAST: **not releasable publicly**. It's ready for code review as an internal build. Items marked ✗ block a public release.

## 1. Readiness
- [ ] PR `feat/mvp-pipeline` → `main` reviewed and merged. Normal-high: 2 approvals (CHG-2026-002). Open.
- [x] Change record CHG-2026-002 linked in the release notes.
- [x] No open P1/P2 incidents. INC-2026-001 and INC-2026-002 are P4 and mitigated.
- [ ] ✗ Risk register: RSK-015 and RSK-016 are new High risks. Mitigations are in place for internal use; publication needs CSI-014.

## 2. Data gates
- [x] Sources' freshness recorded. eTenders delta is `partial` (KE-001) and PPD is awaiting a manual drop (KE-009); both are visible on the dashboard sources table.
- [x] `thusa run` exit 0: DQ 48 pass / 0 fail / 1 warn (`award_buyer_match_rate_info`, tracked as CSI-015).
- [x] `pytest`: 99 passed.
- [ ] Reconciliations within tolerance. Done: derived vs published municipal totals, 1,243/1,244 within 0.5%. **Not yet**: AGSA UIF&W totals; OCDS counts vs portal headline. (CSI-013)
- [x] Coverage model built. This is the first release, so there's no diff.
- [ ] ✗ Every flag naming a supplier or person is `reviewed`. Currently 1 D3 and 34 D4 flags are `pending human review`.
- [x] No SA ID numbers in curated or marts (DQ `popia_*` pass; e2e scan pass).

## 3. Build & verify
- [x] Manifest: `dist/summary.json` (build id, git commit, row counts, flags, DQ). Raw checksums are in `ops.raw_file`.
- [x] Local preview: `dist/site/index.html`; screenshots in `dist/`.
- [ ] Public preview (D-03 host): not started.

## 4. Deploy (production): not in scope for v0.1.0

## 5. Rollback
- Revert the merge commit; delete `data/thusa.duckdb` and `dist/`.
