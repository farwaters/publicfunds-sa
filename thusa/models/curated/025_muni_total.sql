-- Total revenue / total expenditure per municipality-year-amount type.
-- The API publishes the subtotal items (2900 Total Revenue, 4400 Total Expenditure) only for some years, so we
-- use the published subtotal when present and otherwise the sum of line items (revenue 0200-2800,
-- expenditure 3000-4300). On 19 Oct 2026 the derived sum matched the published subtotal (within 0.5%) for
-- 1,243 of 1,244 cases where both exist (DQ check: derived_totals_match_published).
-- A derived total is NULL (unknown) when no line item is known; it is never zero-filled.
CREATE OR REPLACE TABLE curated.muni_total AS
WITH d AS (
  SELECT gov_body_id, fye, fy_label, amount_type,
         max(amount_cents) FILTER (WHERE item_code = '2900') AS rev_pub,
         sum(amount_cents) FILTER (WHERE item_code BETWEEN '0200' AND '2800') AS rev_sum,
         count(amount_cents) FILTER (WHERE item_code BETWEEN '0200' AND '2800') AS rev_lines,
         max(amount_cents) FILTER (WHERE item_code = '4400') AS exp_pub,
         sum(amount_cents) FILTER (WHERE item_code BETWEEN '3000' AND '4300') AS exp_sum,
         count(amount_cents) FILTER (WHERE item_code BETWEEN '3000' AND '4300') AS exp_lines,
         any_value(source_id) AS source_id, max(source_file) AS source_file, max(source_sha256) AS source_sha256,
         max(fetched_at_utc) AS fetched_at_utc, min(source_locator) AS source_locator
  FROM curated.muni_fin_line GROUP BY ALL
)
SELECT gov_body_id, fye, fy_label, amount_type,
       coalesce(rev_pub, CASE WHEN rev_lines > 0 THEN rev_sum END)::BIGINT AS total_revenue_cents,
       CASE WHEN rev_pub IS NOT NULL THEN 'published_subtotal' WHEN rev_lines > 0 THEN 'sum_of_line_items' END AS revenue_basis,
       coalesce(exp_pub, CASE WHEN exp_lines > 0 THEN exp_sum END)::BIGINT AS total_expenditure_cents,
       CASE WHEN exp_pub IS NOT NULL THEN 'published_subtotal' WHEN exp_lines > 0 THEN 'sum_of_line_items' END AS expenditure_basis,
       rev_pub AS published_revenue_cents, rev_sum::BIGINT AS derived_revenue_cents,
       exp_pub AS published_expenditure_cents, exp_sum::BIGINT AS derived_expenditure_cents,
       source_id, source_file, source_sha256, fetched_at_utc, source_locator
FROM d;
