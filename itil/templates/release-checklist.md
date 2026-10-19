# Release checklist — REL-YYYY.MM.N

Cadence: monthly data+code release (plus standard data refreshes in between that pass DQ).

## 1. Readiness
- [ ] All included PRs merged with green CI, AI review + security review resolved, approvals on final commits
- [ ] Change records for normal changes linked in release notes
- [ ] No open P1/P2 incidents; error-budget policy not in freeze for affected components
- [ ] Risk register reviewed; no unmitigated *High* risk tied to this release

## 2. Data gates
- [ ] All MVP sources within freshness SLO or explicitly marked stale in UI
- [ ] `uv run thusa run` exit 0: 100% `error` DQ checks pass (`ops.dq_result`); warnings reviewed (ADR-0007: plain SQL, no dbt)
- [ ] `uv run pytest -q` green (unit + e2e smoke + DQ suite on the real warehouse)
- [ ] `ops.ingest_run` reviewed: every non-`ok` source has an INC/KE record and is shown as stale/missing in coverage
- [ ] Reconciliations within tolerance (municipal UIFW vs AGSA totals; OCDS counts vs portal headline; PPD totals)
- [ ] Coverage model rebuilt; diff vs last release reviewed (new `missing`/`late` cells explained)
- [ ] Detector run complete; new flags spot-checked (≥10 or all)
- [ ] **Review gates (ADR-0008):** the public snapshot (`dist/public/flags.json`) contains only `confirmed` flags whose evidence is unchanged; every named-supplier flag in it has two distinct confirmers (`pf review export`); `config/publication.yaml` is unchanged since the last release, or its change has a Normal-high CHG record
- [ ] `uv run pf review verify` → `ok: true`; record the **audit-chain head hash and decision count** in the release record
- [ ] Reviewer list checked (`pf reviewer list`): no shared or duplicate-person accounts, leavers disabled (RSK-017)
- [ ] Review DB backed up with the warehouse (RB-10)
- [ ] No SA ID numbers or other prohibited fields in public marts (automated scan: DQ `popia_*`, e2e column scan)
- [ ] Detector config version bumped for any threshold change; CHG record links before/after flag counts

## 3. Build & verify (preview)
- [ ] Tag `rel-YYYY.MM.N`; build static snapshot from tag
- [ ] Release manifest written: git commit, snapshot ids per source, detector versions, build time (UTC+SAST)
- [ ] Deploy to **preview** URL; Playwright E2E pass; Lighthouse ×3 median recorded; security headers check
- [ ] Review app (if changed): `/healthz` ok; screenshots of queue, one flag detail and coverage (`scripts/review_screenshots.py`); still bound to localhost or behind TLS per RB-08
- [ ] Owner review of preview (screenshots of home, 1 municipality, 1 department, flags page)

## 4. Deploy (production) — needs owner approval
- [ ] Update the **PublicFunds Bot template** (ADR-0009, CI-102): instructions and skills refreshed; contents checked against docs/bot/template.md, with **no `data/`, credentials, tokens or keys** (RSK-020); share link `https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi` still valid. (D-03 public web hosting is superseded: no web deploy in the MVP)
- [ ] Smoke test from outside the box; external uptime check green
- [ ] Release notes / public changelog published; methodology updated if detectors changed

## 5. Rollback (if needed)
- [ ] Re-promote previous snapshot `REL-…` (RTO 1 h); open incident; note in change log

## 6. After
- [ ] Post-release review within 3 days; add CSI items; close change records
