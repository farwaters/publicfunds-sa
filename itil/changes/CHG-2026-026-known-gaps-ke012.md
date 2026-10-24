# CHG-2026-026: Public known-gap text KE-012 (fuel) says what is still true

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus backlog, 2026-10-24 ~08:26: fix the stale public KE-012 text. No GO to merge is given |
| Environment | DEV only (branch `chg-2026-026-known-gaps-ke012` from origin/main 15c55e7; PR open, not merged, nothing pushed to main) |
| Type | Standard (public wording only; no code, no data, no figures change) |
| CIs affected | `config/public-data.yaml` (`known_gaps`, id KE-012), `itil/knowledge/known-errors.md` (KE-012 row), `itil/registers/change-log.md`, this record |
| Linked records | KE-012; CHG-2026-019, CHG-2026-022 (months recovered); CHG-2026-018 (CPI via IMF); CHG-2026-025 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the old wording returns at the next nightly refresh (git is the rollback; no .bkp files) |

## Problem
The live manifest (`public-data/v1/manifest.json`, `known_gaps`) still says the months Nov 2021, Sep 2022, Jan, May, Oct and
Dec 2023 are missing. `thusa/publish_data.py` line 438 copies `known_gaps` verbatim from `config/public-data.yaml`;
`apps/public-dashboard/index.html` line 255 shows `g.text` on the page. CHG-2026-019 and CHG-2026-022 recovered those months.

## Evidence (read 2026-10-24 ~08:27 SAST)
- Live `https://publicfunds.grokforum.site/public-data/v1/prices.json`: 651 fuel rows = 93 periods x 7 grades (each grade 93 rows),
  first period 2019-01, last 2026-10. Of the 94 months 2019-01 to 2026-10 the only one absent is **2025-12**.
- 2025-12: the November 2025 yearly PDF has an empty December row; `.../Fuel Prices Per Zone/2025/December 2025/Fuel-Price-History.pdf`
  and `.../2026/January 2026/...` return HTTP 404 (re-checked today); the current-year DOCX covers 2026 only (CHG-2026-022 record).
  The DMPR archive's December 2025 "Breakdown of Prices" is a different table and is not mapped (CHG-2026-022): not claimed here.
- Pre-2019: `Fuel-Price-History.pdf` under `.../Fuel Prices Per Zone/<year>/December <year>/` for 2015 to 2018, and the November folders
  for 2015 to 2018, return HTTP 404 (curl, today); same finding as CHG-2026-019. 2019 to 2025 load. History therefore starts 2019-01.
- Other places that already say this (consistent, not edited): CHG-2026-019/022 records, `thusa/connectors/prices.py` line 51 comment,
  `prices.fuel.about` last line ("Only months published in the loaded DMPR history table are included (KE-012)").
- No test asserts the text: `tests/test_publish_data.py` checks only the manifest key set.

## Change
`config/public-data.yaml`, `known_gaps` id KE-012, `text`:

Before:
> Fuel prices come from the Department of Mineral and Petroleum Resources' yearly price history tables, from January 2019. A few months are missing because their figures could not be read reliably from the PDF (Nov 2021, Sep 2022, Jan, May, Oct and Dec 2023, Dec 2025); those months show as unknown.

After:
> Fuel prices come from the Department of Mineral and Petroleum Resources' yearly price history tables. Earlier yearly tables are not available from DMPR (HTTP 404), so history starts in January 2019. One month is missing: December 2025 is not in any DMPR history table we could load (the November 2025 table has an empty December row and no December 2025 history table is published at DMPR's address), so it shows as unknown.

`itil/knowledge/known-errors.md`, KE-012 row, was stale in two places and is updated minimally: adds "(HTTP 404, 24 Oct 2026), so history starts
2019-01" after "2015-2018 not at that path"; the CPI clause "the OECD CPI series used instead of Stats SA lags (last period 2025-01 ...)" now
says Stats SA CPI is read through the IMF republication since CHG-2026-018 (last period 2026-07 on 24 Oct 2026; OECD kept as fallback); the
workaround column says the fuel text is the `known_gaps` KE-012 text and the CPI text sits under KE-003. The rest of the row is unchanged.

Out of scope (mentioned, left in place, Law J): `config/sources.yaml` line 105 still says "Earlier years not loaded (KE-012)" (stale; own change).
`public-data/` is not edited by hand: the live manifest changes only at the next nightly refresh after this is merged and the refresh
runs on current origin/main (CHG-2026-025). Until then the live text stays as it is.

## Data identical before/after
Fingerprint = `sha256(json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])))`, first 16 hex, over every
`data/raw/dmpr_fuel/*/*.pdf` parsed with `fuel_history_pdf_rows(blob, os.path.basename(path))` (as in CHG-2026-022/023), run with this
worktree first on PYTHONPATH: expected and measured `80bc13d78db54047`, 581 rows, before and after (wording only).

## Tests
- `pytest` (uv venv in this worktree): 166 passed, 60 skipped.
- `config/public-data.yaml` parses; KE-012 text read back with `yaml.safe_load`.
- `scripts/dashboard_check.py`: plain `python` has no Playwright; `uv run --group screenshots python scripts/dashboard_check.py` ran: problems []
  (it reads the committed `public-data/`, so it does not show the new wording; that appears after the nightly export).

## POPIA review
PASS. Wording, URLs paths and statistics only; no personal information, IDs, contacts, accounts, credentials or supplier names.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.
PRs #22 and #23 also append a line at the end of `itil/registers/change-log.md`; this line is separate, expect a trivial conflict on whichever merges second.

Result: DEV build succeeded; awaiting review.
