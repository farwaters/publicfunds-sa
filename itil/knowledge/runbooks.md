# Runbooks

## RB-01 Source ingestion failed
1. Check `ops.ingest_run` for the source: error_class (http_5xx, timeout, parse_error, schema_drift, blocked).
2. http_5xx / timeout: retry policy already ran (3× with jitter). Try the fallback in `config/sources.yaml`. If no fallback, mark stale; the UI banner shows automatically.
3. parse_error / schema_drift: do **not** force-load. Open a problem record; capture the raw snapshot path; adapt the parser on a branch (normal change).
4. If the source exceeds 2× its freshness SLO, open a P3 incident.

## RB-02 Wrong figure reported publicly
1. P1/P2 incident. Confirm against the raw snapshot + source page.
2. If wrong or possibly defamatory: **emergency change**, hide the figure/flag (feature flag or re-promote previous snapshot).
3. Fix root cause; add a regression test; correction log entry; right-of-reply notification if an entity was named.

## RB-03 Release
Follow `itil/templates/release-checklist.md`. The routine prepares; the owner approves production promotion.

## RB-04 Monthly restore test
1. Copy the latest backup of `thusa.duckdb` + a sample of raw snapshots to `/tmp/restore-test/`.
2. Rebuild one mart (`marts.municipal_scorecard`) from the raw files at the release tag.
3. Compare row counts and a checksum of key measures with production. Log the result in the CSI register (CSI-009).

## RB-05 Leaked secret
Emergency change: revoke/rotate at the provider, purge it from the repo history if committed (needs owner confirmation: destructive git operation), check access logs, incident record.
