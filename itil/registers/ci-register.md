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
| CI-007 | Raw snapshot store | Storage | /workspace/publicfunds/data/raw (git-ignored) | Ops Bot | CI-002 | Planned |
| CI-008 | Warehouse `thusa.duckdb` | Database | /workspace/publicfunds/data/warehouse (git-ignored) | Ops Bot | CI-007 | Planned |
| CI-009 | Public host (snapshot) | Hosting | Vercel or Grok Build (D-03) | Owner | CI-001 | Planned |
| CI-010..021 | Detectors D1–D12 | Analytical rules | config/detectors.yaml | Owner | CI-008 | D1,D3,D4,D5,D8 planned for MVP |
| CI-030..043 | Data sources (14) | Data source / supplier | config/sources.yaml | Owner | publishers | Registered |
| CI-050 | Offsite backup target | Storage | D-05 | Owner | CI-007, CI-008 | Planned |
| CI-060 | Secrets: host deploy token, uptime monitor key, HMAC pepper | Secret (reference only) | Grok Bot secrets / env at runtime, never in repo | Owner | — | Planned |
| CI-070 | Bot skills: thusa-ingest, thusa-dq-triage, thusa-release, thusa-ask | Grok Bot skill | Private skills library | Owner | CI-003 | Planned |
| CI-080 | Upstream publisher contacts (OCPO ocpodatarequest@treasury.gov.za per Instruction 10; MM feedback@municipalmoney.gov.za) | Supplier relationship | this file | Owner | — | Recorded |
