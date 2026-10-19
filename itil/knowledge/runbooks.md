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

## RB-06 Procurement Payments Dashboard manual drop (PPD / BAS + LOGIS)
The PPD is a Power BI report on https://data.etenders.gov.za/. As of 19 Oct 2026 there's no documented scriptable download, so we
don't automate the Power BI session (D-07).
1. Open the Procurement Payments Dashboard in a normal browser and choose the period. Export the transaction list visual as CSV
   ("Export data" → CSV). The user guide (Feb 2026) names the file `Procurement_Spend_Transaction_List.csv`.
2. Rename it to `Procurement_Spend_Transaction_List_<YYYY-MM>.csv` and save it in `data/drop/ppd/` on the box.
3. Run `uv run thusa run --only ppd_payments`. The loader copies the file into `data/raw/ppd_payments/<date>/` with a sha256.
   It maps columns by alias (department, supplier, amount, date, system). Unrecognised columns are ignored, and
   blank amounts stay unknown.
4. Check `ops.ingest_run` for status `ok` and `curated.payment` for row counts. If the columns weren't recognised, open a
   CSI item with the header row (don't paste supplier data into tickets).

## RB-07 Daily pipeline run (`thusa run`)
`uv run thusa run [--refresh] [--as-of YYYY-MM-DD]` does ingest (all sources) → build → DQ → report.
- Exit 0: build is releasable. Exit 2: at least one `error` DQ check failed. Don't publish; open an incident (RB-01).
- Outputs: `data/thusa.duckdb`, `dist/site/index.html`, `dist/*.png`, and `dist/summary.json` (git-ignored).
- Raw files are immutable and deduplicated by checksum. Re-runs on the same day reuse today's copies unless `--refresh`.
