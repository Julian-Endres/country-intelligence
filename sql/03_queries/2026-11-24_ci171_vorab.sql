-- CI-171: Vorab-Prüfung für die gebündelte Migration (nur lesen).
-- Aufruf (Shell, Repo):
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-24_ci171_vorab.sql > logs/2026-11-24_ci171_vorab.txt 2>&1

\echo '--- 1) Fremdschlüssel auf indicator_metadata(indicator_code) – diese Tabellen muss ein Umbenennen mitziehen'
SELECT conrelid::regclass AS tabelle, conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint WHERE confrelid = 'indicator_metadata'::regclass AND contype = 'f';

\echo ''
\echo '--- 2) Alle Spalten namens indicator_code (auch ohne Fremdschlüssel, auch Sichten)'
SELECT table_schema, table_name, (SELECT table_type FROM information_schema.tables t
        WHERE t.table_schema = c.table_schema AND t.table_name = c.table_name) AS art
FROM information_schema.columns c
WHERE column_name = 'indicator_code' AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;
\echo '(Materialized Views stehen nicht in information_schema:)'
SELECT schemaname, matviewname FROM pg_matviews;

\echo ''
\echo '--- 3) Spalten von sources und indicator_metadata'
SELECT table_name, string_agg(column_name, ', ' ORDER BY ordinal_position) AS spalten
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('sources', 'indicator_metadata', 'known_issues')
GROUP BY 1;

\echo ''
\echo '--- 4) Betroffene Quellen'
SELECT id, short_code, name, loaded_version, access_method
FROM sources
WHERE short_code IN ('WHO','UNODC','WB','OWID_SOCIAL','Ember','EMBER','EI','EIA','WEF_GGGI','FAO_FOOD','FAO_FOOD_GRP',
                     'SAMAYO','TI','RSF','OWID_CO2','OLYMPICS','COW','FH','UNDP')
ORDER BY id;

\echo ''
\echo '--- 5) Die 9 Codes aus #2/#8: heutige Metadaten'
SELECT m.indicator_code, s.short_code AS quelle_meta, m.status, m.loader_script, left(m.reference, 60) AS reference
FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
WHERE m.indicator_code IN (SELECT DISTINCT indicator_code FROM indicators WHERE source_id = 53)
ORDER BY 1;

\echo ''
\echo '--- 6) Umbenennen (#84): Codes, Werte, known_issues, und ob ein Zielcode schon existiert'
WITH plan AS (
  SELECT indicator_code AS alt,
         CASE WHEN indicator_code LIKE 'WEF:%'      THEN 'WEF_GGGI:'     || split_part(indicator_code, ':', 2)
              WHEN indicator_code LIKE 'FAO_FOOD:%' THEN 'FAO_FOOD_GRP:' || split_part(indicator_code, ':', 2)
              WHEN indicator_code = 'CULTURE:has_national_dish' THEN 'SAMAYO:has_national_dish' END AS neu
  FROM indicator_metadata m
  WHERE indicator_code LIKE 'WEF:%' OR indicator_code = 'CULTURE:has_national_dish'
     OR (indicator_code LIKE 'FAO_FOOD:%' AND source_id = (SELECT id FROM sources WHERE short_code = 'FAO_FOOD_GRP'))
)
SELECT split_part(alt, ':', 1) AS praefix_alt, count(*) AS codes,
       (SELECT count(*) FROM indicators i WHERE i.indicator_code IN (SELECT alt FROM plan p2 WHERE split_part(p2.alt, ':', 1) = split_part(plan.alt, ':', 1))) AS werte,
       (SELECT count(*) FROM known_issues k WHERE k.indicator_code IN (SELECT alt FROM plan p3 WHERE split_part(p3.alt, ':', 1) = split_part(plan.alt, ':', 1))) AS known_issues,
       count(*) FILTER (WHERE neu IN (SELECT indicator_code FROM indicator_metadata)) AS zielcode_existiert_schon
FROM plan GROUP BY 1 ORDER BY 1;

\echo ''
\echo '--- 7) Deprecated-Kandidaten und FH:STATUS'
SELECT m.indicator_code, m.status, m.scale_type, m.value_labels,
       (SELECT count(*) FROM indicators i WHERE i.indicator_code = m.indicator_code) AS werte
FROM indicator_metadata m
WHERE m.indicator_code IN ('WB:poverty_3_day','COW:intrastate_wars','COW:total_wars','FH:STATUS')
ORDER BY 1;

\echo ''
\echo '--- 8) #85 NaN in UNDP und #91 Namen der WB-Armutscodes'
SELECT indicator_code, count(*) AS nan_werte FROM indicators
WHERE value = 'NaN'::float GROUP BY 1 ORDER BY 1;
SELECT indicator_code, name FROM indicator_metadata WHERE indicator_code IN ('WB:SI.POV.DDAY', 'WB:SI.POV.GAPS');

\echo ''
\echo '--- 9) Bezugsweg: heutige loader_script/reference der über OWID geladenen Codes'
SELECT split_part(m.indicator_code, ':', 1) AS praefix, count(*) AS codes,
       count(*) FILTER (WHERE coalesce(m.loader_script, '') = '') AS ohne_loader_script,
       count(*) FILTER (WHERE coalesce(m.reference, '') = '')     AS ohne_reference,
       min(m.loader_script) AS beispiel_loader
FROM indicator_metadata m
WHERE split_part(m.indicator_code, ':', 1) IN ('TI','RSF','EI','EMBER','EIA','OWID_CO2','WHO','UNODC')
GROUP BY 1 ORDER BY 1;
