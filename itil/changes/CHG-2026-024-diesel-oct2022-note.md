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
| diesel_005_inland (0.05%) | 2396.1 | 2406.0 | +9.90 |
| diesel_005_coast (0.05%) | 2330.9 | 2340.9 | +10.00 |
| petrol_93_inland | 2295.0 | 2206.0 | -89.00 |
| petrol_95_inland | 2338.0 | 2236.0 | -102.00 |
| petrol_95_coast | 2273.0 | 2171.0 | -102.00 |

- SAnews, "Reprieve at petrol pumps", 4 Oct 2022 (https://www.sanews.gov.za/south-africa/reprieve-petrol-pumps-0):
  93 ULP & LRP down 89c, 95 ULP & LRP down R1.02, diesel 0.05% up 10c; 95 ULP Gauteng 23.38 -> R22.36 (matches column 3).
- Inland diesel: 2396.10 + 10 = 2406.10 implied; DMPR prints 2406.00. Coast moves exactly +10.00. Likely a printing slip.
- The 93/95 split is official (article). The reason (octane gap reset each quarter) is not stated in the article: unverified.

## Change
- New KE-014 row in the KEDB stating the above; DMPR's figure is kept as printed (2406.00), PublicFunds does not correct data.
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
