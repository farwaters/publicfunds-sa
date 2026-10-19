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
| CI-060 | Secrets: host deploy token, uptime monitor key, HMAC key for SA ID hashing, review-app credentials | Secret (reference only) | HMAC key: env `THUSA_HMAC_KEY` or file `~/.config/thusa/hmac.key` (0600, outside repo; generated 19 Oct 2026). Review admin `lootty` credentials: `/home/box/.config/publicfunds/admin_credentials` (0600, created 19 Oct 2026 by CHG-2026-003). Reviewer passwords are stored as scrypt hashes and tokens/sessions as SHA-256 hashes in CI-098. Others: Grok Bot secrets, not yet created | Owner | — | HMAC + review admin Active; others Planned |
| CI-070 | Bot skills: thusa-ingest, thusa-dq-triage, thusa-release, thusa-ask, **thusa-review** (draft: docs/bot/review-skill.md) | Grok Bot skill | Private skills library | Owner | CI-003, CI-099 | Planned (thusa-review drafted) |
| CI-080 | Upstream publisher contacts (OCPO ocpodatarequest@treasury.gov.za per Instruction 10; MM feedback@municipalmoney.gov.za) | Supplier relationship | this file | Owner | — | Recorded |
| CI-090 | Python package `thusa` v0.2.0 (connectors, parsers, staging, SQL models, detectors, DQ, report, CLI; `thusa.review` and `thusa.publish` added by CHG-2026-003) | Application | thusa/ (repo) | Owner | CI-091 | Active (branches feat/mvp-pipeline, feat/review-app) |
| CI-091 | Dependency lock `uv.lock` (duckdb 1.4.1, httpx 0.28.1, pdfplumber 0.11.7, pyyaml 6.0.3, jinja2 3.1.6, matplotlib 3.10.7, pytz 2025.2, fastapi 0.146.0 (starlette 1.9.0, pydantic 2.14.1), uvicorn 0.54.0, python-multipart 0.0.32; dev: pytest 8.4.2; group `screenshots`: playwright 1.64.0). Vendored front-end asset: htmx 2.0.11 (`thusa/review/static/`, sha256 d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717) | Configuration | uv.lock, pyproject.toml | Owner | — | Active |
| CI-092 | Connectors: muni_api, etenders_ocds (bulk + API delta), rsr (PDF), ppd_payments (manual drop), nt_budget (vulekamali pages) | Integration | thusa/connectors/ | Owner | CI-030..043 | Active; PPD awaiting first drop |
| CI-093 | Coverage model `marts.coverage_cell` / `marts.coverage_entity_year` | Data product | thusa/models/marts/100_coverage.sql | Owner | CI-008 | Active |
| CI-094 | Local dashboard snapshot (static HTML + PNG), now labelled INTERNAL | Data product | dist/site, dist/*.png (git-ignored) | Ops Bot | CI-008 | Active (local only) |
| CI-095 | Data-quality suite (50 checks; `province_codes_official` added by CHG-2026-003) | Control | thusa/dq.py, tests/ | Owner | CI-008 | Active |
| CI-096 | Public static snapshot (confirmed flags only, per `config/publication.yaml`) | Data product | dist/public/ (git-ignored), built by `thusa report` / `pf publish` | Owner | CI-008, CI-098, CI-101 | Active (local; not hosted, CI-009) |
| CI-097 | Review web app `pf serve` (FastAPI + Jinja + HTMX; JSON API under /api) | Application service | box 127.0.0.1:8765; started by `scripts/review-app.sh` (PID in data/review/serve.pid) or `deploy/thusa-review.service` | Owner | CI-008, CI-098, CI-090 | Active (localhost only) |
| CI-098 | Review store `review.sqlite` (append-only, hash-chained decisions; reviewers; sessions) | Database | /workspace/publicfunds/data/review/review.sqlite (0600, git-ignored); override with `THUSA_REVIEW_DB` | Owner | — | Active; backup per RB-10 (D-05) |
| CI-099 | `pf` CLI (reviewer admin; review list/show/decide/history/verify/export; serve; publish) | Application | thusa/review/cli.py | Owner | CI-098 | Active |
| CI-100 | Reviewer accounts (`lootty`, admin, created 19 Oct 2026) | Identity | CI-098 `reviewer` table; events in `reviewer_event` | Owner | CI-098 | Active (1 of the ≥ 2 needed for four-eyes) |
| CI-101 | Publication policy `config/publication.yaml` (`flags.unconfirmed: exclude`) | Configuration | config/publication.yaml | Owner | — | Active (changing it is a Normal-high change) |
