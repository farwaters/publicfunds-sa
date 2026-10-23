# CHG-2026-021: Fuel grade label: name the DMPR "Leaded Replacement Petrol" 95 coast column correctly (CSI-051)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~17:46 ("GO"): DEV build of CSI-051 (label part only) |
| Environment | DEV only (branch `feat/coast95-lrp` from origin/main 4667179; PR open, not merged, nothing pushed to main) |
| Type | **Normal** (public label/note text changes at the next nightly refresh after a merge; no figures change) |
| CIs affected | `thusa/parsers.py` (FUEL_GRADES label), `thusa/publish_data.py` (prices.fuel.about note), `tests/test_publish_data.py`, this record, `itil/registers/change-log.md`, `itil/registers/csi-register.md` |
| Linked records | CSI-051; CHG-2026-020 (PR #18); KE-012 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the next nightly export restores the old label (git is the rollback; no .bkp files) |

## Evidence (raw files in data/raw/dmpr_fuel/, read 2026-10-23)
- October 2026 "History of Fuel Prices" DOCX (inside the 2026-10-19 ZIP): the "Leaded Replacement Petrol" header cell
  has `gridSpan=2` over sub-header columns Inland93 and Coast95; "Unleaded" sits over Inland95 only. October row:
  2988.00 / 2938.00 / 3025.00.
- October 2026 "Breakdown of Prices" DOCX: "95 ULP & LRP" Coastal 2938.00 c/l, equal to column 2 (Coast 95).
- 2019-2025 yearly PDFs: same heading order. Word positions (pdfplumber) checked for 2019: "Leaded Replacement Petrol"
  spans x 134-222, covering "Inland" (141-168) and "Coast" (189-213); "Unleaded" (228-268) sits over the 3rd column
  (234-262). 2025: "Leaded Replacement" 142-229, "Unleaded" from 235; same layout.
- Unknown: whether LRP 95 and ULP 95 shared a coastal price in every earlier month (no loaded document shows it).

## Change
- Label `petrol_95_coast`: "Petrol 95, coast" -> "Leaded Replacement Petrol (LRP) 95, coast". Grade id unchanged.
- One matching line in `prices.fuel.about` (evidence plus the unknown), mirroring CHG-2026-020.
- Test asserts the new label. `public-data/` not edited by hand. `fuel.about` is still **not rendered** on the
  dashboard; that is the other half of CSI-051 and stays open.

## Data identical before/after
All raw DMPR files parsed with the parser functions; fingerprint = sha256 of sorted (year, month, grade,
cents_per_litre, source_locator), first 16 hex: before `2d41afb650c22d16`, 644 rows; after `2d41afb650c22d16`, 644 rows.

## Tests
- `pytest`: 161 passed, 60 skipped.
- `scripts/dashboard_check.py` against a temporary local prices.json with both new labels (shown in the fuel select
  and table): problems []. File restored with git afterwards.

## POPIA review
PASS. Diff and record contain no personal information, IDs, contacts, accounts, credentials or supplier names; only
official DMPR grade headings and prices.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; awaiting review.
