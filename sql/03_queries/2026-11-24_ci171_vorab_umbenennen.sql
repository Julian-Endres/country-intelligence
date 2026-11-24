-- CI-171: Vorab-Prüfung Teil 6 (korrigiert) – Umbenennen #84. Nur lesen.
-- Aufruf (Shell, Repo):
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-24_ci171_vorab_umbenennen.sql > logs/2026-11-24_ci171_vorab_umbenennen.txt 2>&1
WITH plan AS (
  SELECT m.indicator_code AS alt,
         CASE WHEN m.indicator_code LIKE 'WEF:%'      THEN 'WEF_GGGI:'     || split_part(m.indicator_code, ':', 2)
              WHEN m.indicator_code LIKE 'FAO_FOOD:%' THEN 'FAO_FOOD_GRP:' || split_part(m.indicator_code, ':', 2)
              ELSE 'SAMAYO:has_national_dish' END AS neu
  FROM indicator_metadata m
  WHERE m.indicator_code LIKE 'WEF:%' OR m.indicator_code = 'CULTURE:has_national_dish'
     OR (m.indicator_code LIKE 'FAO_FOOD:%' AND m.source_id = (SELECT id FROM sources WHERE short_code = 'FAO_FOOD_GRP'))
),
je_code AS (
  SELECT p.alt, p.neu,
         (SELECT count(*) FROM indicators i   WHERE i.indicator_code = p.alt) AS werte,
         (SELECT count(*) FROM known_issues k WHERE k.indicator_code = p.alt) AS known_issues,
         EXISTS (SELECT 1 FROM indicator_metadata x WHERE x.indicator_code = p.neu) AS ziel_existiert
  FROM plan p
)
SELECT split_part(alt, ':', 1) AS praefix_alt, split_part(neu, ':', 1) AS praefix_neu,
       count(*) AS codes, sum(werte) AS werte, sum(known_issues) AS known_issues,
       count(*) FILTER (WHERE ziel_existiert) AS zielcode_existiert_schon
FROM je_code GROUP BY 1, 2 ORDER BY 1;

\echo ''
\echo '--- Kontrolle: FAO_FOOD-Codes, die bei der Quelle FAO_FOOD bleiben (sollen nicht umbenannt werden)'
SELECT m.indicator_code, s.short_code FROM indicator_metadata m JOIN sources s ON s.id = m.source_id
WHERE m.indicator_code LIKE 'FAO_FOOD:%' AND s.short_code <> 'FAO_FOOD_GRP' ORDER BY 1;

\echo ''
\echo '--- Kontrolle: Quellen-ID der Werte bei den umzubenennenden Codes (muss je Präfix eine sein)'
SELECT split_part(i.indicator_code, ':', 1) AS praefix, s.short_code, count(*) AS werte
FROM indicators i JOIN sources s ON s.id = i.source_id
WHERE i.indicator_code LIKE 'WEF:%' OR i.indicator_code = 'CULTURE:has_national_dish'
   OR i.indicator_code IN (SELECT indicator_code FROM indicator_metadata
                           WHERE indicator_code LIKE 'FAO_FOOD:%' AND source_id = 50)
GROUP BY 1, 2 ORDER BY 1;
