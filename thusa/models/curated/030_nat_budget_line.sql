-- National departments: budget phase totals per financial year (FY starts April; 2025 = 2025/26).
-- Unknown line values (blank, or absurd sentinels >= R1e15) are excluded from the sum and counted, never zeroed.
-- 14 lines in the 2025 CSV are Excel scientific notation (e.g. '1,06087E+11': ~6 significant digits) and are
-- counted in n_approx_lines.
CREATE OR REPLACE TABLE curated.nat_budget_line AS
SELECT 'NAT:' || regexp_replace(lower(department), '[^a-z0-9]+', '-', 'g') AS gov_body_id, department,
       vote_number, financial_year,
       financial_year::VARCHAR || '/' || right((financial_year + 1)::VARCHAR, 2) AS fy_label,
       budget_phase,
       sum(amount_cents)::BIGINT AS amount_cents,
       count(*) AS n_lines,
       count(*) FILTER (WHERE amount_cents IS NULL) AS n_unknown_lines,
       count(*) FILTER (WHERE value_note = 'scientific_notation_precision_loss') AS n_approx_lines,
       rf.source_id, rf.path AS source_file, rf.sha256 AS source_sha256, rf.fetched_at_utc,
       min(source_locator) || ' .. ' || max(source_locator) AS source_locator
FROM staging.nt_bva JOIN ops.raw_file rf USING (raw_file_id)
WHERE department <> ''
GROUP BY ALL;
