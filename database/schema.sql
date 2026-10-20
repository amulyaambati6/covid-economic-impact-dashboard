-- =====================================================================
-- COVID-19 and the Global Economy: MySQL schema (bonus challenge)
--
-- Creates the `covid_economy` database: 3 reference tables, 2 observation
-- tables, and 5 views. Run first; then run load_data.sql.
--   mysql -u <user> -p < database/schema.sql
--
-- Design (see database/README.md for the full explanation):
--   * Each fact is stored once, in "long" form: one row per country,
--     indicator and period. Annual and monthly data are kept in separate
--     tables because their time keys differ (year vs month).
--   * Derived tables used by the dashboard (merged by-year table,
--     2018-2019 baselines) are VIEWS, so they can never drift from the
--     observations they are calculated from.
--   * A missing value is an absent row, never zero.
--
-- Re-running this script drops and rebuilds the database.
-- =====================================================================

DROP DATABASE IF EXISTS covid_economy;
CREATE DATABASE covid_economy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE covid_economy;

-- ---------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------

-- Where each dataset comes from.
CREATE TABLE data_source (
  source_id     TINYINT UNSIGNED NOT NULL,
  source_name   VARCHAR(120)     NOT NULL,
  publisher     VARCHAR(160)     NOT NULL,
  url           VARCHAR(255)     NULL,
  raw_file      VARCHAR(120)     NOT NULL,   -- file in data/raw/
  last_updated  DATE             NULL,       -- as stated by the publisher
  PRIMARY KEY (source_id),
  UNIQUE KEY uq_source_name (source_name)
) ENGINE = InnoDB;

-- The seven countries studied.
CREATE TABLE country (
  country_code  CHAR(3)     NOT NULL,         -- ISO 3166-1 alpha-3
  country_name  VARCHAR(60) NOT NULL,
  PRIMARY KEY (country_code),
  UNIQUE KEY uq_country_name (country_name)
) ENGINE = InnoDB;

-- What each measured value means.
CREATE TABLE indicator (
  indicator_code      VARCHAR(30)  NOT NULL,  -- World Bank code, or project code
  column_name         VARCHAR(40)  NOT NULL,  -- column name in data/processed/
  indicator_name      VARCHAR(120) NOT NULL,
  unit                VARCHAR(80)  NOT NULL,
  frequency           ENUM('annual', 'monthly')     NOT NULL,
  -- How 12 monthly values become one yearly value ('none' for annual data).
  yearly_aggregation  ENUM('none', 'sum', 'mean')   NOT NULL,
  source_id           TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (indicator_code),
  UNIQUE KEY uq_indicator_column (column_name),
  CONSTRAINT fk_indicator_source
    FOREIGN KEY (source_id) REFERENCES data_source (source_id),
  CONSTRAINT ck_indicator_aggregation CHECK (
    (frequency = 'annual'  AND yearly_aggregation = 'none') OR
    (frequency = 'monthly' AND yearly_aggregation IN ('sum', 'mean'))
  )
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Observation tables
-- ---------------------------------------------------------------------

-- World Bank indicators: one value per country, indicator and year.
CREATE TABLE annual_observation (
  country_code    CHAR(3)       NOT NULL,
  indicator_code  VARCHAR(30)   NOT NULL,
  year            SMALLINT      NOT NULL,
  value           DECIMAL(12,3) NOT NULL,
  PRIMARY KEY (country_code, indicator_code, year),
  KEY ix_annual_indicator_year (indicator_code, year),
  CONSTRAINT fk_annual_country
    FOREIGN KEY (country_code) REFERENCES country (country_code),
  CONSTRAINT fk_annual_indicator
    FOREIGN KEY (indicator_code) REFERENCES indicator (indicator_code),
  CONSTRAINT ck_annual_year CHECK (year BETWEEN 1960 AND 2100)
) ENGINE = InnoDB;

-- Pandemic and policy measures: one value per country, indicator and month.
-- month_start is the first day of the month (2020-01-01 = January 2020).
CREATE TABLE monthly_observation (
  country_code    CHAR(3)       NOT NULL,
  indicator_code  VARCHAR(30)   NOT NULL,
  month_start     DATE          NOT NULL,
  value           DECIMAL(14,3) NOT NULL,
  PRIMARY KEY (country_code, indicator_code, month_start),
  KEY ix_monthly_indicator_month (indicator_code, month_start),
  CONSTRAINT fk_monthly_country
    FOREIGN KEY (country_code) REFERENCES country (country_code),
  CONSTRAINT fk_monthly_indicator
    FOREIGN KEY (indicator_code) REFERENCES indicator (indicator_code),
  CONSTRAINT ck_monthly_first_day CHECK (DAYOFMONTH(month_start) = 1)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Views (derived data; nothing below is stored twice)
-- ---------------------------------------------------------------------

-- Economic indicators side by side, like data/processed/*_annual.csv combined.
CREATE VIEW v_economic_annual AS
SELECT c.country_name AS country,
       a.country_code AS code,
       a.year,
       MAX(CASE WHEN i.column_name = 'gdp_growth_pct'   THEN a.value END) AS gdp_growth_pct,
       MAX(CASE WHEN i.column_name = 'inflation_pct'    THEN a.value END) AS inflation_pct,
       MAX(CASE WHEN i.column_name = 'unemployment_pct' THEN a.value END) AS unemployment_pct
FROM annual_observation a
JOIN indicator i USING (indicator_code)
JOIN country   c USING (country_code)
GROUP BY c.country_name, a.country_code, a.year;

-- Each country's 2018-2019 average ("own normal"). Both years are required,
-- as in the dashboard (src/analysis/economics.py).
CREATE VIEW v_economic_baseline AS
SELECT country_code,
       indicator_code,
       AVG(value) AS baseline_2018_2019
FROM annual_observation
WHERE year IN (2018, 2019)
GROUP BY country_code, indicator_code
HAVING COUNT(*) = 2;

-- Each annual value and its difference from the country's own normal (pp).
CREATE VIEW v_economic_vs_baseline AS
SELECT c.country_name AS country,
       a.country_code AS code,
       i.column_name  AS indicator,
       a.year,
       a.value,
       b.baseline_2018_2019,
       a.value - b.baseline_2018_2019 AS difference_pp
FROM annual_observation a
JOIN indicator i USING (indicator_code)
JOIN country   c USING (country_code)
LEFT JOIN v_economic_baseline b
       ON b.country_code = a.country_code
      AND b.indicator_code = a.indicator_code;

-- Monthly pandemic measures turned into yearly values: summed (cases,
-- deaths) or averaged (stringency). A year is only calculated when all
-- 12 months have a value, matching src/data/merge_datasets.py.
CREATE VIEW v_pandemic_yearly AS
SELECT m.country_code,
       m.indicator_code,
       i.column_name AS indicator,
       YEAR(m.month_start) AS year,
       COUNT(*) AS months_with_data,
       CASE
         WHEN COUNT(*) < 12 THEN NULL
         WHEN i.yearly_aggregation = 'sum'  THEN ROUND(SUM(m.value), 3)
         WHEN i.yearly_aggregation = 'mean' THEN ROUND(AVG(m.value), 2)
       END AS yearly_value
FROM monthly_observation m
JOIN indicator i USING (indicator_code)
GROUP BY m.country_code, m.indicator_code, i.column_name,
         i.yearly_aggregation, YEAR(m.month_start);

-- Rebuilds data/processed/merged_dataset_by_year.csv: one row per country
-- and year for the period every dataset covers (2020-2022).
CREATE VIEW v_merged_by_year AS
SELECT e.country,
       e.code,
       e.year,
       MAX(CASE WHEN p.indicator = 'new_cases_per_million'  THEN p.yearly_value END) AS new_cases_per_million,
       MAX(CASE WHEN p.indicator = 'new_deaths_per_million' THEN p.yearly_value END) AS new_deaths_per_million,
       MAX(CASE WHEN p.indicator = 'sti_vaccinated'         THEN p.yearly_value END) AS sti_vaccinated,
       MAX(CASE WHEN p.indicator = 'sti_nonvaccinated'      THEN p.yearly_value END) AS sti_nonvaccinated,
       MAX(CASE WHEN p.indicator = 'sti_weighted'           THEN p.yearly_value END) AS sti_weighted,
       e.gdp_growth_pct,
       e.inflation_pct,
       e.unemployment_pct
FROM v_economic_annual e
JOIN v_pandemic_yearly p
  ON p.country_code = e.code
 AND p.year = e.year
WHERE e.year BETWEEN 2020 AND 2022
GROUP BY e.country, e.code, e.year,
         e.gdp_growth_pct, e.inflation_pct, e.unemployment_pct;
