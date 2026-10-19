-- Public bodies: municipalities (Municipal Finance API) + national departments (Vulekamali BvA).
CREATE OR REPLACE TABLE curated.gov_body AS
WITH dis AS (
  SELECT old_code AS code, min(change_date) AS valid_to FROM staging.muni_demarcation_change
  WHERE old_transition = 'disestablished' GROUP BY 1
), est AS (
  SELECT new_code AS code, min(change_date) AS valid_from FROM staging.muni_demarcation_change
  WHERE new_transition = 'established' GROUP BY 1
)
SELECT 'MUN:' || e.demarcation_code AS gov_body_id, e.name, e.long_name, 'local' AS sphere,
       CASE e.category WHEN 'A' THEN 'metro' WHEN 'B' THEN 'local' WHEN 'C' THEN 'district' END AS body_type,
       -- KE-011: the API uses KZ/LP for current and KZN/LIM for some disestablished munis; normalise to KZN/LP
       CASE e.province_code WHEN 'KZ' THEN 'KZN' WHEN 'LIM' THEN 'LP' ELSE e.province_code END AS province,
       e.demarcation_code, e.name_key,
       est.valid_from, dis.valid_to,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, e.source_locator
FROM staging.muni_entity e
JOIN ops.raw_file rf USING (raw_file_id)
LEFT JOIN dis ON dis.code = e.demarcation_code
LEFT JOIN est ON est.code = e.demarcation_code
UNION ALL
SELECT 'NAT:' || regexp_replace(lower(department), '[^a-z0-9]+', '-', 'g') AS gov_body_id, department, department,
       'national', 'department', NULL, NULL, NULL, NULL, NULL,
       rf.source_id, rf.path, rf.sha256, rf.fetched_at_utc, min(b.source_locator)
FROM staging.nt_bva b JOIN ops.raw_file rf USING (raw_file_id)
WHERE department <> ''
GROUP BY ALL;
