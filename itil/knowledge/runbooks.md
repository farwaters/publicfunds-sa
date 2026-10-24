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
The PPD is a Power BI report on https://data.etenders.gov.za/. There's no documented scriptable download, so we don't
automate the Power BI session (D-07). A person exports the file in a normal browser. The steps follow National
Treasury's *Procurement Payments Dashboard: User Guide* (Feb 2026, sections 6–7). Updated in CHG-2026-009.

**Cadence:** quarterly, after National Treasury's update. Also do it once now, to load history.

1. **Open the dashboard.** On a computer (the guide says it isn't optimised for phones), open
   https://data.etenders.gov.za/ in Edge or Chrome and open the **Procurement Payments Dashboard**.
   - Don't download the `.pbix` file (about 1 GB).
2. **BAS payments:**
   - Go to the **Supplier Transactions** view.
   - Click the link **"Procurement_Spend_Transaction_List.csv"** and save the file.
   - Rename it `PPD_BAS_<YYYY-MM-DD>.csv`, using the export date.
3. **LOGIS quantities (needed for the fuel price check, D13):**
   - Go to the LOGIS **Transaction View**.
   - Filter **Item / commodity** to fuel (diesel, petrol, paraffin), with all years and all departments.
   - Hover over the table, click the **three dots** in its top-right corner → **Export** → **CSV**, and save.
   - Rename it `PPD_LOGIS_fuel_<YYYY-MM-DD>.csv`.
   - Power BI may cap the number of exported rows. If the file looks cut short, export one financial year at a
     time: `PPD_LOGIS_fuel_<FY>_<date>.csv`.
4. **Get the files to the box.** Send them to the bot in chat, saying they're PPD exports. The bot saves them in
   `/workspace/publicfunds/data/drop/ppd/`. Don't rename columns or edit cells; the loader keeps the file byte-for-byte,
   with its sha256.
5. **Load:** `uv run thusa ingest --only ppd_payments && uv run thusa build`, or wait for the nightly run.
6. **Check:** `data/raw/runs.jsonl` has the last `ppd_payments` entry.
   - `ok` or `unchanged`: loaded. `curated.payment` shows the rows (blank amounts and quantities stay NULL, meaning
     unknown).
   - `schema_mismatch` or `partial`: a file lacks a **department**, **supplier** or **amount** column. The error lists
     only the header names. Add the missing header spellings to `PPD_ALIASES` in `thusa/parsers.py` (a Normal change),
     or open a CSI item quoting the header row. Never paste supplier rows into tickets.
   - Notes list the columns that weren't used. D13 needs **quantity** with **unit = litres**, plus a UNSPSC code or a
     fuel word in the item description. Lines without these are not assessed.
7. **Review:** D13 flags name a supplier, so they wait in the review queue (four-eyes) and are **never published**
   (`config/publication.yaml` `never_publish`).

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

## RB-11 Public data export and public dashboard
- **Publish after a refresh**: `scripts/publish-public-data.sh` (export + commit `public-data/` only). Add `--push` only from the owner-approved routine or with the owner's go-ahead. Exit 3 = export refused (quality gate or safety scan: read `data/publish-data.json` / `.log`); exit 4 = refused to commit/push (other staged files, wrong branch, `main` moved).
- **Check**: `curl -s https://raw.githubusercontent.com/farwaters/publicfunds-sa/main/public-data/v1/manifest.json | python3 -m json.tool | head` (raw cache ~5 min). The site shows the data age; > 48 h breaches SLO-PD-1.
- **Local preview**: see `apps/public-dashboard/README.md`; `uv run --group screenshots python scripts/dashboard_check.py`.
- **Takedown** (wrong or harmful content): revert the offending `public-data/` commit and push (owner approval), or unpublish the app in Grok Build; open a P2 incident (P1 if personal data), and if personal data was exposed follow the security incident steps for RSK-021 (history and forks keep it).

## RB-12 Live site and data-age check (CHG-2026-032, SLO-PD-1)
- **Run** (read-only, standard library only, writes nothing): `python3 scripts/check_live.py`. Checks that the home page and dashboard answer, the manifest is valid and no older than 48 h (SLO-PD-1; WARN above 30 h), and three sample data files match the manifest checksums.
- **After a publish** (the nightly): `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --raw-url https://raw.githubusercontent.com/farwaters/publicfunds-sa/main/public-data/v1/manifest.json --wait 600`. Also confirms the site serves the build just pushed (waits up to 10 minutes for Pages) and agrees with the git host.
- **Exit code**: 0 = OK or WARN only; 1 = at least one `[BREACH]` line. `--json` prints the same as JSON. Exit code 2 = bad command line, nothing checked. Flags: `--site`, `--raw-url`, `--expect-local`, `--wait` (0 to 3600 s), `--poll` (1 to 600 s), `--max-age-hours`, `--warn-age-hours` (must be below max), `--sample-files`, `--retries` (0 to 10), `--retry-delay` (0 to 60 s). Only http and https URLs are accepted; redirects are followed (to http and https only); the 20 s timeout is per socket read, not a total; printed URLs have no userinfo or query string. A manifest that cannot be read or has an odd `files` entry is a `[BREACH]`, not a crash. A missing build id when comparing with the git host is a `[WARN]` (cannot confirm the same build).
- **Limits**: a default run measures the site, not raw.githubusercontent.com (the SLO's measuring point): add `--raw-url` for that. A checksum BREACH right after a publish can be Pages still deploying: re-run with `--expect-local ... --wait 600`; one that persists is real.
- **On a BREACH**: report it as a breach with the output, never as success. Do not re-run the publish blindly. Stale data: check the last refresh report, RB-11 and the data-quality gate (RSK-024). Site down or files mismatched: check GitHub Pages status and the last Pages build; takedown steps are in RB-11. Open a P2 incident if the site shows wrong data.
- **Not covered**: an external uptime check from another network every 5 minutes (D-08) is still open; this script runs from the box when called.
