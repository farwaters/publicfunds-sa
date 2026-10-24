# CHG-2026-026: Public known-gap text KE-012 (fuel) says what is still true

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus backlog, 2026-10-24 ~08:26: fix the stale public KE-012 text. No GO to merge is given |
| Environment | DEV build and test; PROD release via the nightly after the owner's merge GO |
| Type | Standard (public wording only; no code, no data, no figures change) |
| CIs affected | `config/public-data.yaml` (`known_gaps`, id KE-012), `itil/knowledge/known-errors.md` (KE-012 row; also published as manifest `known_errors[KE-012].symptom`), `itil/registers/change-log.md`, this record |
| Linked records | KE-012; CHG-2026-019, CHG-2026-022 (months recovered); CHG-2026-018 (CPI via IMF); CHG-2026-025 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the old wording returns at the next nightly publish (git is the rollback; no .bkp files) |

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
- Pre-2019: the yearly `Fuel-Price-History.pdf` under `.../Fuel Prices Per Zone/<year>/December <year>/` for 2015 to 2018, and the November folders
  for 2015 to 2018, return HTTP 404 (curl, today); same finding as CHG-2026-019. 2019 to 2025 load. History therefore starts 2019-01. This says the tables are not at that address; it does not claim DMPR has no earlier data.
- Other places that already say this (consistent, not edited): CHG-2026-019/022 records, `thusa/connectors/prices.py` line 51 comment,
  `prices.fuel.about` last line ("Only months published in the loaded DMPR history table are included (KE-012)").
- No test asserts the text: `tests/test_publish_data.py` checks only the manifest key set.

## Change
`config/public-data.yaml`, `known_gaps` id KE-012, `text`:

Before:
> Fuel prices come from the Department of Mineral and Petroleum Resources' yearly price history tables, from January 2019. A few months are missing because their figures could not be read reliably from the PDF (Nov 2021, Sep 2022, Jan, May, Oct and Dec 2023, Dec 2025); those months show as unknown.

After:
> Fuel prices come from the Department of Mineral and Petroleum Resources' yearly price history tables. Earlier yearly tables are not at the address DMPR uses for the 2019-2025 tables (HTTP 404), so history starts in January 2019. One month is missing: December 2025 is not in any DMPR history table we could load (the November 2025 table has an empty December row and no December 2025 history table is published at DMPR's address), so it shows as unknown.

`itil/knowledge/known-errors.md`, KE-012 row, was stale and is rewritten so its start carries the key statements. `thusa/publish_data.py`
`_known_errors()` (line 397) copies each KE row's first cell into the manifest as `known_errors[<id>].symptom`, backticks and asterisks removed, cut at 280
characters plus "…". The December 2025 statement therefore had to sit inside the first 280 characters. Changes: the symptom now opens with "December 2025
fuel prices are unknown ... history starts 2019-01 (2015-2018 not at that path, HTTP 404)", the rest of the old text follows (current-year page, yearly
PDFs, months recovered by CHG-2026-019/022); the CPI clause now says Stats SA CPI is read through the IMF republication since CHG-2026-018 (last period
2026-07 on 24 Oct 2026; OECD kept as fallback); the workaround column says the fuel text is the `known_gaps` KE-012 text and the CPI text sits under KE-003.

Real `_known_errors()` run on this branch (worktree first on sys.path), `known_errors[KE-012].symptom` (281 characters including the ellipsis):
> Price benchmarks are partial: December 2025 fuel prices are unknown (not in the November 2025 PDF; no December 2025 PDF at the DMPR path, HTTP 404) and history starts 2019-01 (2015–2018 not at that path, HTTP 404). Checked 23-24 Oct 2026; the current-year DOCX covers 2026 only. D…

Not changed (Law J): `config/sources.yaml` line 105 (`mvp_load_2026_10_19`) still says "Earlier years not loaded (KE-012)". Re-read 2026-10-24: it is a dated note on the 19 Oct 2026 October-ZIP load, which loaded Jan-Oct 2026 only, so it is accurate for that day and not clearly stale; the next line (`history_pdfs`) records the 2019-2025 load. An earlier version of this RFC called it stale; that is withdrawn.
`public-data/` is not edited by hand. The live manifest changes only at the next nightly refresh and publish after this is merged, which runs on current
origin/main (CHG-2026-025). Three manifest fields change at that publish: `known_gaps[KE-012].text`, `known_errors[KE-012].symptom`, and `generated_at_sast`.
Until then the live text stays as it is.

### Merge GO and PROD publish
Sequence with the follow-ups: merge #24 first. PR #25 (CHG-2026-027, 2025-12 recovered) and PR #27 (CHG-2026-029, wording that replaces this change's "December 2025 is unknown" text) are then merged TOGETHER under one GO and land before the same nightly publish. #25 must not go live without #27.
The owner's merge GO should quote CHG-2026-026 and name the PROD publish at the next nightly (the push of `public-data/` to origin/main, which GitHub Pages
serves). A GO for another change (PR #22, #23) does not cover this one.

## Possible recovery lead (unopened, unverified)
DMPR's Petrol-Price-Archive page lists `December-2025-Fuel-Regulations.xlsx`, which may hold the 2025-12 price. It has not been opened and
nothing about its contents, licence or grade mapping is verified. Not used in this change; 2025-12 stays unknown.

## Data identical before/after
Fingerprint = `sha256(json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])))`, first 16 hex, over every
`data/raw/dmpr_fuel/*/*.pdf` parsed with `fuel_history_pdf_rows(blob, os.path.basename(path))` (as in CHG-2026-022/023), run with this
worktree first on PYTHONPATH: expected and measured `80bc13d78db54047`, 581 rows, before and after (wording only).

## Tests
- `pytest` (uv venv in this worktree): 166 passed, 60 skipped.
- `config/public-data.yaml` parses; KE-012 text read back with `yaml.safe_load`. `_known_errors()` run for real: KE-012 symptom shown above (December 2025 inside the first 280 characters).
- `scripts/dashboard_check.py`: plain `python` has no Playwright; `uv run --group screenshots python scripts/dashboard_check.py` ran: problems []
  (it reads the committed `public-data/`, so it does not show the new wording; that appears after the nightly export).

## POPIA review
PASS. Wording, URLs paths and statistics only; no personal information, IDs, contacts, accounts, credentials or supplier names.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO.
PRs #22 and #23 also append a line at the end of `itil/registers/change-log.md`; this line is separate, expect a trivial conflict on whichever merges second.

Result: DEV build succeeded; merged as PR #24 (merge commit f6ea633, 2026-10-24 10:41 SAST) on the owner's GO quoted in `changes/CAB-DECISION.md` (section "PRs #22, #24, #26, #25 and #27 to PROD, in sequence"); Validator and Scout PASS at head d95a862 as recorded there. PROD: not yet published. The data files and public text change only at the next nightly publish; as of 2026-10-24 11:22 SAST origin/main is still 6abd695 and the last data commit is 15c55e7 (2026-10-24 03:05 SAST, before this merge).
