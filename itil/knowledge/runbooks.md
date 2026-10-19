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
4. Restore the latest `data/review/review.sqlite` backup to a scratch path and run `THUSA_REVIEW_DB=<path> uv run pf review verify`. It must report `ok: true` (RB-10).

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

## RB-08 Review app: start, stop, check, expose
The review app (`pf serve`, CI-097) reads the current warehouse (read-only) and writes reviews to
`data/review/review.sqlite` (CI-098). It binds to **127.0.0.1:8765** by default and refuses a non-loopback bind
unless you pass `--allow-remote`.

**Fresh install:** `scripts/bootstrap.sh` (CI-103) does everything below and is safe to re-run. Set `PF_PORT` and `PF_CONFIG_DIR` to run a second, isolated copy.

**Start, stop and check (no systemd on the box as of 19 Oct 2026):**
- `scripts/review-app.sh start` runs `uv sync --frozen`, starts `pf serve` detached with setsid/nohup, writes
  `data/review/serve.pid`, and waits for `/healthz`.
- `scripts/review-app.sh status | stop | restart`. The log is `data/review/serve.log`.
- Health: `curl -s http://127.0.0.1:8765/healthz` returns `{"status":"ok", "warehouse_build_id":…, "audit_chain_ok":true}`.
  HTTP 503 or `degraded` means the warehouse is missing, or the **audit hash chain is broken**. A broken chain is
  treated as a security incident: stop the app, keep a copy of the DB, and run `pf review verify`.

**With systemd --user (other hosts):** `deploy/thusa-review.service` (see the header comment). Use
`loginctl enable-linger` so the app keeps running after logout.

**After a pipeline rebuild:** no restart is needed. Every request opens the current warehouse read-only. Flags whose
evidence changed show `evidence changed` and need re-review.

**How users reach it (ADR-0009):** through the **PublicFunds Bot**.
- The bot chat is the primary UI: `pf review …`, skill `thusa-review`.
- When a visual view helps, the bot opens http://127.0.0.1:8765 in its **own box browser**, and the user watches or
  takes over through the bot's desktop and signs in there. The bot never types the password.
- Exposing the app to the internet is **not an MVP requirement** (D-14 superseded). Don't use `--allow-remote`,
  tunnels or public proxies.
- If a later phase needs remote access, that is a new Normal-high change with its own ADR. Its prerequisites:
  - a TLS reverse proxy;
  - `THUSA_REVIEW_SECURE_COOKIES=1`;
  - `THUSA_REVIEW_ALLOWED_HOSTS=<host>`;
  - `pf serve --proxy-headers --forwarded-allow-ips 127.0.0.1`.

## RB-09 Reviewer accounts: add, rotate, off-board
Run all of these in a shell on the box from the repo root. Each step writes an append-only `reviewer_event` row.
- **Add:**
  `uv run pf reviewer add <username> --display-name "Full Name" [--admin] --credentials-file ~/.config/publicfunds/<username>_credentials`
  - Writes a random 24-character password to a 0600 file and never prints it.
  - Send the file to the person over a private channel, then delete your copy.
- **API/CLI token** (for the person's own scripts, or the Grok Bot acting for them):
  `uv run pf reviewer token <username> --out ~/.config/publicfunds/review_token`. Issuing a new token replaces the old one.
- **Reset password:** `uv run pf reviewer reset-password <username> --credentials-file <path> --force`. This revokes
  the person's sessions.
- **Off-board:** `uv run pf reviewer disable <username>` (revokes sessions; the decision history is kept) and
  `uv run pf reviewer revoke-token <username>`.
- **List:** `uv run pf reviewer list`. It shows no secrets.
- **Four-eyes needs at least two active, independent reviewers.** Don't create a second account for the same person.
  The reviewer list is checked at each release (REL checklist).

## RB-10 Review data backup and restore
- **Back up** (with the warehouse and raw files, D-05):
  `sqlite3 data/review/review.sqlite ".backup data/review/backup-$(date +%F).sqlite"`, or copy the file while the
  app is stopped.
- **Restore:** stop the app, copy the backup to `data/review/review.sqlite` (mode 0600), and start the app.
  `uv run pf review verify` must report `ok: true` and the head hash recorded in the last release record.
