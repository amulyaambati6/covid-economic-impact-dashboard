-- =====================================================================
-- Example queries for the covid_economy database.
-- Each one reproduces a result shown in the dashboard or in
-- findings_summary.md, so the answers can be checked against them.
--   mysql -u <user> -p --table < database/example_queries.sql
-- =====================================================================
USE covid_economy;

-- 1. What is in the database? Rows per table.
SELECT 'data_source' AS table_name, COUNT(*) AS row_count FROM data_source
UNION ALL SELECT 'country', COUNT(*) FROM country
UNION ALL SELECT 'indicator', COUNT(*) FROM indicator
UNION ALL SELECT 'annual_observation', COUNT(*) FROM annual_observation
UNION ALL SELECT 'monthly_observation', COUNT(*) FROM monthly_observation;

-- 2. Every indicator with its unit and source (joins indicator -> data_source).
SELECT i.indicator_code, i.indicator_name, i.unit, i.frequency, s.publisher
FROM indicator i
JOIN data_source s USING (source_id)
ORDER BY i.frequency, i.indicator_code;

-- 3. GDP growth in 2020 against each country's own 2018-2019 average,
--    largest shortfall first (dashboard: Economic Growth page).
SELECT country, value AS gdp_growth_2020, ROUND(baseline_2018_2019, 2) AS baseline,
       ROUND(difference_pp, 1) AS difference_pp
FROM v_economic_vs_baseline
WHERE indicator = 'gdp_growth_pct' AND year = 2020
ORDER BY difference_pp;

-- 4. Change in unemployment from 2019 to 2020, largest rise first
--    (self-join of the annual table; dashboard: Labour Market page).
SELECT c.country_name AS country,
       y19.value AS unemployment_2019,
       y20.value AS unemployment_2020,
       ROUND(y20.value - y19.value, 1) AS change_pp
FROM annual_observation y19
JOIN annual_observation y20
  ON y20.country_code = y19.country_code
 AND y20.indicator_code = y19.indicator_code
 AND y20.year = 2020
JOIN country c ON c.country_code = y19.country_code
WHERE y19.indicator_code = 'SL.UEM.TOTL.ZS' AND y19.year = 2019
ORDER BY change_pp DESC;

-- 5. Median GDP growth of the seven countries by year. MySQL has no MEDIAN
--    function, so rank the values within each year and take the middle one.
WITH ranked AS (
  SELECT year, value,
         ROW_NUMBER() OVER (PARTITION BY year ORDER BY value) AS position,
         COUNT(*)     OVER (PARTITION BY year)                AS n
  FROM annual_observation
  WHERE indicator_code = 'NY.GDP.MKTP.KD.ZG'
)
SELECT year, ROUND(AVG(value), 1) AS median_gdp_growth
FROM ranked
WHERE position IN (FLOOR((n + 1) / 2), CEIL((n + 1) / 2))
GROUP BY year
ORDER BY year;

-- 6. Total reported COVID-19 deaths per million, 2020-2022 (Pandemic page).
SELECT c.country_name AS country, ROUND(SUM(p.yearly_value)) AS deaths_per_million_2020_2022
FROM v_pandemic_yearly p
JOIN country c ON c.country_code = p.country_code
WHERE p.indicator = 'new_deaths_per_million' AND p.year BETWEEN 2020 AND 2022
GROUP BY c.country_name
ORDER BY deaths_per_million_2020_2022 DESC;

-- 7. Each country's strictest month (window function over monthly data).
WITH ranked AS (
  SELECT country_code, month_start, value,
         ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY value DESC, month_start) AS rk
  FROM monthly_observation
  WHERE indicator_code = 'OXCGRT.STI_WEIGHTED'
)
SELECT c.country_name AS country, DATE_FORMAT(r.month_start, '%M %Y') AS strictest_month,
       r.value AS stringency
FROM ranked r
JOIN country c ON c.country_code = r.country_code
WHERE r.rk = 1
ORDER BY stringency DESC;

-- 8. Pandemic severity next to the economic shock in 2020: one row per
--    country joining the yearly pandemic view to the baseline view
--    (Country Comparisons page).
SELECT m.country,
       ROUND(m.new_deaths_per_million) AS deaths_per_million_2020,
       m.sti_weighted                  AS avg_stringency_2020,
       ROUND(e.difference_pp, 1)       AS gdp_vs_own_normal_pp
FROM v_merged_by_year m
JOIN v_economic_vs_baseline e
  ON e.code = m.code AND e.year = m.year AND e.indicator = 'gdp_growth_pct'
WHERE m.year = 2020
ORDER BY gdp_vs_own_normal_pp;
