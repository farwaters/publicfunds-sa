# CHG-2026-024: Known-error note KE-014: DMPR October 2022 inland diesel figure

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~21:06: docs-only known-error note |
| Environment | Built and tested in DEV (branch `chg-2026-024-diesel-oct2022-note` from origin/main da29dbc; PR open, not merged, nothing pushed to main); released to PROD only through the nightly publish after the owner's merge GO: the manifest `known_errors` gains KE-014 at the next nightly. One GO binds one RFC and one environment |
| Type | **Standard** (documentation only; no code and no data change; the KE-014 symptom reaches the published manifest `known_errors` at the next nightly, nothing in `public-data/` is edited by hand) |
| CIs affected | `itil/knowledge/known-errors.md` (KE-014 added), `itil/registers/change-log.md`, this record |
| Linked records | KE-012; CHG-2026-022 (PR #20, 2022-09 row recovered); CHG-2026-029 (PR #27) points to KE-014 in its public `known_gaps` text, so this PR must merge before or with #27 |
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
- The published part is only the first cell of the row (`_known_errors()` in `thusa/publish_data.py` keeps the first 280 characters). The first version of the symptom was 281+ characters and was cut mid-sentence ("... gives Gauteng dies…"). The symptom is now one sentence of 261 characters with the key statement first (printed 2406.00; DMRE says 2,406.100); the URLs, the coast figures and the 93/95 split moved, unchanged, into the cause column (not published). Real `_known_errors()` output (worktree first on sys.path, `thusa.__file__` = /tmp/chg024/thusa/__init__.py), `known_errors[KE-014].symptom`, 261 characters, no ellipsis:
  > DMPR's 2022 history PDF prints October 2022 inland diesel 0.05% as 2406.00 c/l (September 2396.10; official change +10c); DMRE's 30 Sep 2022 statement (Annexure 1) gives Gauteng diesel 0.05% as 2,406.100 c/l, so DMPR's table is 0.10 c/l below DMRE's own figure.
- Change-log line. No code, tests, parser or `public-data/` change by hand.

## Manifest effect and PROD publish
At the first nightly after a merge (`thusa run`, then `scripts/publish-public-data.sh`, which commits and pushes `public-data/` to origin/main, served by GitHub Pages), `manifest.json` `known_errors` gains the KE-014 entry (id and symptom above) and `generated_at_sast` changes. No data file changes. The merge GO must quote CHG-2026-024 and name the PROD publish at the next nightly. Merge order with the stack: this PR before or with PR #27 (CHG-2026-029), whose public text says "see the known error KE-014".

## Data identical before/after
Fingerprint = `sha256(json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])))`, first 16 hex,
over every `data/raw/dmpr_fuel/*/*.pdf` parsed with `fuel_history_pdf_rows(blob, os.path.basename(path))` (as in
CHG-2026-022/023): before `80bc13d78db54047`, after `80bc13d78db54047`, 581 rows (docs only).

## Tests
- `pytest`: 166 passed, 60 skipped (worktree on PYTHONPATH; the shared venv otherwise imports the older /workspace/publicfunds checkout, which gives 539 rows / `89c020f2bb3f1f82`).
- `scripts/dashboard_check.py`: problems [].
- Re-run 2026-10-24 ~09:35 SAST after the symptom rearrangement and RFC wording (docs only): `pytest` 166 passed, 60 skipped; PDF fingerprint 581 rows `80bc13d78db54047`; dashboard check problems []; `_known_errors()` KE-014 symptom 261 characters, uncut.

## POPIA review
PASS. Record contains no personal information, IDs, contacts, accounts, credentials or supplier names; only official
DMPR prices and a government news source.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO for CHG-2026-024 naming the PROD publish at the next nightly.

Result: DEV build succeeded; awaiting review.
