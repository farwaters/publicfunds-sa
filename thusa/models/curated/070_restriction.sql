-- Restricted suppliers & tender defaulters. Natural persons: name kept for matching/review only;
-- the SA ID number is never stored (person_id_hmac only) and person names never reach public marts.
CREATE OR REPLACE TABLE curated.restriction AS
SELECT CASE WHEN s.is_person THEN 'PER:' || left(coalesce(s.person_id_hmac, md5(s.name_key)), 16)
            ELSE 'SUP:' || md5(coalesce(s.cipc_reg_no, s.name_key)) END AS subject_id,
       s.is_person, s.name, s.name_key, s.cipc_reg_no, s.person_id_hmac, s.restriction_type, s.reason,
       s.period_from, s.period_to, s.authorised_by,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, rf.url AS source_url,
       s.source_locator
FROM staging.rsr s JOIN ops.raw_file rf USING (raw_file_id);
