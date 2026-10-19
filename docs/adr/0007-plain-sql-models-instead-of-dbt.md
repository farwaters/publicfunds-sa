# ADR-0007: Plain SQL models run by a small Python runner (dbt deferred)

- Status: Accepted (MVP v0.1.0, CHG-2026-002)
- Date: 2026-10-19
- Supersedes: the dbt part of ADR-0002 (DuckDB + Python stay)

## Context
ADR-0002 chose DuckDB + dbt-duckdb + Python. Building the MVP showed that:
- Most raw inputs (paged API JSON, a PDF table, gzipped OCDS JSONL, a semicolon CSV with Excel-style
  scientific notation) need Python parsers before SQL can use them. dbt can't do that step, so Python
  orchestration is needed anyway.
- dbt-duckdb releases lag DuckDB releases. Pinning both, plus dbt-core's large dependency tree, adds
  lockfile churn and upgrade friction for the 9 models the MVP has.
- The data-quality suite has to run in-build (to gate release) and under pytest. A shared Python list of
  SQL checks (`thusa/dq.py`) does both with no second tool.

## Decision
- Models are plain DuckDB SQL files in `thusa/models/{curated,marts}/NNN_name.sql`, executed in filename
  order by `thusa/build.py`.
- The warehouse is rebuilt from raw files on every run into a temporary file, then swapped in atomically.
  Builds are deterministic and idempotent.
- Data-quality tests live in `thusa/dq.py`. They write to `ops.dq_result`; any `error` failure makes
  `thusa run` exit 2 (not releasable). The same checks run under pytest (`tests/test_dq_warehouse.py`).
- Revisit dbt when any of these happens: more than ~30 models, more than one contributor writing SQL, or a
  need for dbt docs/lineage graphs.

## Consequences
- Fewer dependencies (6 runtime packages, all pinned in `uv.lock`). Anyone with `uv` can run it.
- Model dependencies are implicit, set by filename order. Reviewers must check the order when adding models.
- No dbt docs site. Lineage is recorded per row instead (`source_id`, `source_file`, `source_sha256`,
  `fetched_at_utc`, `source_locator`) and checked by DQ (`lineage_present:*`, `lineage_resolves:*`).
