# CHG-2026-019: Fuel price history gaps (CSI-032, part): read the publisher's decimal comma in DMPR yearly PDFs

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus, 2026-10-23 ~16:30 ("GO ahead, iterate until you've run out of design") for a DEV build of the top eligible roadmap item |
| Environment | DEV only (branch `feat/next-chg019` from origin/main a90606b; PR open, not merged, nothing pushed to main) |
| Type | **Normal** (parser change that alters public price data at the next nightly refresh after a merge) |
| CIs affected | `thusa/parsers.py` (`fuel_history_pdf_rows`, new `_decimal_comma`), `tests/test_ppd_fuel.py`, `itil/knowledge/known-errors.md` (KE-012 text), this record, `itil/registers/change-log.md` |
| Linked records | Roadmap CSI-032 (score 25), KE-012, CSI-022, CHG-2026-009 |
| Rollback | Close the PR unmerged. If ever merged: `git revert -m 1 <merge commit>`; the next nightly rebuild leaves the 5 months unknown again (git history is the rollback; no .bkp files per owner amendment) |

## Why this item
Eligible = no owner login or manual admin, no personal information, no unreviewed flags or uncleared AGSA figures, one focused PR.
Done or excluded: CSI-026 (28, owner manual PPD export), CSI-029 (26, needs PPD line items; leads hidden), CSI-030 (26, AGSA load not
cleared), CSI-027/028/031 (shipped), CSI-033/034/038 (built as D17/D16/D6, never published). Highest remaining: CSI-032 (25).
CSI-035 (25) needs legal review of wording and is multi-week. Next two eligible: CSI-036 uptime/freshness monitor (24) and
CSI-037 Census 2022 population (24, open republication and licence still to verify).

## Source feasibility (2026-10-23, SAST)
- DMPR yearly `Fuel-Price-History.pdf` for 2015-2018 at the CHG-2026-009 path (December and November folders): HTTP 404. Not loaded; stays unknown.
- The 9 unknown months in KE-012: 5 are rows where DMPR typed a decimal comma, which the parser rejected (checked against
  `pdftotext -layout` of the raw PDFs): 2021-11 `1882,00`; 2023-01 `2122,87` and `1525,958`; 2023-05 `1439,058`;
  2023-10 `2429,79`; 2023-12 `2325,00`. 2022-09 is split across lines in the PDF text; 2025-12 is not in the November 2025 PDF.

## What
- `fuel_history_pdf_rows` accepts a token of 3-4 digits, a comma and 2-3 decimals and reads the comma as the decimal point.
  This rule is not proof against thousands separators: a 3-digit group like `152,525` does match (and `123,456` would be read
  as 123.456). What keeps it harmless in these PDFs is that a row must still give exactly 7 numbers, else it is skipped, so an
  extra comma token (8 numbers) leaves the month unknown rather than taking wrong values.
- KE-012 text updated: 2 months stay unknown (2022-09, 2025-12).
- Public data is not edited in this PR; it changes at the first nightly refresh after a merge.

## Evidence (raw files already in the raw store, sha256 lineage unchanged, data/raw/dmpr_fuel/2026-10-20)
Months missing per year, before -> after: 2021 [11] -> []; 2022 [9] -> [9]; 2023 [1,5,10,12] -> []; 2025 [12] -> [12]; 2019/2020/2024 none.
Example, 2023-01 read: 2110.00 / 2075.00 / 2140.00 / 2122.87 / 2057.67 / 1446.758 / 1525.958 c/l, identical to the PDF text
(`pdftotext -layout`). No figure invented: each value is the published digit string with ',' read as '.'.

## Tests
- New `test_fuel_history_pdf_rows_read_publisher_decimal_comma` (decimal comma read; thousands-style `2,122` row still skipped).
- New `test_fuel_history_pdf_rows_skip_row_with_extra_comma_token` (a `152,525` token makes 8 numbers: row skipped, month stays unknown).
- Full suite: 161 passed, 60 skipped (warehouse tests, no warehouse built in the worktree; same before the change). Dashboard not touched, so `dashboard_check.py` not needed.

## popia-review verdict: PASS
Scan of the diff: no ID, passport, phone, email, address, account numbers, plates, locations, credentials or keys. No persons
or suppliers: national regulated fuel prices only (official DMPR publication). No identity linking. Nothing removed.

## Left out
2022-09 (would need re-joining split PDF lines: guessing, not done); 2025-12 (needs DMPR's December 2025 PDF or the 2026 page);
pre-2019 history (not at the DMPR path; SAPIA history not checked for licence); zone mapping beyond the 7 published grades.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; merged as PR #17 (merge commit 52940de, 2026-10-23 17:02 SAST) on the owner's GO quoted in `changes/CAB-DECISION.md` (section "PR #17"); Validator, Scout and popia-review PASS as recorded there.. PROD: live since the nightly publish of 2026-10-24 03:05 SAST (data commit 15c55e7); checked in `public-data/v1` on origin/main: fuel rows for 2021-11, 2023-01, 2023-05, 2023-10 and 2023-12 are present.
