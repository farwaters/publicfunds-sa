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
| `sql/core_schema.sql` | Target logical schema (the implemented MVP schema is in `thusa/models/` + `thusa/staging.py`) |
| `thusa/` | **MVP pipeline (v0.1.0)**: connectors, parsers, staging, SQL models (curated, marts/coverage), detectors, DQ suite, report, CLI |
| `tests/` | pytest: unit, connectors with mock HTTP, end-to-end smoke on synthetic data, DQ suite on the real warehouse |
| `docs/releases/v0.1.0.md` | Release notes (draft) |
| `AGENTS.md`, `REVIEW.md`, `.github/` | AI-agent context, review rules, PR template, CODEOWNERS |

## Running the MVP pipeline
```bash
uv sync                                   # Python 3.13; pinned deps in uv.lock
uv run thusa run --as-of 2026-10-19       # ingest all sources -> build warehouse -> DQ gate -> dashboard
uv run thusa run --refresh                # refetch even if today's raw copies exist
uv run thusa ingest --only muni_api       # one source
uv run thusa build && uv run thusa report # rebuild from raw files only (offline)
uv run pytest -q                          # 99 tests
```
Outputs (git-ignored):
- `data/raw/<source>/<date>/…` (+ `.sha256`, `manifest.jsonl`, `runs.jsonl`)
- `data/thusa.duckdb`
- `dist/site/index.html` (dashboard), `dist/*.png` (charts and screenshots), `dist/summary.json`

Exit code 2 means a data-quality check failed and the build is not releasable.

**PPD manual drop:** put Power BI CSV exports in `data/drop/ppd/` (runbook RB-06).

**SA ID hashing key:** `THUSA_HMAC_KEY` (hex) or `~/.config/thusa/hmac.key`, created on first run with mode 0600. Never commit it.

## Not in git (by design)
- `src/` — raw research downloads from 19 Oct 2026 (~16 MB): eTenders OCDS full mirror `full.jsonl.gz` (11.7 MB, from https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz), PPD user guide PDF, PFMA SCM Instruction 10 PDF + page renders. Re-download from the URLs in the landscape report.
- `data/`, `dist/`, `*.duckdb`: generated or raw data, backed up separately (D-05). Rebuild with `uv run thusa run`.

## Status
MVP pipeline v0.1.0 on branch `feat/mvp-pipeline` (CHG-2026-002). Local only, nothing published.
- All flags are unreviewed automated indicators.
- Supplier-naming flags are `pending human review`.

