# Configuration item register (CMDB-lite)

Machine-readable CIs also live in `config/sources.yaml` (data sources) and `config/detectors.yaml` (detectors). This register covers everything, including relationships. **Never record secret values here, only where they're stored.**

| CI ID | Name | Type | Location / identifier | Owner | Depends on | Status |
|---|---|---|---|---|---|---|
| CI-001 | Thusa repo | Code repository | /workspace/publicfunds (remote: see README) | Owner | — | Active |
| CI-002 | Grok Bot computer ("box") | Host (Linux VM, 8 vCPU, 15 GiB RAM, ~120 GB free, Python 3.13; no Docker/Postgres as of 19 Oct 2026) | Grok Bot account of owner | Owner | Grok Bot platform | Active |
| CI-003 | Thusa Ops Bot | Grok Bot Bot | To be created (D-11) | Owner | CI-002 | Planned |
| CI-004 | Routine `thusa-ingest-daily` (03:00 SAST) | Scheduled job | CI-003 routines | Ops Bot | CI-002, sources | Planned |
| CI-005 | Routine `thusa-dq-weekly` (Mon 07:00 SAST) | Scheduled job | CI-003 | Ops Bot | CI-008 | Planned |
| CI-006 | Routine `thusa-release-monthly` (1st Tue 09:00 SAST, prepares release; deploy needs approval) | Scheduled job | CI-003 | Ops Bot | CI-009 | Planned |
| CI-007 | Raw snapshot store (dated + sha256, manifest.jsonl, runs.jsonl) | Storage | /workspace/publicfunds/data/raw (git-ignored; ~70 MB on 19 Oct 2026) | Ops Bot | CI-002 | Active (v0.1.0) |
| CI-008 | Warehouse `thusa.duckdb` (schemas ops/staging/curated/marts; rebuilt per run, atomic swap) | Database | /workspace/publicfunds/data/thusa.duckdb (git-ignored) | Ops Bot | CI-007, CI-090 | Active (v0.1.0) |
| CI-009 | Public host (snapshot) | Hosting | Vercel or Grok Build (D-03) | Owner | CI-001 | Planned |
| CI-010..021 | Detectors D1–D15 (MVP v0.1.0: D1 overspend vs budget, D3 restricted supplier awarded, D4 supplier concentration, D5 award-value gaps, D8 irregular-expenditure trend; re-scoped by CHG-2026-002) | Analytical rules | config/detectors.yaml, thusa/detectors.py | Owner | CI-008 | MVP five Active (unpublished); rest Planned |
| CI-030..043 | Data sources (14) | Data source / supplier | config/sources.yaml | Owner | publishers | Registered |
| CI-050 | Offsite backup target | Storage | D-05 | Owner | CI-007, CI-008 | Planned |
| CI-060 | Secrets: host deploy token, uptime monitor key, HMAC key for SA ID hashing | Secret (reference only) | HMAC key: env `THUSA_HMAC_KEY` or file `~/.config/thusa/hmac.key` (0600, outside repo; generated 19 Oct 2026). Others: Grok Bot secrets, not yet created | Owner | — | HMAC Active; others Planned |
| CI-070 | Bot skills: thusa-ingest, thusa-dq-triage, thusa-release, thusa-ask | Grok Bot skill | Private skills library | Owner | CI-003 | Planned |
| CI-080 | Upstream publisher contacts (OCPO ocpodatarequest@treasury.gov.za per Instruction 10; MM feedback@municipalmoney.gov.za) | Supplier relationship | this file | Owner | — | Recorded |
| CI-090 | Python package `thusa` v0.1.0 (connectors, parsers, staging, SQL models, detectors, DQ, report, CLI) | Application | thusa/ (repo) | Owner | CI-091 | Active (branch feat/mvp-pipeline) |
| CI-091 | Dependency lock `uv.lock` (duckdb 1.4.1, httpx 0.28.1, pdfplumber 0.11.7, pyyaml 6.0.3, jinja2 3.1.6, matplotlib 3.10.7, pytz 2025.2; dev: pytest 8.4.2) | Configuration | uv.lock, pyproject.toml | Owner | — | Active |
| CI-092 | Connectors: muni_api, etenders_ocds (bulk + API delta), rsr (PDF), ppd_payments (manual drop), nt_budget (vulekamali pages) | Integration | thusa/connectors/ | Owner | CI-030..043 | Active; PPD awaiting first drop |
| CI-093 | Coverage model `marts.coverage_cell` / `marts.coverage_entity_year` | Data product | thusa/models/marts/100_coverage.sql | Owner | CI-008 | Active |
| CI-094 | Local dashboard snapshot (static HTML + PNG) | Data product | dist/ (git-ignored) | Ops Bot | CI-008 | Active (local only) |
| CI-095 | Data-quality suite (49 checks) | Control | thusa/dq.py, tests/ | Owner | CI-008 | Active |

