CREATE OR REPLACE TABLE curated.payment AS
SELECT p.* EXCLUDE (raw_file_id), rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc
FROM staging.ppd_payment p JOIN ops.raw_file rf USING (raw_file_id);
