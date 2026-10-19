# CHG-2026-002: MVP data pipeline, coverage model and detectors (v0.1.0)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner (approved "build the MVP data pipeline"), 2026-10-19 09:27 |
| Type | **Normal-high**: it introduces detectors whose flags name suppliers (D3, D4). Two approvals needed before any publication |
| CIs affected | CI-001 repo; CI-007 raw store; CI-008 warehouse; CI-010..021 detectors (re-scoped, see below); CI-030..043 data sources (5 MVP connectors); new CI-090..095 |
| Linked records | ADR-0007 (plain SQL, no dbt), INC-2026-001, INC-2026-002, KE-001/002/005..010, RSK-015/016, CSI-010..015 |
| PR / commit | branch `feat/mvp-pipeline` → PR to `main` (not merged; the PR link is in the PR itself) |

## What and why
This delivers the first working slice of SVC-01 behind the scenes:
- Ingestion connectors for 5 sources, writing dated, checksummed raw files.
- Raw → staging → curated → marts layers in DuckDB. Money is held as integer cents, blank stays NULL, and every row carries lineage.
- The headline **coverage model** (entity × financial year × data type → present / partial / missing / n.a.).
- MVP detectors D1, D3, D4, D5 and D8, writing an evidence-linked flags table.
- A static local dashboard with PNG charts.
- Tests and a data-quality gate.

Nothing is published. The dashboard is local, in `dist/`, which is git-ignored.

## Detector re-scope (Normal-high: changes who could be flagged)
The parent request defined the MVP set differently from design v0.1 §6.7, so `config/detectors.yaml` was changed:
- **D1** is now *overspend vs budget*. The fuel unit-price rule moves to D13, blocked until PPD/LOGIS data is dropped in.
- **D5** is now *award-value gaps*. The non-competitive share rule moves to D14.
- **D8** is now *irregular-expenditure trend*. The wider distress rules move to D15.

Thresholds are versioned (all 0.1.0). They were tuned once against real data:
- D1 uses cash operating expenditure. Non-cash items (debt impairment, depreciation and write-offs) caused most of the "overspends" in a first pass.
- D1 ratios above 200% are reported as possible source data errors (`info`), not as overspends.
- D8 needs two consecutive increases from a base of at least R1m.
- Award values above R20bn are excluded as implausible. Example: R370.8bn for one SANRAL road contract.

## Risk assessment
- **Wrong or misleading flag naming a supplier (RSK-001, RSK-016).** D3 and D4 flags are `pending human review` and `not published`. DQ checks `flags_named_supplier_pending_review` and `flags_never_published_unreviewed` block release. D3 matches on names only, because eTenders publishes no registration numbers. Its confidence is stated in every flag.
- **Personal data (RSK-002).** SA ID numbers from the RSR PDF are HMAC'd at parse time. The key is outside the repo (`~/.config/thusa/hmac.key`, mode 0600). Natural-person names never appear in flags. DQ checks `popia_*`, and an end-to-end test scans every staging, curated and marts column for the planted test ID number.
- **Source data errors read as findings (RSK-015).** Each detector explanation carries a caveat. D1 has the possible-data-error class.
- **Blast radius:** local only; no public surface.
- **Licences:** Municipal Finance API (site terms); eTenders OCDS (PDDL on the API, CC BY 4.0 on the portal — inconsistent, attribute both); Treasury RSR (public report); Vulekamali (open data). No licence-restricted sources are ingested.

## Testing (evidence)
- `uv run pytest -q`: **99 passed** (unit, connectors with mock HTTP, end-to-end smoke on synthetic data, DQ suite on the real warehouse).
- In-build DQ gate (`ops.dq_result`): **48 pass, 0 fail, 1 warn**. The warning is `award_buyer_match_rate_info`: some award rows with "municipal" in the buyer name could not be matched to a municipality.
- Real run: `uv run thusa run --refresh --as-of 2026-10-19` (see the PR description for row counts).
- Screenshots: `dist/screenshot_dashboard.png`, `dist/screenshot_muni_NW396.png`.

## Implementation plan
1. Merge the PR after review: 2 approvals because it's Normal-high (REVIEW.md checklist).
2. Create routine `thusa-ingest-daily` (CI-004) running `uv run thusa run`; it alerts on exit code 2 (D-11).
3. Public release only after the release checklist and human review of named flags (REL-0.1.0).

## How to revert
`git revert` the merge commit on `main`. Data effects are local only: delete `data/thusa.duckdb` and `dist/`. Raw files in `data/raw/` are immutable and harmless; keep them.

## Approval
| Role | Name | Commit approved | Date |
|---|---|---|---|
| Change authority | (owner) | | |
| Second reviewer (high-risk) | | | |

## Post-implementation review
- Outcome: pending merge.
- Follow-ups: CSI-010..015.
