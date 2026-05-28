-- ============================================================
-- Culture & Identity — Category & Dimension Assignments
-- + IMDb & Nobel von Communication & Media rüberziehen
-- Stand: 2026-05-28
-- ============================================================
-- 4 Categories:
--   Identity & Values
--   Religion & Belief
--   Cultural Production
--   Heritage & Memory


-- ============================================================
-- 0. IMDb & Nobel: Domain + Category updaten
-- ============================================================

UPDATE indicator_metadata SET domain = 'Culture & Identity'
WHERE indicator_code LIKE 'IMDB:%'
   OR indicator_code LIKE 'NOBEL:%';


-- ============================================================
-- 1. IDENTITY & VALUES
-- Wer sind die Menschen? Wie denken sie?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Identity & Values',
    dimension = 'Values & Attitudes'
WHERE indicator_code LIKE 'WVS:%';

UPDATE indicator_metadata SET
    category  = 'Identity & Values',
    dimension = 'Cultural Dimensions'
WHERE indicator_code LIKE 'HOFSTEDE:%';


-- ============================================================
-- 2. RELIGION & BELIEF
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Religion & Belief',
    dimension = 'Religion'
WHERE indicator_code LIKE 'PEW:%';


-- ============================================================
-- 3. CULTURAL PRODUCTION
-- Was haben sie geschaffen?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Cultural Production',
    dimension = 'Film & TV'
WHERE indicator_code LIKE 'IMDB:%';

UPDATE indicator_metadata SET
    category  = 'Cultural Production',
    dimension = 'Science & Achievement'
WHERE indicator_code LIKE 'NOBEL:%';

UPDATE indicator_metadata SET
    category  = 'Cultural Production',
    dimension = 'Sport'
WHERE indicator_code LIKE 'OLY:%';


-- ============================================================
-- 4. HERITAGE & MEMORY
-- Was haben sie bewahrt?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Heritage & Memory',
    dimension = 'Cultural Heritage'
WHERE indicator_code LIKE 'UNESCO_WHC:%'
   OR indicator_code LIKE 'UNESCO_ICH:%';


-- ============================================================
-- VERIFICATION
-- ============================================================

SELECT
    category,
    dimension,
    COUNT(*) as n_indicators,
    SUM(CASE WHEN n_countries > 0 THEN 1 ELSE 0 END) as with_data
FROM (
    SELECT
        im.indicator_code,
        im.category,
        im.dimension,
        COUNT(DISTINCT i.iso_numeric) as n_countries
    FROM indicator_metadata im
    LEFT JOIN indicators i ON i.indicator_code = im.indicator_code
    WHERE im.domain = 'Culture & Identity'
    GROUP BY im.indicator_code, im.category, im.dimension
) sub
GROUP BY category, dimension
ORDER BY category, dimension;
