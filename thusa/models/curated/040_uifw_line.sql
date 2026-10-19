-- Unauthorised, irregular, fruitless & wasteful expenditure as reported in AFS notes (uifwexp cube).
-- The API does not state whether the amount is incurred-in-year or closing balance: measure = 'reported'.
CREATE OR REPLACE TABLE curated.uifw_line AS
SELECT 'MUN:' || s.demarcation_code AS gov_body_id, s.fye,
       (s.fye - 1)::VARCHAR || '/' || right(s.fye::VARCHAR, 2) AS fy_label,
       CASE s.item_code WHEN 'fruitless' THEN 'fruitless_wasteful' ELSE s.item_code END AS uifw_type,
       'reported' AS measure, s.amount_cents,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, s.source_locator
FROM staging.muni_uifw s JOIN ops.raw_file rf USING (raw_file_id);
