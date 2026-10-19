-- Municipal income & expenditure (incexp_v2, annual). amount_type: ORGB original budget, ADJB adjusted budget,
-- AUDA audited actual, ACT actual (pre-audit / s71). fye = financial year END (June).
CREATE OR REPLACE TABLE curated.muni_fin_line AS
SELECT 'MUN:' || s.demarcation_code AS gov_body_id, s.fye,
       (s.fye - 1)::VARCHAR || '/' || right(s.fye::VARCHAR, 2) AS fy_label,
       s.amount_type, s.item_code, i.item_label, s.amount_cents,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, s.source_locator
FROM staging.muni_incexp s
JOIN ops.raw_file rf USING (raw_file_id)
LEFT JOIN staging.muni_incexp_item i USING (item_code);
