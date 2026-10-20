# CHG-2026-009: PPD payments ingest (schema check) and D13 fuel unit-price outlier

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-20 00:35 ("do them in logical order. Ensure surgical code changes"), item A |
| Type | **Normal-high**. Adds a detector that names suppliers. Its flags stay in the four-eyes review queue and are **never published** (`config/publication.yaml` `never_publish`). Owner approves the merge |
| CIs affected | CI-092 (ppd_payments connector, dmpr_fuel connector), parsers/staging, detectors (new D13), publish policy (`never_publish`), RB-06, KE-012 |
| Linked records | RB-06, KE-012, D-07 (no Power BI automation) |
| PR | branch `feat/ppd-payments` (unmerged) |

## What
1. **PPD loader (`ppd_payments`, manual drop `data/drop/ppd/`):**
   - Each file's header is checked before storing. A file without department, supplier and amount columns (matched by
     alias) is **not stored**, and the run status becomes `schema_mismatch` (`partial` if other files loaded).
   - The error lists header names only, never row data. Unused columns are listed in the run notes.
   - Lineage: raw bytes, sha256, file name and row locator, as for every source.
   - Money is in integer cents. Blank cells stay NULL (unknown), never 0.
   - New staged fields: financial_year, quantity, unit, item_description, commodity_code (UNSPSC), commodity_title,
     province.
2. **Fuel price history:**
   - Fetches DMPR's yearly `Fuel-Price-History.pdf` for 2019–2025. Each file is fetched once only; afterwards the stored
     copy is reused.
   - Parses each PDF from word positions and keeps only rows with exactly 7 values. Ambiguous rows are skipped, never
     guessed.
   - `curated.fuel_price` goes from 70 to 609 rows, covering 2019-01 to 2026-10. The 9 months that couldn't be read are
     listed in KE-012.
   - Spot checks against the PDFs: 2024-03 95 inland 2445.000 c/l; 2025-01 diesel 0.005% inland 1928.550 c/l.
3. **D13 fuel unit price (v0.1.0):**
   - Applies to PPD lines with a litre unit and a fuel UNSPSC code (15101505/15101513 diesel, 15101506 petrol,
     15101502 paraffin) or a fuel word in the item description.
   - Implied price = amount ÷ quantity. It's compared with the highest DMPR pump/wholesale price for that fuel type in
     the payment month, or across the financial year when only the FY is known. At least 6 benchmark months are
     needed.
   - Flags when the implied price is more than 20% above the benchmark; severity is high at 2× or more.
   - The DMPR maximum is used as a generous ceiling, because PPD lines are aggregates (the guide says unit prices
     can't be seen directly). A flag is a lead to check, not a finding.
   - Evidence: the PPD file, row and sha256, plus the DMPR PDF and row.
4. **Publish policy:** `never_publish` detectors are skipped by `public_flags`. The public export counts them as hidden
   leads only.

## Not changed
- `scripts/publish-public-data.sh` and the nightly routine.
- Other detectors, dependencies, the dashboard code.
- Public data: the fuel checker's price table grows to 2019 onwards, and the KE-012 text was updated.

## Test / backout
- `uv run pytest`: tests/test_ppd_fuel.py is new; one existing PPD drop test now includes a Supplier column.
- Backout: revert the PR. Raw files stay in `data/raw` (append-only).
