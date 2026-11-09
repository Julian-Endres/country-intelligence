-- DB-Audit Teil 1: Struktur und Integrität (10.11.2026)
-- Nur lesend. Ausführen mit psql -f, Ausgabe in eine Datei (siehe Anleitung im Chat).

SET default_transaction_read_only = on;
SET statement_timeout = '180s';
\pset pager off
\pset null '∅'

\echo '=== Q01 Constraints auf indicators / indicator_metadata / sources ==='
SELECT conrelid::regclass AS tabelle, conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN ('indicators'::regclass, 'indicator_metadata'::regclass, 'sources'::regclass)
ORDER BY 1, 3, 2;

\echo '=== Q02 Indexe auf indicators ==='
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'indicators';

\echo '=== Q03 Alle Tabellen mit Zeilenzahl (Schätzung) ==='
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY schemaname, relname;

\echo '=== Q04 Ist indicator_coverage aktuell? (Summe Coverage vs. echte Zeilen) ==='
SELECT (SELECT MAX(refreshed_at) FROM indicator_coverage)   AS coverage_stand,
       (SELECT SUM(n_values) FROM indicator_coverage)       AS werte_laut_coverage,
       (SELECT COUNT(*) FROM indicators)                    AS werte_echt;

\echo '=== Q05 Indikatoren in den Metadaten ohne Daten ==='
SELECT m.indicator_code, m.source_id, s.short_code, m.status, m.name
FROM indicator_metadata m
LEFT JOIN sources s ON s.id = m.source_id
WHERE NOT EXISTS (SELECT 1 FROM indicator_coverage c WHERE c.indicator_code = m.indicator_code)
ORDER BY 1;

\echo '=== Q06 Quellen-ID der Werte weicht von den Metadaten ab (nach Präfix) ==='
SELECT split_part(c.indicator_code, ':', 1) AS praefix,
       c.source_id                          AS sid_werte,
       m.source_id                          AS sid_metadaten,
       COUNT(*)                             AS n_codes,
       SUM(c.n_values)                      AS n_werte
FROM indicator_coverage c
JOIN indicator_metadata m USING (indicator_code)
WHERE c.source_id IS DISTINCT FROM m.source_id
GROUP BY 1, 2, 3
ORDER BY 5 DESC;

\echo '=== Q07 Code-Präfix passt nicht zum Kürzel der Quelle (Metadaten) ==='
SELECT split_part(m.indicator_code, ':', 1) AS praefix, s.id AS source_id, s.short_code, COUNT(*) AS n_codes
FROM indicator_metadata m
LEFT JOIN sources s ON s.id = m.source_id
WHERE s.short_code IS DISTINCT FROM split_part(m.indicator_code, ':', 1)
GROUP BY 1, 2, 3
ORDER BY 1;

\echo '=== Q08 Quellen-Übersicht: Codes, Werte, letzte Periode ==='
SELECT s.id, s.short_code,
       (SELECT COUNT(*) FROM indicator_metadata m WHERE m.source_id = s.id)   AS codes_meta,
       COALESCE(SUM(c.n_values), 0)                                           AS werte,
       MAX(c.last_period)                                                     AS letzte_periode,
       (s.publisher IS NOT NULL)::int + (s.license IS NOT NULL)::int
         + (s.loaded_version IS NOT NULL)::int + (s.documentation_url IS NOT NULL)::int AS v2_felder_von_4
FROM sources s
LEFT JOIN indicator_coverage c ON c.source_id = s.id
GROUP BY s.id, s.short_code
ORDER BY s.short_code;

\echo '=== Q09 Doppelte Werte über Quellen hinweg (gleiches Land, Code, Periode) ==='
SELECT indicator_code, COUNT(*) AS doppelte_land_perioden
FROM (
  SELECT indicator_code, iso_numeric, time_period
  FROM indicators
  GROUP BY 1, 2, 3
  HAVING COUNT(*) > 1
) d
GROUP BY 1
ORDER BY 2 DESC
LIMIT 60;

\echo '=== Q10 Werte NULL, NaN oder unendlich ==='
SELECT indicator_code,
       COUNT(*) FILTER (WHERE value IS NULL)                                  AS n_null,
       COUNT(*) FILTER (WHERE value = 'NaN'::float8)                          AS n_nan,
       COUNT(*) FILTER (WHERE value IN ('Infinity'::float8, '-Infinity'::float8)) AS n_inf
FROM indicators
WHERE value IS NULL OR value = 'NaN'::float8 OR value IN ('Infinity'::float8, '-Infinity'::float8)
GROUP BY 1
ORDER BY 2 DESC, 3 DESC
LIMIT 60;

\echo '=== Q11 Format von time_period (Muster) ==='
SELECT CASE
         WHEN time_period ~ '^\d{4}$'            THEN 'JJJJ'
         WHEN time_period ~ '^\d{4}-\d{4}$'      THEN 'JJJJ-JJJJ'
         WHEN time_period ~ '^\d{4}-Q[1-4]$'     THEN 'Quartal'
         WHEN time_period ~ '^\d{4}-\d{2}$'      THEN 'Monat'
         WHEN time_period IS NULL                THEN 'NULL'
         ELSE 'anderes' END AS muster,
       COUNT(*) AS n_werte,
       COUNT(DISTINCT indicator_code) AS n_codes,
       MIN(time_period) AS beispiel_min, MAX(time_period) AS beispiel_max
FROM indicators
GROUP BY 1
ORDER BY 2 DESC;

\echo '=== Q12 Codes mit Perioden außerhalb JJJJ (Liste) ==='
SELECT indicator_code, COUNT(*) AS n, MIN(time_period), MAX(time_period)
FROM indicators
WHERE time_period !~ '^\d{4}$' OR time_period IS NULL
GROUP BY 1
ORDER BY 2 DESC
LIMIT 40;

\echo '=== Q13 Jahre in der Zukunft (> 2026) bzw. sehr früh (< 1700) ==='
SELECT indicator_code, obs_status, COUNT(*) AS n, MIN(time_period), MAX(time_period)
FROM indicators
WHERE time_period ~ '^\d{4}$' AND (time_period::int > 2026 OR time_period::int < 1700)
GROUP BY 1, 2
ORDER BY 1;

\echo '=== Q14 obs_status-Verteilung ==='
SELECT obs_status, COUNT(*) AS n, COUNT(DISTINCT indicator_code) AS n_codes
FROM indicators
GROUP BY 1
ORDER BY 2 DESC;

\echo '=== Q15 Länder ohne einen einzigen Wert ==='
SELECT c.iso_numeric, c.iso_code_3, c.name, c.region
FROM countries c
WHERE NOT EXISTS (SELECT 1 FROM indicators i WHERE i.iso_numeric = c.iso_numeric)
ORDER BY c.name;

\echo '=== Q16 Länder: fehlende Region/Subregion, doppelte Namen ==='
SELECT 'ohne region' AS pruefung, COUNT(*) FROM countries WHERE region IS NULL OR region = ''
UNION ALL SELECT 'ohne subregion', COUNT(*) FROM countries WHERE subregion IS NULL OR subregion = ''
UNION ALL SELECT 'ohne cow_code', COUNT(*) FROM countries WHERE cow_code IS NULL
UNION ALL SELECT 'doppelte namen', COUNT(*) FROM (SELECT lower(name) FROM countries GROUP BY 1 HAVING COUNT(*) > 1) x;

\echo '=== Q17 Metadaten-Vollständigkeit je Quelle ==='
SELECT COALESCE(s.short_code, '(keine Quelle)') AS quelle,
       COUNT(*)                                                         AS codes,
       COUNT(*) FILTER (WHERE m.description IS NULL OR m.description = '') AS ohne_beschr,
       COUNT(*) FILTER (WHERE m.unit IS NULL OR m.unit = '')            AS ohne_einheit,
       COUNT(*) FILTER (WHERE m.name = split_part(m.indicator_code, ':', 2)) AS name_ist_rohcode,
       COUNT(*) FILTER (WHERE m.domain IS NULL OR m.category IS NULL OR m.dimension IS NULL) AS ohne_hierarchie,
       COUNT(*) FILTER (WHERE m.direction IS NULL)                      AS ohne_richtung,
       COUNT(*) FILTER (WHERE m.loader_script IS NULL)                  AS ohne_loader
FROM indicator_metadata m
LEFT JOIN sources s ON s.id = m.source_id
GROUP BY 1
ORDER BY 2 DESC;

\echo '=== Q18 Domains (müssen genau die 10 SIF-v2-Namen sein) ==='
SELECT domain, COUNT(*) AS n_codes FROM indicator_metadata GROUP BY 1 ORDER BY 1;

\echo '=== Q19 Hierarchie-Schreibvarianten (gleich bis auf Groß/Klein/Leerzeichen) ==='
SELECT 'category' AS ebene, lower(trim(category)) AS norm, array_agg(DISTINCT category) AS varianten
FROM indicator_metadata GROUP BY 2 HAVING COUNT(DISTINCT category) > 1
UNION ALL
SELECT 'dimension', lower(trim(dimension)), array_agg(DISTINCT dimension)
FROM indicator_metadata GROUP BY 2 HAVING COUNT(DISTINCT dimension) > 1;

\echo '=== Q20 Gleiche Category oder Dimension in mehreren Domains/Categories ==='
SELECT 'category' AS ebene, category AS name, array_agg(DISTINCT domain) AS eltern
FROM indicator_metadata GROUP BY category HAVING COUNT(DISTINCT domain) > 1
UNION ALL
SELECT 'dimension', dimension, array_agg(DISTINCT category)
FROM indicator_metadata GROUP BY dimension HAVING COUNT(DISTINCT category) > 1;

\echo '=== Q21 Volle Hierarchie (Domain > Category > Dimension, Anzahl Codes) ==='
SELECT domain, category, dimension, COUNT(*) AS n
FROM indicator_metadata
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

\echo '=== Q22 relational_table_metadata (komplett) ==='
SELECT * FROM relational_table_metadata;

\echo '=== Q23 Tabellen außerhalb public (zum Abgleich mit Q22) ==='
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('public', 'pg_catalog', 'information_schema')
ORDER BY 1, 2;

\echo '=== Q24 Views und materialized views ==='
SELECT schemaname, viewname AS name, 'view' AS art FROM pg_views
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT schemaname, matviewname, 'matview' FROM pg_matviews
ORDER BY 1, 2;

\echo '=== Q25 known_issues ==='
SELECT id, scope, source_id, indicator_code, table_name, title, decision FROM known_issues ORDER BY id;

\echo '=== Q26 Rollen ==='
SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY 1;

\echo '=== ENDE Teil 1 ==='
