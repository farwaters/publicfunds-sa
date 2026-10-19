CREATE OR REPLACE TABLE curated.audit_outcome AS
SELECT 'MUN:' || s.demarcation_code AS gov_body_id, s.fye,
       (s.fye - 1)::VARCHAR || '/' || right(s.fye::VARCHAR, 2) AS fy_label,
       s.opinion_code, s.opinion_label, s.report_url,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, s.source_locator
FROM staging.muni_audit s JOIN ops.raw_file rf USING (raw_file_id);
