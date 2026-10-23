# CHG-2026-020: Fuel grade label: name the DMPR "Leaded Replacement Petrol" 93 inland column correctly

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~17:10 ("GO on next"): DEV build of the next eligible item |
| Environment | DEV only (branch `feat/fuel-label` from origin/main a063856; PR open, not merged, nothing pushed to main) |
| Type | **Normal** (public label/note text changes at the next nightly refresh after a merge; no figures change) |
| CIs affected | `thusa/parsers.py` (FUEL_GRADES label), `thusa/publish_data.py` (prices.fuel.about note), `tests/test_publish_data.py`, this record, `itil/registers/change-log.md` |
| Linked records | Reviewer finding on CHG-2026-019; KE-012; CHG-2026-006/009 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the next nightly export restores the old label (git is the rollback; no .bkp files) |

## Why this item
Candidates: CSI-036 uptime/freshness monitor (24), CSI-037 Census 2022 population (24, licence check pending), and a
reviewer-found correctness defect. A wrong label on public official data misleads taxpayers today and is a one-line,
verifiable fix against raw files already on disk, so it goes first; CSI-036/037 stay next.

## Evidence (raw files in data/raw/dmpr_fuel/, read 2026-10-23)
- Every yearly `Fuel-Price-History.pdf` 2019-2025 heads the Petrol block with two sub-groups: "Leaded Replacement Petrol"
  over the first column (Inland 93) and "Unleaded" over Coast 95 / Inland 95.
- The October 2026 ZIP's "History of Fuel Prices" DOCX has the same heading.
- The October 2026 "Breakdown of Prices" DOCX gives one price for "93 ULP & LRP" inland: 2988.00 c/l, equal to the
  history table's October 2026 column-1 value. So for that month the LRP column is also the ULP 93 inland price.
- Not shown by any loaded document: that LRP and ULP 93 shared a price in every earlier month. Stated as unknown.

## Change
- Label `petrol_93_inland`: "Petrol 93, inland" -> "Petrol 93 inland (Leaded Replacement Petrol column)". Grade id unchanged
  (no schema change, no data change).
- One plain-language line added to `prices.fuel.about` with the evidence above and the unknown.
- `public-data/` is not edited by hand; the nightly export picks up the new text after a merge.

## Tests
- `pytest`: 161 passed, 60 skipped.
- `scripts/dashboard_check.py` against a local, uncommitted copy of prices.json carrying the new label: problems [].

## POPIA review
PASS. Diff and record contain no personal information, IDs, contacts, accounts, credentials or supplier names; only
official DMPR grade headings and prices.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; awaiting review.
