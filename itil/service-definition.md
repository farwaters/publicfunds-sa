# Service definition & catalogue entry

## SVC-01 — Thusa Public Spending Dashboard
| Field | Value |
|---|---|
| Service ID | SVC-01 |
| Status | **Pipeline** (designed, not live) |
| Description | Free, public dashboard of South African government spending with provenance, coverage gaps ("known unknowns"), red-flag exceptions and benchmarks |
| Value proposition | Find what any public body spent, with whom, what auditors said, what looks anomalous, and what data is missing, in one place, with sources |
| Consumers | Taxpayers/residents, journalists, civil-society analysts, oversight staff (personas in design §2) |
| Service owner | The owner |
| Operator | Thusa Ops Bot (Grok Bot) under owner supervision |
| Offering | Web dashboard (read-only, no login); CSV downloads; methodology; corrections channel |
| Coverage (MVP) | 292 municipalities (Municipal Finance API), national & provincial departments (PPD/OCDS), restricted suppliers, AGSA 2024-25 outcomes, fuel & CPI benchmarks |
| Exclusions | Personal ID numbers; non-public/leaked data; legal advice; verdicts of wrongdoing |
| Hours | 24×7 availability target; operator response business hours SAST (Mon–Fri 08:00–17:00) |
| Service levels | See sla-slo.md |
| Support / requests | Corrections & objections form (phase 2); until then, owner email **[to be set; D-05]** |
| Dependencies | Grok Bot computer (box), routines, the PublicFunds Bot template (CI-102, ADR-0009; no public web host); upstream publishers (CI register) |
| Cost model | Free to users; operating cost = Grok Bot plan usage per bot (each importer runs their own) **[estimate pending]** |
| Key risks | RSK-001..RSK-012 |

## SVC-02 — Thusa Public API (phase 2)
Status: *Pipeline*. Read-only REST, rate-limited; same data as SVC-01. Availability 99.0%.

## SVC-03 — Thusa Alerts & Watchlists (phase 2)
Status: *Pipeline*. Email digests from the Bot's own inbox; first template send requires owner approval, thereafter a standard change.

## SVC-INT-01 — Ingestion & publishing (internal/supporting service)
Routines on the box; consumers = SVC-01..03. SLOs on freshness and DQ pass rate.
