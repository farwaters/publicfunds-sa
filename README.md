# Thusa — South African public spending, with receipts

Prototype design for the most comprehensive, honest taxpayer dashboard of SA government spending. It ingests public sources, shows **what it doesn't know**, flags exceptions with evidence, and puts benchmarks ("utilities on the glass") next to every number. It is built as a **Grok Bot-hosted app** (ADR-0001).

## Contents
| Path | What |
|---|---|
| `sa_public_funds_landscape.md` (+ `.pdf`, `.docx`) | Landscape of ~48 SA tools, coverage matrix, gap analysis, source inventory, exception ideas (19 Oct 2026) |
| `docs/design/application-design.md` (+ `.pdf`) | **Application design**: vision, personas, requirements, architecture, data model, detectors, coverage model, API, UI, security/POPIA/PAIA, roadmap, testing, engineering practices, observability, ITIL summary, open decisions |
| `docs/adr/` | Decision log (ADR-0001…0006 + template) |
| `docs/research/discoveringai-reposts.md` | The @DiscoveringAI reposts on going beyond vibe coding, and the practices adopted |
| `itil/` | ITIL 4 practice map, service definition, SLA/SLO, change enablement, templates (change, incident, problem, release), registers (risk, CI, CSI, change, incident), knowledge (runbooks, KEDB) |
| `config/sources.yaml`, `config/detectors.yaml` | Machine-readable CIs: data sources and red-flag detectors |
| `sql/core_schema.sql` | Draft DuckDB schema |
| `AGENTS.md`, `REVIEW.md`, `.github/` | AI-agent context, review rules, PR template, CODEOWNERS |

## Not in git (by design)
- `src/` — raw research downloads from 19 Oct 2026 (~16 MB): eTenders OCDS full mirror `full.jsonl.gz` (11.7 MB, from https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz), PPD user guide PDF, PFMA SCM Instruction 10 PDF + page renders. Re-download from the URLs in the landscape report.
- `data/`, `dist/`, `*.duckdb`: generated or raw data, backed up separately (D-05).

## Status
Design phase. No running service yet. Next step: MVP ingestion of the Municipal Finance API + OCDS bulk + RSR, after the open decisions in design §16.

## Getting started (target: < 1 hour, once code lands)
```bash
uv sync && uv run pytest -q && uv run dbt build && uv run thusa serve
```
