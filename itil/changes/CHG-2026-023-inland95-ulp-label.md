# CHG-2026-023: Fuel grade label: name the DMPR "Unleaded" 95 inland column (CSI-052)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~18:42: DEV build of CSI-052 (Inland 95 label only) |
| Environment | DEV only (branch `feat/inland95-ulp` from origin/main a3c1e07; PR open, not merged, nothing pushed to main) |
| Type | **Normal** (public label/note text changes at the next nightly refresh after a merge; no figures change) |
| CIs affected | `thusa/parsers.py` (FUEL_GRADES label), `thusa/publish_data.py` (prices.fuel.about note), `tests/test_publish_data.py`, this record, `itil/registers/change-log.md`, `itil/registers/csi-register.md` |
| Linked records | CSI-052; CHG-2026-021 (PR #19); CHG-2026-020 (PR #18); KE-012 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the next nightly export restores the old label (git is the rollback; no .bkp files) |

## Evidence (raw files in data/raw/dmpr_fuel/, read 2026-10-23)
- October 2026 "History of Fuel Prices" DOCX (inside the 2026-10-19 ZIP): "Leaded Replacement Petrol" header cell has
  `gridSpan=2` (Inland93, Coast95); "Unleaded" has `gridSpan=1` and sits over the sub-header column Inland95 only.
- 2019-2025 yearly PDFs (pdfplumber word positions, page 1): "Unleaded" spans x 228-268 (2019, 2020) / 235-275
  (2021-2025) and sits over the 3rd column "Inland" (234-262 / 241-269); the next "Inland" (285+ / 292+) is under
  Diesel. Same layout in all seven years.

## Change
- Label `petrol_95_inland`: "Petrol 95, inland" -> "Unleaded Petrol (ULP) 95, inland". Grade id unchanged.
- One line in `prices.fuel.about` naming the heading, following the CHG-2026-020/021 pattern.
- Test asserts the new label. `public-data/` not edited by hand.
- Out of scope (stays open in CSI-052): the coastal 93 price in the Breakdown that the History table has no column for;
  `fuel.about` is still not rendered on the dashboard (CSI-051).

## Data identical before/after
All raw DMPR files parsed with the parser functions; fingerprint =
`sha256(json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])))`, first 16 hex, 644 rows.
The value depends on the name passed to the parser (it goes into `source_locator` for PDFs):
- basename (as in CHG-2026-021): before `2d41afb650c22d16`, after `2d41afb650c22d16`
- path relative to the repo root: before `6401e136d51074a1`, after `6401e136d51074a1`
- absolute path: before `bfb81f03f6022d42`, after `bfb81f03f6022d42`

## Tests
- `pytest`: 161 passed, 60 skipped.
- `scripts/dashboard_check.py` against a temporary local prices.json carrying the new label: problems []. File
  restored with git afterwards.

## POPIA review
PASS. Diff and record contain no personal information, IDs, contacts, accounts, credentials or supplier names; only
official DMPR grade headings.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; awaiting review.
