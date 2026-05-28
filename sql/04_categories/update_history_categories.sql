-- ============================================================
-- History & Collective Memory — Category & Dimension Assignments
-- Stand: 2026-05-28
-- ============================================================
-- 4 Categories:
--   Ethnicity & Peoples
--   Conflict & War
--   Economic History
--   State & Sovereignty


-- ============================================================
-- 1. ETHNICITY & PEOPLES
-- Wer lebt hier? Wie ist Macht zwischen Gruppen verteilt?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Ethnicity & Peoples',
    dimension = 'Ethnic Composition'
WHERE indicator_code IN (
    'EPR:n_groups',
    'EPR:discriminated_share',
    'EPR:excluded_share'
);


-- ============================================================
-- 2. CONFLICT & WAR
-- Welche Kriege hat das Land erlebt?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Conflict & War',
    dimension = 'Interstate Conflict'
WHERE indicator_code IN (
    'COW:interstate_wars',
    'COW:battle_deaths'
);

-- COW Intrastate + Total löschen (leer)
DELETE FROM indicator_metadata
WHERE indicator_code IN ('COW:intrastate_wars', 'COW:total_wars');


-- ============================================================
-- 3. ECONOMIC HISTORY
-- Wie hat sich Wohlstand historisch entwickelt?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Economic History',
    dimension = 'Historical Economy'
WHERE indicator_code IN (
    'MADDISON:gdppc',
    'MADDISON:pop'
);


-- ============================================================
-- 4. STATE & SOVEREIGNTY
-- Placeholder für zukünftige Indikatoren:
-- Unabhängigkeitsjahr, Staatsalter, Coups (aggregiert), etc.
-- ============================================================

-- Keine Indikatoren aktuell — Category für spätere Erweiterung reserviert


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
    WHERE im.domain = 'History & Collective Memory'
    GROUP BY im.indicator_code, im.category, im.dimension
) sub
GROUP BY category, dimension
ORDER BY category, dimension;
