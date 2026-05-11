-- =========================================
-- INDICATOR SEARCH
-- Suchbegriff anpassen: '%suchbegriff%'
-- =========================================

-- SUCHE nach Stichwort
SELECT 
    source_code,
    name,
    category,
    country_coverage,
    source
FROM indicator_catalog
WHERE 
    LOWER(name) LIKE '%education%' OR
    LOWER(description) LIKE '%education%' OR
    LOWER(category) LIKE '%education%'
ORDER BY 
    country_coverage DESC NULLS LAST,
    name ASC
LIMIT 20;

-- =========================================
-- BESTE INDIKATOREN PRO KATEGORIE
-- =========================================

SELECT 
    category,
    source_code,
    name,
    country_coverage
FROM (
    SELECT 
        category,
        source_code,
        name,
        country_coverage,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY country_coverage DESC NULLS LAST) as rank
    FROM indicator_catalog
    WHERE country_coverage IS NOT NULL
) ranked
WHERE rank <= 3
ORDER BY category, rank;

-- =========================================
-- KATEGORIEN ÜBERSICHT
-- =========================================

SELECT 
    category,
    COUNT(*) as total_indikatoren,
    COUNT(country_coverage) as mit_coverage_check,
    ROUND(AVG(country_coverage)::numeric, 0) as avg_coverage
FROM indicator_catalog
GROUP BY category
ORDER BY total_indikatoren DESC;