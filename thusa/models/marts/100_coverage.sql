-- COVERAGE MODEL (headline feature): entity x financial year x data type -> present / partial / missing / n.a.
-- Computed only from rows actually loaded. Variables: as_of (DATE), fye_min, fye_max (INTEGER).
-- Components per data type (each must be non-NULL to count as present):
--   budget         : ORGB & ADJB total revenue and total expenditure (curated.muni_total)       -> 4 components
--   actual_audited : AUDA total revenue and total expenditure                                    -> 2 components
--   uifw           : unauthorised, irregular, fruitless & wasteful reported                     -> 3 components
--   audit_opinion  : an AGSA opinion ('outstanding' counts as partial)                           -> 1 component
--   procurement    : eTenders awards matched to the municipality; present if >=90% carry a value -> 1 component
-- n.a. rules: entity not in existence that year (demarcation); audited data types for a year whose audit is
-- not yet due (before 1 Dec of the FYE year, MFMA s126 timetable) when nothing has been published yet;
-- procurement in years where the eTenders OCDS publication itself has < 1,000 releases (source not yet live).
CREATE OR REPLACE TABLE marts.coverage_cell AS
WITH years AS (SELECT range AS fye FROM range(getvariable('fye_min'), getvariable('fye_max') + 1)),
ent AS (
  SELECT gov_body_id, name, body_type, province, valid_from, valid_to FROM curated.gov_body WHERE sphere = 'local'
),
grid AS (
  SELECT e.*, y.fye,
         (e.valid_to IS NOT NULL AND e.valid_to <= make_date(y.fye - 1, 7, 1))
      OR (e.valid_from IS NOT NULL AND e.valid_from > make_date(y.fye, 6, 30)) AS not_in_existence
  FROM ent e CROSS JOIN years y
),
fin AS (
  SELECT gov_body_id, fye,
    count(*) FILTER (WHERE amount_type IN ('ORGB','ADJB') AND total_revenue_cents IS NOT NULL)
  + count(*) FILTER (WHERE amount_type IN ('ORGB','ADJB') AND total_expenditure_cents IS NOT NULL) AS budget_n,
    count(*) FILTER (WHERE amount_type = 'AUDA' AND total_revenue_cents IS NOT NULL)
  + count(*) FILTER (WHERE amount_type = 'AUDA' AND total_expenditure_cents IS NOT NULL) AS actual_n
  FROM curated.muni_total GROUP BY ALL
),
uifw AS (
  SELECT gov_body_id, fye, count(DISTINCT uifw_type) FILTER (WHERE amount_cents IS NOT NULL) AS uifw_n
  FROM curated.uifw_line GROUP BY ALL
),
aud AS (
  SELECT gov_body_id, fye, max(CASE WHEN opinion_code = 'outstanding' THEN 1 ELSE 2 END) AS audit_q
  FROM curated.audit_outcome GROUP BY ALL
),
proc_years AS (
  SELECT CASE WHEN month(release_date) >= 7 THEN year(release_date) + 1 ELSE year(release_date) END AS fye
  FROM curated.ocds_release WHERE release_date IS NOT NULL GROUP BY 1 HAVING count(*) >= 1000
),
proc AS (
  SELECT buyer_gov_body_id AS gov_body_id,
         CASE WHEN month(award_date) >= 7 THEN year(award_date) + 1 ELSE year(award_date) END AS fye,
         count(DISTINCT ocid || award_id) AS n_awards,
         count(DISTINCT ocid || award_id) FILTER (WHERE value_cents IS NOT NULL AND value_note IS NULL) AS n_valued
  FROM curated.award WHERE buyer_gov_body_id IS NOT NULL AND award_date IS NOT NULL GROUP BY ALL
),
long AS (
  SELECT g.gov_body_id, g.name, g.body_type, g.province, g.fye, g.not_in_existence, t.data_type, t.expected_n,
         t.present_n, t.audited, t.extra
  FROM grid g
  LEFT JOIN fin USING (gov_body_id, fye) LEFT JOIN uifw USING (gov_body_id, fye)
  LEFT JOIN aud USING (gov_body_id, fye) LEFT JOIN proc USING (gov_body_id, fye)
  CROSS JOIN LATERAL (VALUES
    ('budget', 4, coalesce(fin.budget_n, 0), false, NULL),
    ('actual_audited', 2, coalesce(fin.actual_n, 0), true, NULL),
    ('uifw', 3, coalesce(uifw.uifw_n, 0), true, NULL),
    ('audit_opinion', 2, coalesce(aud.audit_q, 0), true, NULL),
    ('procurement', 1, CASE WHEN coalesce(proc.n_awards, 0) = 0 THEN 0
                            WHEN proc.n_valued >= 0.9 * proc.n_awards THEN 1 ELSE 0.5 END, false,
                   CASE WHEN g.fye IN (SELECT fye FROM proc_years) THEN 'source_live' ELSE 'source_not_live' END)
  ) AS t(data_type, expected_n, present_n, audited, extra)
)
SELECT gov_body_id, name, body_type, province, fye,
       (fye - 1)::VARCHAR || '/' || right(fye::VARCHAR, 2) AS fy_label, data_type, expected_n, present_n,
       CASE
         WHEN not_in_existence THEN 'n.a.'
         WHEN data_type = 'procurement' AND extra = 'source_not_live' AND present_n = 0 THEN 'n.a.'
         WHEN audited AND present_n = 0 AND getvariable('as_of') < make_date(fye, 12, 1) THEN 'n.a.'
         WHEN present_n >= expected_n THEN 'present'
         WHEN data_type = 'procurement' AND present_n = 0.5 THEN 'partial'
         WHEN present_n > 0 THEN 'partial'
         ELSE 'missing'
       END AS state,
       CASE
         WHEN not_in_existence THEN 'entity_not_in_existence'
         WHEN data_type = 'procurement' AND extra = 'source_not_live' AND present_n = 0 THEN 'source_not_publishing_yet'
         WHEN audited AND present_n = 0 AND getvariable('as_of') < make_date(fye, 12, 1) THEN 'audit_not_yet_due'
         WHEN data_type = 'audit_opinion' AND present_n = 1 THEN 'opinion_outstanding'
         WHEN data_type = 'procurement' AND present_n = 0.5 THEN 'award_values_missing'
         WHEN present_n > 0 AND present_n < expected_n THEN 'components_missing'
         WHEN present_n = 0 THEN 'not_in_loaded_sources'
       END AS reason_code,
       getvariable('as_of') AS as_of
FROM long;

CREATE OR REPLACE TABLE marts.coverage_entity_year AS
SELECT gov_body_id, name, body_type, province, fye, fy_label,
       count(*) FILTER (WHERE state <> 'n.a.' AND data_type <> 'procurement') AS core_applicable,
       count(*) FILTER (WHERE state = 'present' AND data_type <> 'procurement') AS core_present,
       CASE WHEN count(*) FILTER (WHERE state <> 'n.a.' AND data_type <> 'procurement') = 0 THEN 'n.a.'
            WHEN count(*) FILTER (WHERE state <> 'n.a.' AND data_type <> 'procurement')
               = count(*) FILTER (WHERE state = 'present' AND data_type <> 'procurement') THEN 'complete'
            WHEN count(*) FILTER (WHERE state IN ('present','partial') AND data_type <> 'procurement') > 0 THEN 'partial'
            ELSE 'missing' END AS core_state,
       bool_and(state IN ('present','n.a.')) AS complete_incl_procurement,
       -- headline denominator: only years in which every core data type is already due
       getvariable('as_of') >= make_date(fye, 12, 1) AS all_core_due
FROM marts.coverage_cell GROUP BY ALL;
