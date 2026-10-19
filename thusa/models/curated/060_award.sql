-- eTenders awards (one row per award x supplier). Buyer -> municipality by exact normalised-name key; when a
-- district and a local share a key, 'district' in the buyer name selects the district.
CREATE OR REPLACE TABLE curated.buyer_alias AS
WITH b AS (SELECT DISTINCT buyer_id, buyer_name, buyer_key FROM staging.ocds_release WHERE buyer_key IS NOT NULL),
cand AS (
  SELECT b.*, g.gov_body_id, g.body_type,
         row_number() OVER (PARTITION BY b.buyer_id, b.buyer_name ORDER BY
           CASE WHEN (b.buyer_name ILIKE '%district%') = (g.body_type = 'district') THEN 0 ELSE 1 END,
           (g.valid_to IS NOT NULL)) AS rk,
         count(*) OVER (PARTITION BY b.buyer_id, b.buyer_name) AS n_cand
  FROM b JOIN curated.gov_body g ON g.name_key = b.buyer_key AND g.sphere = 'local'
)
SELECT buyer_id, buyer_name, gov_body_id, 'exact_normalised_name' AS match_method,
       CASE WHEN n_cand = 1 THEN 0.95 ELSE 0.85 END AS confidence
FROM cand WHERE rk = 1;

CREATE OR REPLACE TABLE curated.award AS
SELECT a.ocid, a.award_id, a.award_status, r.buyer_id, r.buyer_name, ba.gov_body_id AS buyer_gov_body_id,
       a.supplier_id, a.supplier_name, a.supplier_key, a.supplier_person_key, a.n_suppliers,
       a.value_cents, a.value_note,
       coalesce(a.date_signed, a.release_date) AS award_date,
       CASE WHEN a.date_signed IS NOT NULL THEN 'contract.dateSigned' ELSE 'release.date (proxy)' END AS award_date_basis,
       r.tender_title, r.procurement_method, r.main_category, r.province, r.doc_url,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc, a.source_locator
FROM staging.ocds_award a
JOIN staging.ocds_release r USING (ocid)
JOIN ops.raw_file rf ON rf.raw_file_id = a.raw_file_id
LEFT JOIN curated.buyer_alias ba ON ba.buyer_id = r.buyer_id AND ba.buyer_name = r.buyer_name;

CREATE OR REPLACE TABLE curated.ocds_release AS
SELECT r.* EXCLUDE (raw_file_id), ba.gov_body_id AS buyer_gov_body_id,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc
FROM staging.ocds_release r JOIN ops.raw_file rf USING (raw_file_id)
LEFT JOIN curated.buyer_alias ba ON ba.buyer_id = r.buyer_id AND ba.buyer_name = r.buyer_name;
