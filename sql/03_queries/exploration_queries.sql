-- Exploration queries for the Country Intelligence database
-- Use these to verify data and explore content

-- =========================================
-- BASIC OVERVIEW
-- =========================================

-- Count countries by region
SELECT region, COUNT(*) AS country_count 
FROM countries 
GROUP BY region 
ORDER BY country_count DESC;

-- All countries in a specific region
SELECT name, capital, area_km2 
FROM countries 
WHERE region = 'Americas' 
ORDER BY name;

-- =========================================
-- DATA QUALITY CHECKS
-- =========================================

-- Find countries with missing data
SELECT name, capital, region 
FROM countries 
WHERE capital IS NULL 
   OR region IS NULL 
   OR latitude IS NULL;

-- Verify ISO codes are correct length
SELECT name, iso_code_2, iso_code_3, iso_numeric 
FROM countries 
WHERE LENGTH(iso_code_2) != 2 
   OR LENGTH(iso_code_3) != 3 
   OR LENGTH(iso_numeric) != 3;

-- =========================================
-- SOURCES & INDICATORS
-- =========================================

-- All available sources
SELECT * FROM sources;

-- All indicators with their source
SELECT im.indicator_code, im.name, im.unit, im.category, s.short_code AS source
FROM indicator_metadata im
JOIN sources s ON im.source_id = s.id
ORDER BY im.category, im.name;