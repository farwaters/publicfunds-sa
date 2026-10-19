# ADR-0004: Every fact carries provenance; missing is NULL with a coverage reason, never 0
- Status: Accepted
- Date: 2026-10-19
## Decision
- Every fact row has `source_snapshot_id` + `source_locator`.
- Money is BIGINT cents.
- A missing value is NULL, and a `coverage_cell` explains why.
- The UI never renders a missing value as R0.
## Consequences
Enables "sourced or silent" and the known-unknowns model. Slightly heavier tables.
