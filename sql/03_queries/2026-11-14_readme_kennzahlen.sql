-- Kennzahlen für README und PROJECT_CONTEXT (14.11.2026). Liest nur, ändert nichts.
-- Aufruf (Shell, Repo-Wurzel), Ausgabe in eine Datei, die Claude lesen kann:
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-14_readme_kennzahlen.sql > scripts/agent/output/2026-11-14_readme_kennzahlen.txt 2>&1

\echo '=== K01 Version'
SELECT version();

\echo '=== K02 Zeilen je Tabelle (exakt, alle Schemas)'
SELECT table_schema AS schema, table_name AS tabelle,
       (xpath('/row/c/text()', query_to_xml(format('SELECT COUNT(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text::bigint AS zeilen
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema') AND table_type = 'BASE TABLE'
ORDER BY 1, 2;

\echo '=== K03 Views und materialisierte Views'
SELECT schemaname, matviewname AS name, 'materialized' AS art FROM pg_matviews
UNION ALL
SELECT schemaname, viewname, 'view' FROM pg_views WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;

\echo '=== K04 Quellen: gesamt und mit Werten in indicators'
SELECT (SELECT COUNT(*) FROM sources) AS quellen_gesamt,
       (SELECT COUNT(DISTINCT source_id) FROM indicators WHERE source_id IS NOT NULL) AS quellen_mit_werten,
       (SELECT COUNT(*) FROM indicators WHERE source_id IS NULL) AS werte_ohne_source_id;

\echo '=== K05 Indikatoren: Codes, mit Daten, beschrieben, geprüft'
SELECT COUNT(*) AS codes,
       COUNT(*) FILTER (WHERE status = 'active') AS aktiv,
       COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM indicator_coverage c WHERE c.indicator_code = m.indicator_code)) AS mit_daten_laut_coverage,
       COUNT(description) AS mit_description,
       COUNT(metadata_reviewed_at) AS geprueft,
       COUNT(key_info) AS mit_key_info
FROM indicator_metadata m;

\echo '=== K06 Geprüfte Indikatoren je Quelle (nur Quellen mit mind. 1 geprüftem)'
SELECT s.short_code, COUNT(*) AS codes, COUNT(m.metadata_reviewed_at) AS geprueft
FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
GROUP BY 1 HAVING COUNT(m.metadata_reviewed_at) > 0 ORDER BY 1;

\echo '=== K07 Indikatoren je Domain'
SELECT COALESCE(domain, '(leer)') AS domain, COUNT(*) AS codes
FROM indicator_metadata GROUP BY 1 ORDER BY 1;

\echo '=== K08 known_issues und relational_table_metadata'
SELECT (SELECT COUNT(*) FROM known_issues) AS known_issues,
       (SELECT COUNT(*) FROM relational_table_metadata) AS relationale_tabellen_beschrieben;

\echo '=== K09 Stand indicator_coverage gegen echte Zeilen'
SELECT (SELECT SUM(n_values) FROM indicator_coverage) AS werte_laut_coverage,
       (SELECT COUNT(*) FROM indicators) AS werte_echt;

\echo '=== ENDE'
