-- Price benchmarks for the public dashboard utilities (CHG-2026-006).
-- fuel_price: DMPR "South African Fuel Price History" (RSA cents per litre, by month of the price adjustment).
--   When several stored documents carry the same month and grade, the most recently fetched document wins.
-- cpi: headline CPI index (2015 = 100), Stats SA data as republished by the OECD (KE-003, KE-012).
CREATE OR REPLACE TABLE curated.fuel_price AS
SELECT year, month, grade, grade_label, cents_per_litre, rf.source_id, rf.path AS source_file,
       rf.sha256 AS source_sha256, rf.fetched_at_utc, rf.url AS source_url, f.source_locator
FROM staging.fuel_price f JOIN ops.raw_file rf USING (raw_file_id)
QUALIFY row_number() OVER (PARTITION BY year, month, grade ORDER BY rf.fetched_at_utc DESC, rf.path DESC) = 1;

CREATE OR REPLACE TABLE curated.cpi AS
SELECT year, month, index_value, base_period, rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256,
       rf.fetched_at_utc, rf.url AS source_url, c.source_locator
FROM staging.cpi c JOIN ops.raw_file rf USING (raw_file_id);
