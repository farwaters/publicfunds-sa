# CHG-2026-022: Fuel price history gaps (KE-012): join the 2022-09 DMPR PDF row split over text lines

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via the parent agent, 2026-10-23 ~18:30: recover the two unknown fuel months (KE-012) if the official DMPR source allows it |
| Environment | DEV only (branch `chg-2026-022-fuel-months` from origin/main in a /tmp worktree; PR open, not merged, nothing pushed to main) |
| Type | **Normal** (parser change that adds public price data at the next nightly refresh after a merge) |
| CIs affected | `thusa/parsers.py` (`fuel_history_pdf_rows`, new `_split_row_by_columns`, `_PDF_VALUE`), `tests/test_ppd_fuel.py`, `itil/knowledge/known-errors.md` (KE-012 text), this record, `itil/registers/change-log.md` |
| Linked records | KE-012, CSI-032, CHG-2026-009, CHG-2026-019 |
| Rollback | Close the PR unmerged. If ever merged: `git revert -m 1 <merge commit>`; the next nightly rebuild leaves 2022-09 unknown again (git history is the rollback; no .bkp files per owner amendment) |

## Source feasibility (2026-10-23, SAST)
- **2022-09**: in `fuel-price-history-2022.pdf` (raw store 2026-10-20) the Sep figures are printed on three text lines: six at y=357.4
  (above the label at y=366.6) and `2330.90` at y=371.2 (below it). Each word still sits squarely in its own value column.
  DMPR's own September 2022 and October 2022 history PDFs (same DMPR path) have the identical split, so no official file gives the
  row on one line. The October 2026 history DOCX covers 2026 only. energy.gov.za did not answer (connection failed).
- **2025-12**: not recoverable from the history series. The November 2025 PDF has an empty Dec row; `.../2025/December 2025/Fuel-Price-History.pdf`
  and `.../2026/January 2026/...` return HTTP 404; the DMPR Fuel Prices page lists 2026 documents only and the October 2026 DOCX is
  2026-only. The DMPR Petrol Price Archive has a December 2025 "Breakdown of Prices" PDF and "Fuel Regulations" XLSX, but they are a
  different table (zone price build-ups, not the 7-column history table); mapping them onto history grades would be a new source and
  grade mapping, not this change. Left unknown.

## What
- When a month row does not give exactly 7 numbers on its text line, `_split_row_by_columns` tries a join by word coordinates only:
  words whose vertical centre is within half the gap to the nearest other month label; column x-ranges from the clean 7-value rows on
  the same page; every word must be a whole figure (`dddd.dd[d]` or decimal comma) and overlap exactly one column, one word per
  column, all 7 filled. Otherwise [] and the month stays unknown. No figure is invented or re-ordered by guess.

## Evidence
2022-09 read (c/l): 2295.00 / 2273.00 / 2338.00 / 2396.10 / 2330.90 / 1681.088 / 1760.288 (`2295,00`, `1681,088`, `1760,288`
typed with a decimal comma, read as in CHG-2026-019), identical to `pdftotext -layout` of the raw PDF and of DMPR's September 2022 PDF.
Fingerprint, sha256 of json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])) over all loaded yearly PDFs, first 16 hex:
before `6c45fe5e9117e0ce` (574 rows) -> after `80bc13d78db54047` (581 rows). Diff: 0 rows removed or changed, 7 added (2022-09 only).
How computed: every `data/raw/dmpr_fuel/*/*.pdf` in the local raw store, sorted by path, parsed with
`fuel_history_pdf_rows(blob, os.path.basename(path))`; tuples sorted; `hashlib.sha256(json.dumps(tuples).encode()).hexdigest()[:16]`
(default `json.dumps` separators). The fingerprint is path-dependent: `source_locator` embeds the file name passed to the parser
(`fuel-price-history-2022.pdf#page1-Sep`), so a different name or a full path gives a different hash for the same figures.
Compare fingerprints only when computed the same way.

Review fixes (same PR): the band is also bounded by any non-month word in the label column ('Ytd', 'Avg'), so an empty first or
last month cannot take a summary row; new tests for that guard (fails without it), a non-price word in the band, and a page with
no clean rows (returns nothing). Fingerprint unchanged after the fixes: `80bc13d78db54047`, 581 rows.

## Tests
- New `test_fuel_history_pdf_rows_join_split_row_by_word_columns` and `test_split_row_join_refuses_ambiguous_columns`.
- Full suite: 166 passed, 60 skipped after the review fixes (163 at first push) (warehouse tests, no warehouse in the worktree; 161 + 60 before).

## popia-review verdict: PASS
Diff scanned: no ID, passport, phone, email, address, account numbers, plates, locations, credentials or keys. No persons or suppliers:
national regulated fuel prices only (official DMPR publication). No identity linking. Nothing removed.

## Left out
2025-12 (see above); pre-2019 history; the Breakdown-of-Prices source.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.

Result: DEV build succeeded; merged as PR #20 (merge commit 65bc8dd, 2026-10-23 19:04 SAST) on the owner's GO quoted in `changes/CAB-DECISION.md` (section "PR #20"); Validator, Scout and popia-review PASS as recorded there. PROD: live since the nightly publish of 2026-10-24 03:05 SAST (data commit 15c55e7); checked in `public-data/v1` on origin/main: fuel row for 2022-09 is present.
