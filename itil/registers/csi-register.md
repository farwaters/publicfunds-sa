# Continual improvement register

Value 1–5, Effort 1–5; Priority = Value / Effort (higher first). Reviewed monthly.

| ID | Improvement | Source | Value | Effort | Priority | Status | Measure of success |
|---|---|---|---|---|---|---|---|
| CSI-001 | Ask OCPO for a bulk/API feed of PPD at order/invoice level + Instruction 10 public-entity data | Landscape gap §3 | 5 | 2 | 2.5 | Proposed | Feed agreed / dataset published |
| CSI-002 | Report OCDS API 500s and licence inconsistency (PDDL vs CC BY) to OCPO | Liveness test 19 Oct 2026 | 3 | 1 | 3.0 | Proposed | Acknowledged / fixed |
| CSI-003 | Ingest Treasury monthly OCDS bulk directly (registry mirror held 35,309 processes vs 70,873 awards headlined) | OCDS profile | 4 | 2 | 2.0 | Proposed | Count reconciliation within 2% |
| CSI-004 | Build detector eval set from known public cases (NW Agriculture diesel 2023, TenderWatch barred-and-paid) | P2 practice | 4 | 2 | 2.0 | Proposed | Precision ≥ 0.8 on D1/D3 |
| CSI-005 | Request Stats SA bulk/whitelist access (WAF blocks scripts) | Liveness test | 3 | 1 | 3.0 | Proposed | Automated CPI ingestion |
| CSI-006 | Partner data-sharing with TenderWatch / OCP Cardinal | Landscape §6 | 4 | 3 | 1.3 | Proposed | MoU / shared method |
| CSI-007 | Add circuit breaker: tighten review when revert/incident rate rises | P2 (gap they noted) | 3 | 2 | 1.5 | Proposed | Auto-switch implemented |
| CSI-008 | Recruit a second maintainer (bus factor > 1) | P3, RSK-013 | 4 | 3 | 1.3 | Proposed | Second person can release |
| CSI-009 | Monthly restore test automation | P1/P3 | 4 | 2 | 2.0 | Proposed | 3 consecutive passes |
| CSI-010 | Load pre-2019 municipal income & expenditure (incexp v1) once the cube's members endpoint works; extend the coverage window back to FYE 2012 for UIF&W and audit | KE-005 | 3 | 2 | 1.5 | Proposed | FYE 2012–2019 cells computed |
| CSI-011 | eTenders delta: page by 1-day windows; alert if the delta stays partial for 3 days | INC-2026-001 | 3 | 1 | 3.0 | Proposed | Delta `ok` 7 days running |
| CSI-012 | Add provincial BvA + ENE resources from vulekamali dataset pages (provincial departments into coverage) | INC-2026-002 | 4 | 2 | 2.0 | Proposed | Provincial depts in grid |
| CSI-013 | Fill 2024/25 audit opinions & UIF&W from the AGSA MFMA 2024-25 microsite until the API catches up | KE-006 | 5 | 3 | 1.7 | Proposed | 2024/25 core coverage > 75% |
| CSI-014 | Build a labelled eval set for D3/D4 (reviewed true/false positives) before any publication; report precision | RSK-016, P2 "incidents → evals" | 5 | 3 | 1.7 | Proposed | Precision measured on ≥ 50 reviewed flags |
| CSI-015 | Buyer-name matching beyond exact keys (e.g. "Ugu Disctrict Munucipality" typo); manual alias table with review | DQ warn `award_buyer_match_rate_info` | 3 | 2 | 1.5 | Proposed | Match rate of municipal buyers > 95% |
| CSI-016 | Recruit and onboard a second independent reviewer (and ideally a legal reviewer for D3), so four-eyes can complete and named flags can be published | CHG-2026-003, ADR-0008, D-12 | 5 | 2 | 2.5 | **Parked** (owner, 19 Oct 2026: no second human yet; don't raise again) | ≥ 2 active independent reviewers |
| CSI-017 | Move the test client off the deprecated `httpx`-based Starlette TestClient (Starlette warns; filtered in pytest config) once the replacement is stable | CHG-2026-003 | 2 | 1 | 2.0 | Proposed | No filtered deprecation warnings |
| CSI-018 | Report KE-011 (province code mix) to Municipal Money (feedback@municipalmoney.gov.za) | KE-011 | 1 | 1 | 1.0 | Proposed | Upstream fixed or acknowledged |
| CSI-019 | Review-time SLO (ADR-0005 open item) and queue metrics (age of oldest `pending human review`) on /healthz or a metrics page, once volumes are known | ADR-0005, CHG-2026-003 | 3 | 2 | 1.5 | Proposed | SLO in itil/sla-slo.md |
| CSI-020 | Automated secret scan before every push and in CI, now the repo is public (e.g. gitleaks pre-push hook + GitHub secret scanning/push protection) | RSK-021, CHG-2026-004 | 4 | 1 | 4.0 | Proposed | Scan runs on every push; zero findings |
| CSI-021 | Verify how Grok Bot templates package skills, memory and routines, and trim the skills to the template size cap once known | CHG-2026-005, D-15 | 3 | 1 | 3.0 | Proposed | Template imports cleanly into a fresh bot |
