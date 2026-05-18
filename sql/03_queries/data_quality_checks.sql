-- =========================================
-- DATA QUALITY CHECKS
-- Country Intelligence Layer
-- Letzte Aktualisierung: 2026-05
-- =========================================
-- Reihenfolge: Immer von oben nach unten ausführen
-- Alle Queries sollten 0 Zeilen zurückgeben (außer den Übersicht-Queries)
-- =========================================


-- =========================================
-- 1. ÜBERBLICK
-- =========================================

-- Gesamtübersicht Datenpunkte
SELECT 
    COUNT(*) as gesamt_datenpunkte,
    COUNT(DISTINCT iso_numeric) as laender_mit_daten,
    COUNT(DISTINCT indicator_code) as indikatoren,
    MIN(time_period) as aeltester_datenpunkt,
    MAX(time_period) as neuester_datenpunkt
FROM indicators;

-- Datenpunkte pro Indikator
SELECT 
    indicator_code,
    source_id,
    COUNT(*) as anzahl_datenpunkte,
    COUNT(DISTINCT iso_numeric) as laender,
    COUNT(DISTINCT time_period) as jahre,
    MIN(time_period) as fruehstes_jahr,
    MAX(time_period) as aktuellstes_jahr
FROM indicators
GROUP BY indicator_code, source_id
ORDER BY indicator_code;


-- =========================================
-- 2. DUPLIKATE
-- =========================================

-- Echte Duplikate (sollte 0 Zeilen zurückgeben)
SELECT iso_numeric, indicator_code, source_id, time_period, COUNT(*)
FROM indicators
GROUP BY iso_numeric, indicator_code, source_id, time_period
HAVING COUNT(*) > 1;


-- =========================================
-- 3. FOREIGN KEY KONSISTENZ
-- =========================================

-- Länder in indicators die nicht in countries sind (sollte 0 sein)
SELECT DISTINCT i.iso_numeric
FROM indicators i
LEFT JOIN countries c ON i.iso_numeric = c.iso_numeric
WHERE c.iso_numeric IS NULL;

-- Indikatoren in indicators die nicht in indicator_metadata sind (sollte 0 sein)
SELECT DISTINCT indicator_code 
FROM indicators
WHERE indicator_code NOT IN (
    SELECT indicator_code FROM indicator_metadata
);


-- =========================================
-- 4. COVERAGE PRO LAND
-- =========================================

-- Coverage-Score pro Land (wie viele Indikatoren hat jedes Land?)
SELECT 
    c.name,
    c.region,
    COUNT(DISTINCT i.indicator_code) as abgedeckte_indikatoren,
    ROUND(COUNT(DISTINCT i.indicator_code)::numeric / 
        (SELECT COUNT(*) FROM indicator_metadata) * 100, 0) as coverage_pct
FROM countries c
LEFT JOIN indicators i ON c.iso_numeric = i.iso_numeric
GROUP BY c.name, c.region
ORDER BY abgedeckte_indikatoren DESC;

-- Coverage nach Region
SELECT 
    c.region,
    ROUND(AVG(sub.coverage_pct), 1) as avg_coverage_pct,
    COUNT(*) as anzahl_laender
FROM countries c
JOIN (
    SELECT 
        c.iso_numeric,
        ROUND(COUNT(DISTINCT i.indicator_code)::numeric / 
            (SELECT COUNT(*) FROM indicator_metadata) * 100, 0) as coverage_pct
    FROM countries c
    LEFT JOIN indicators i ON c.iso_numeric = i.iso_numeric
    GROUP BY c.iso_numeric
) sub ON c.iso_numeric = sub.iso_numeric
GROUP BY c.region
ORDER BY avg_coverage_pct DESC;

-- Länder mit 0% Coverage (Territorien, Mikrostaaten)
SELECT c.name, c.region, c.subregion
FROM countries c
LEFT JOIN indicators i ON c.iso_numeric = i.iso_numeric
GROUP BY c.name, c.region, c.subregion
HAVING COUNT(i.indicator_code) = 0
ORDER BY c.region, c.name;


-- =========================================
-- 5. SPEZIFISCHE INDIKATOR-CHECKS
-- =========================================

-- Welche Länder fehlen bei einem bestimmten Indikator?
-- (Indikator-Code anpassen)
SELECT c.name, c.region, c.subregion
FROM countries c
WHERE c.iso_numeric NOT IN (
    SELECT iso_numeric FROM indicators
    WHERE indicator_code = 'WB:SP.DYN.IMRT.IN'  -- hier anpassen
)
ORDER BY c.region, c.name;

-- Auffällige Werte (Ausreißer) für einen Indikator
-- (Indikator-Code und Jahr anpassen)
SELECT 
    c.name,
    c.region,
    i.value,
    i.time_period,
    AVG(i.value) OVER () as global_avg,
    i.value - AVG(i.value) OVER () as abweichung_vom_avg
FROM indicators i
JOIN countries c ON i.iso_numeric = c.iso_numeric
WHERE i.indicator_code = 'WB:NY.GDP.PCAP.CD'  -- hier anpassen
AND i.time_period = '2023'                      -- hier anpassen
ORDER BY i.value DESC;


-- =========================================
-- 6. INDICATOR METADATA CHECKS
-- =========================================

-- Indikatoren ohne Domain-Mapping
SELECT indicator_code, name, category
FROM indicator_metadata
WHERE domain IS NULL OR domain = ''
ORDER BY indicator_code;

-- Indikatoren ohne Dimension-Mapping
SELECT indicator_code, name, domain
FROM indicator_metadata
WHERE dimension IS NULL OR dimension = ''
ORDER BY domain, indicator_code;

-- Übersicht Domain/Dimension Mapping
SELECT 
    domain,
    dimension,
    COUNT(*) as anzahl_indikatoren
FROM indicator_metadata
GROUP BY domain, dimension
ORDER BY domain NULLS LAST, dimension;
