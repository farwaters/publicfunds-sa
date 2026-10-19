# ADR-0002: Python 3.13 + DuckDB + dbt-duckdb + Parquet; Postgres deferred
- Status: Accepted
- Date: 2026-10-19

## Context
The box has 8 vCPU, 15 GiB RAM (shared, ~3.5 GiB free at the time of measurement), ~120 GB free disk, Python 3.13, no Docker, no Postgres. Data volumes are modest: OCDS full mirror 12 MB gz; Municipal Finance ~85m facts; PPD up to ~1 GB Power BI model.

## Decision
- DuckDB single-file warehouse with staging/curated/marts schemas.
- dbt-duckdb for transforms and tests.
- Parquet exports for public downloads.
- `uv` for dependency management with a lockfile.
- Migrations as numbered up/down SQL.

## Consequences
- (+) Zero-ops, fast analytics, easy backups (one file + Parquet).
- (−) Single-writer: ingestion and API must coordinate. The API uses a read-only copy swapped atomically per build.
- Revisit Postgres if multi-user writes (corrections, watchlists) grow; DuckDB can attach Postgres later.
