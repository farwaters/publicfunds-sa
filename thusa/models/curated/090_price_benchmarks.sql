-- Price benchmarks for the public dashboard utilities (CHG-2026-006).
-- fuel_price: DMPR "South African Fuel Price History" (RSA cents per litre, by month of the price adjustment).
--   When several stored documents carry the same month and grade, the most recently fetched document wins.
-- cpi: Stats SA headline CPI index. One source, one base: the IMF republication (Dec 2024 = 100, to the latest
--   month; CHG-2026-018) when loaded, else the OECD republication (2015 = 100, ends 2025-01; KE-003, KE-012).
--   Within the chosen source the most recently fetched file wins per month.
CREATE OR REPLACE TABLE curated.fuel_price AS
SELECT year, month, grade, grade_label, cents_per_litre, rf.source_id, rf.path AS source_file,
       rf.sha256 AS source_sha256, rf.fetched_at_utc, rf.url AS source_url, f.source_locator
FROM staging.fuel_price f JOIN ops.raw_file rf USING (raw_file_id)
QUALIFY row_number() OVER (PARTITION BY year, month, grade ORDER BY rf.fetched_at_utc DESC, rf.path DESC) = 1;

CREATE OR REPLACE TABLE curated.cpi AS
SELECT year, month, index_value, base_period, rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256,
       rf.fetched_at_utc, rf.url AS source_url, c.source_locator
FROM staging.cpi c JOIN ops.raw_file rf USING (raw_file_id)
WHERE rf.source_id = (SELECT CASE WHEN count(*) FILTER (WHERE r2.source_id = 'imf_cpi') > 0 THEN 'imf_cpi'
                                  ELSE 'oecd_cpi' END
                      FROM staging.cpi c2 JOIN ops.raw_file r2 USING (raw_file_id))
QUALIFY row_number() OVER (PARTITION BY year, month ORDER BY rf.fetched_at_utc DESC, rf.path DESC) = 1;
