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
- Re-verified 2026-10-23 after validator finding: the October 2026 "History of Fuel Prices" DOCX table XML gives
  "Leaded Replacement Petrol" `gridSpan=2` over columns 1 and 2 (Inland 93, Coast 95) and "Unleaded" span 1 over column 3
  (Inland 95) only. The 2019-2025 yearly PDFs (text layout) show the same heading order and are consistent with that
  span. (The first version of this RFC wrongly said LRP covered column 1 only and Unleaded both 95 columns.)
- The October 2026 "Breakdown of Prices" DOCX prices ULP and LRP together for every petrol line: "93 ULP & LRP" Inland
  2988.00 and Coastal 2901.00, "95 ULP & LRP" Inland 3025.00 and Coastal 2938.00 c/l. Column 1 (2988.00) and column 2
  (2938.00) of the history table match the Inland 93 and Coast 95 lines.
- Not shown by any loaded document: that LRP and ULP 93 shared a price in every earlier month. Stated as unknown.

## Change
- Label `petrol_93_inland`: "Petrol 93, inland" -> "Leaded Replacement Petrol (LRP) 93, inland". Grade id unchanged
  (no schema change, no data change).
- One plain-language line added to `prices.fuel.about` with the evidence above and the unknown.
- Scope is column 1 only. Column 2 (`petrol_95_coast`, label "Petrol 95, coast") also sits under the LRP heading per the
  evidence above; relabelling it is a separate follow-up change, **not done here**.
- The dashboard does not render `fuel.about` (apps/public-dashboard/index.html renders only `dep.about` and `ts.about`),
  so the new note exists only in prices.json for now. Rendering it is a possible follow-up; nothing is rendered in this PR.
- `public-data/` is not edited by hand; the nightly export picks up the new text after a merge.

## Tests
- `pytest`: 161 passed, 60 skipped.
- `scripts/dashboard_check.py` against a local, uncommitted copy of prices.json carrying the new label: problems [].

## POPIA review
PASS. Diff and record contain no personal information, IDs, contacts, accounts, credentials or supplier names; only
official DMPR grade headings and prices.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; merged as PR #18 (merge commit ecdac4d, 2026-10-23 17:45 SAST) on the owner's GO quoted in `changes/CAB-DECISION.md` (section "PR #18"); Validator, Scout and popia-review PASS as recorded there.. PROD: live since the nightly publish of 2026-10-24 03:05 SAST (data commit 15c55e7); checked in `public-data/v1` on origin/main: grade label "Leaded Replacement Petrol (LRP) 93, inland".
