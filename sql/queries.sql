-- =====================================================================
-- The seven required analytical queries.
-- Each is delimited by a banner comment so run_queries.py can split them.
-- =====================================================================

-- @query Q1_top_inventors
-- Q1: Top inventors — who has the most patents?
SELECT
    i.inventor_id,
    i.name,
    i.country,
    COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i
JOIN relationships r ON r.inventor_id = i.inventor_id
GROUP BY i.inventor_id, i.name, i.country
ORDER BY patent_count DESC, i.name
LIMIT 10;

-- @query Q2_top_companies
-- Q2: Top companies — which companies own the most patents?
SELECT
    c.company_id,
    c.name,
    COUNT(DISTINCT r.patent_id) AS patent_count
FROM companies c
JOIN relationships r ON r.company_id = c.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC, c.name
LIMIT 10;

-- @query Q3_top_countries
-- Q3: Top countries — which countries produce the most patents?
SELECT
    i.country,
    COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i
JOIN relationships r ON r.inventor_id = i.inventor_id
WHERE i.country IS NOT NULL AND i.country <> ''
GROUP BY i.country
ORDER BY patent_count DESC
LIMIT 10;

-- @query Q4_yearly_trend
-- Q4: Trends over time — how many patents are created each year?
SELECT
    year,
    COUNT(*) AS patent_count
FROM patents
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year;

-- @query Q5_join_sample
-- Q5: JOIN — combine patents with inventors and companies
SELECT
    p.patent_id,
    p.title,
    p.year,
    i.name    AS inventor_name,
    i.country AS inventor_country,
    c.name    AS company_name
FROM patents p
JOIN relationships r ON r.patent_id    = p.patent_id
LEFT JOIN inventors i ON i.inventor_id = r.inventor_id
LEFT JOIN companies c ON c.company_id  = r.company_id
ORDER BY p.year DESC, p.patent_id
LIMIT 20;

-- @query Q6_cte_top_inventor_companies
-- Q6: CTE — for the 5 most prolific inventors, count distinct companies
-- they have produced patents for. Demonstrates breaking a problem into
-- named sub-results with WITH.
WITH inventor_totals AS (
    SELECT
        inventor_id,
        COUNT(DISTINCT patent_id) AS patent_count
    FROM relationships
    WHERE inventor_id IS NOT NULL
    GROUP BY inventor_id
),
top_inventors AS (
    SELECT inventor_id, patent_count
    FROM inventor_totals
    ORDER BY patent_count DESC
    LIMIT 5
)
SELECT
    i.name,
    i.country,
    t.patent_count,
    COUNT(DISTINCT r.company_id) AS distinct_companies
FROM top_inventors t
JOIN inventors i      ON i.inventor_id   = t.inventor_id
JOIN relationships r  ON r.inventor_id   = t.inventor_id
GROUP BY i.name, i.country, t.patent_count
ORDER BY t.patent_count DESC;

-- @query Q7_window_rank
-- Q7: Window function — rank inventors within their country and globally.
WITH inventor_counts AS (
    SELECT
        i.name,
        i.country,
        COUNT(DISTINCT r.patent_id) AS patent_count
    FROM inventors i
    JOIN relationships r ON r.inventor_id = i.inventor_id
    WHERE i.country IS NOT NULL AND i.country <> ''
    GROUP BY i.name, i.country
)
SELECT
    name,
    country,
    patent_count,
    RANK() OVER (PARTITION BY country ORDER BY patent_count DESC) AS country_rank,
    RANK() OVER (ORDER BY patent_count DESC)                       AS global_rank
FROM inventor_counts
ORDER BY country, country_rank
LIMIT 30;
