-- AGSA general-report annexures (CHG-2026-011). Facts as published by the Auditor-General, with lineage.
-- Municipalities (MFMA, category MUN) are linked to curated.gov_body by name key + province + type; anything that
-- does not match exactly once stays unlinked (gov_body_id NULL), never guessed. ICM (intermediate city) is a local municipality.
CREATE OR REPLACE TABLE curated.agsa_auditee_link AS
WITH a AS (
  SELECT DISTINCT auditee, auditee_key, province,
         CASE auditee_type WHEN 'MET' THEN 'metro' WHEN 'DM' THEN 'district' WHEN 'LM' THEN 'local' WHEN 'ICM' THEN 'local' END AS body_type
  FROM staging.agsa_opinion WHERE regime = 'MFMA' AND auditee_category = 'MUN'
), m AS (
  SELECT a.auditee, a.province, g.gov_body_id, count(*) OVER (PARTITION BY a.auditee, a.province) AS n
  FROM a JOIN curated.gov_body g
    -- AGSA writes Gauteng as GP; the Municipal Finance API (curated.gov_body) uses GT
    ON g.name_key = a.auditee_key AND g.province = CASE a.province WHEN 'GP' THEN 'GT' ELSE a.province END
   AND g.body_type = a.body_type AND g.valid_to IS NULL
)
SELECT auditee, province, gov_body_id FROM m WHERE n = 1;

CREATE OR REPLACE TABLE curated.agsa_audit_outcome AS
SELECT DISTINCT ON (s.regime, s.auditee, s.province, s.audit_group, s.fy_label)
       s.regime, s.auditee, s.auditee_category, s.auditee_type, s.province, s.audit_group, s.fy_label, s.fye,
       s.audit_opinion, l.gov_body_id,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.url AS source_url, rf.fetched_at_utc,
       s.source_locator
FROM staging.agsa_opinion s JOIN ops.raw_file rf USING (raw_file_id)
LEFT JOIN curated.agsa_auditee_link l ON s.regime = 'MFMA' AND l.auditee = s.auditee AND l.province = s.province
-- the same opinion can appear in Annexure 1 and 3: keep Annexure 3 (the five-year table) when both have it
ORDER BY s.regime, s.auditee, s.province, s.audit_group, s.fy_label, s.source_locator LIKE '%annexure-3%' DESC;

CREATE OR REPLACE TABLE curated.agsa_uifw AS
SELECT s.regime, s.auditee, s.auditee_category, s.auditee_type, s.province, s.audit_group, s.fy_label, s.fye,
       s.uifw_type, s.amount_cents, l.gov_body_id,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.url AS source_url, rf.fetched_at_utc,
       s.source_locator
FROM staging.agsa_uifw s JOIN ops.raw_file rf USING (raw_file_id)
LEFT JOIN curated.agsa_auditee_link l ON s.regime = 'MFMA' AND l.auditee = s.auditee AND l.province = s.province;
