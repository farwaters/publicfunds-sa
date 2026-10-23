# CHG-2026-024: Known-error note KE-014: DMPR October 2022 inland diesel figure

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~21:06: docs-only known-error note |
| Environment | DEV only (branch `chg-2026-024-diesel-oct2022-note` from origin/main da29dbc; PR open, not merged, nothing pushed to main) |
| Type | **Standard** (documentation only; no code, data or public-data change) |
| CIs affected | `itil/knowledge/known-errors.md` (KE-014 added), `itil/registers/change-log.md`, this record |
| Linked records | KE-012; CHG-2026-022 (PR #20, 2022-09 row recovered) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files) |

## Evidence (raw files in data/raw/dmpr_fuel/2026-10-20/, parsed 2026-10-23 with `fuel_history_pdf_rows`)
Values in c/l, `source_locator` `fuel-price-history-2022.pdf#page1-<Mon>`:

| Grade | 2022-09 | 2022-10 | Change |
|---|---|---|---|
| diesel_005_inland (0.05%) | 2396.1 | 2406.0 | +9.90 (official +10c wholesale) |
| diesel_005_coast (0.05%) | 2330.9 | 2340.9 | +10.00 |
| petrol_93_inland | 2295.0 | 2206.0 | -89.00 |
| petrol_95_inland | 2338.0 | 2236.0 | -102.00 |
| petrol_95_coast | 2273.0 | 2171.0 | -102.00 |

- SAnews, "Reprieve at petrol pumps", 4 Oct 2022 (https://www.sanews.gov.za/south-africa/reprieve-petrol-pumps-0):
  93 ULP & LRP down 89c, 95 ULP & LRP down R1.02, diesel 0.05% up 10c; 95 ULP Gauteng 23.38 -> R22.36 (matches column 3).
- DMRE statement of 30 Sep 2022 (effective 5 Oct 2022) (https://cefgroup.co.za/wp-content/uploads/2024/08/Press-Release-30-Sept-2022-Change-05-Oct-2022.pdf): section 1 gives diesel 0.05% as +10.00 c/l wholesale;
  Annexure 1 gives Gauteng diesel 0.05% wholesale as 2,406.100 c/l. DMPR's history table (2406.00) is 0.10 c/l below
  DMRE's own figure. Data kept as printed.
- The 93/95 split is official: section 4 of the same statement says the differentials between 95 and 93 are adjusted
  at the beginning of each quarter under the BFP Working Rules; the DMPR statement of 2 July 2025 (https://www.gov.za/news/media-statements/mineral-and-petroleum-resources-announces-adjustment-fuel-prices-2-july-2025) says the
  differential is adjusted on the first Wednesday of each quarter.

## Change
- New KE-014 row in the KEDB stating the above, citing the DMRE statement (URLs only; no contact details copied); DMPR's figure is kept as printed (2406.00), PublicFunds does not correct data.
- Change-log line. No code, tests, parser or `public-data/` change.

## Data identical before/after
Fingerprint = `sha256(json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])))`, first 16 hex,
over every `data/raw/dmpr_fuel/*/*.pdf` parsed with `fuel_history_pdf_rows(blob, os.path.basename(path))` (as in
CHG-2026-022/023): before `80bc13d78db54047`, after `80bc13d78db54047`, 581 rows (docs only).

## Tests
- `pytest`: 166 passed, 60 skipped (worktree on PYTHONPATH; the shared venv otherwise imports the older /workspace/publicfunds checkout, which gives 539 rows / `89c020f2bb3f1f82`).
- `scripts/dashboard_check.py`: problems [].

## POPIA review
PASS. Record contains no personal information, IDs, contacts, accounts, credentials or supplier names; only official
DMPR prices and a government news source.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; awaiting review.
