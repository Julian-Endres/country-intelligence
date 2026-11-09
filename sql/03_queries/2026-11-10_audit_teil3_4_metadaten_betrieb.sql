-- DB-Audit Teil 3 (Metadaten-Inhalt + Nachprüfungen aus Teil 2) und Teil 4 (Betrieb und Sicherheit), 10.11.2026
-- Nur lesend. Ausführen mit psql -f, Ausgabe in eine Datei (siehe Anleitung im Chat).

SET default_transaction_read_only = on;
SET statement_timeout = '600s';
\pset pager off
\pset null '∅'

-- ============================ TEIL 3 ============================

\echo '=== A01 indicator_catalog: Spalten und Beispielzeilen ==='
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'indicator_catalog' ORDER BY ordinal_position;
SELECT * FROM indicator_catalog ORDER BY random() LIMIT 3;

\echo '=== A02 Katalog: Präfixe der Codes ==='
SELECT split_part(source_code, ':', 1) AS praefix_oder_code, COUNT(*)
FROM indicator_catalog
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

\echo '=== A03 WB/WHO-Namen in den Metadaten weichen vom Katalog ab ==='
SELECT m.indicator_code, m.name AS name_metadaten, c.name AS name_katalog
FROM indicator_metadata m
JOIN indicator_catalog c
  ON c.source_code IN (m.indicator_code, split_part(m.indicator_code, ':', 2))
WHERE split_part(m.indicator_code, ':', 1) IN ('WB', 'WHO')
  AND lower(trim(m.name)) <> lower(trim(c.name))
ORDER BY 1;

\echo '=== A04 WB/WHO-Codes der Metadaten, die im Katalog fehlen ==='
SELECT m.indicator_code, m.name
FROM indicator_metadata m
WHERE split_part(m.indicator_code, ':', 1) IN ('WB', 'WHO')
  AND NOT EXISTS (SELECT 1 FROM indicator_catalog c
                  WHERE c.source_code IN (m.indicator_code, split_part(m.indicator_code, ':', 2)))
ORDER BY 1;

\echo '=== A05 Einheiten je Quelle (Vielfalt und Schreibweisen) ==='
SELECT s.short_code, m.unit, COUNT(*) AS n_codes
FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
GROUP BY 1, 2 ORDER BY 1, 3 DESC;

\echo '=== A06 WHO-Quick-Wins und weitere WHO-Codes vorhanden? ==='
SELECT m.indicator_code, m.name, c.n_values, c.first_period, c.last_period
FROM indicator_metadata m LEFT JOIN indicator_coverage c USING (indicator_code)
WHERE m.indicator_code IN ('WHO:NCD_PAA', 'WHO:UHC_INDEX_REPORTED', 'WHO:NCD_BMI_MINUS2C', 'WHO:TB_c_newinc')
   OR m.indicator_code ILIKE 'WHO:MDG%';

\echo '=== A07 Verschwundene Quellen: ND-GAIN, Olympics, UNESCO-Präfixe ==='
SELECT 'sources' AS wo, id::text, short_code, name FROM sources
WHERE name ILIKE '%gain%' OR short_code ILIKE '%GAIN%' OR short_code ILIKE 'OLY%' OR short_code ILIKE 'UNESCO%'
UNION ALL
SELECT 'metadata', COUNT(*)::text, split_part(indicator_code, ':', 1), MIN(indicator_code)
FROM indicator_metadata
WHERE indicator_code ILIKE 'ND%' OR indicator_code ILIKE 'OLY%' OR indicator_code ILIKE 'UNESCO%'
GROUP BY 3;

\echo '=== A08 Comtrade-Verdacht Abschneiden: Produktzeilen je Jahr für große, pünktliche Melder ==='
SELECT year,
       COUNT(*) FILTER (WHERE iso_numeric = '276') AS deu,
       COUNT(*) FILTER (WHERE iso_numeric = '842') AS usa,
       COUNT(*) FILTER (WHERE iso_numeric = '076') AS bra,
       COUNT(*) FILTER (WHERE iso_numeric = '392') AS jpn,
       COUNT(*) FILTER (WHERE iso_numeric = '068') AS bol,
       COUNT(*) FILTER (WHERE iso_numeric = '604') AS per
FROM trade.trade_products
GROUP BY year ORDER BY year;

\echo '=== A09 Comtrade: Zeilen je Land-Jahr (Verteilung) für 2015-2019 ==='
SELECT year, COUNT(*) AS n_laender, ROUND(AVG(n)) AS avg_zeilen, MAX(n) AS max_zeilen
FROM (SELECT iso_numeric, year, COUNT(*) AS n FROM trade.trade_products
      WHERE year BETWEEN 2015 AND 2019 GROUP BY 1, 2) x
GROUP BY year ORDER BY year;

\echo '=== A10 POLITY5: Sondercodes -66/-77/-88 als Werte ==='
SELECT indicator_code, value, COUNT(*) AS n
FROM indicators
WHERE indicator_code LIKE 'POLITY5:%' AND value IN (-66, -77, -88)
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '=== A11 POLITY5: zusammengelegte Staaten (DEU, YEM) mit mehreren Zeilen je Jahr ==='
SELECT iso_numeric, MIN(time_period::int) AS von, MAX(time_period::int) AS bis, COUNT(*) AS faelle
FROM (SELECT iso_numeric, time_period FROM indicators
      WHERE indicator_code = 'POLITY5:democ' GROUP BY 1, 2 HAVING COUNT(*) > 1) d
GROUP BY 1 ORDER BY 1;

\echo '=== A12 GBIF: Bolivien und Deutschland je Jahr (Verdacht: letztes Jahr = Gesamtzahl) ==='
SELECT time_period,
       MAX(value) FILTER (WHERE iso_numeric = '068') AS bol_total,
       MAX(value) FILTER (WHERE iso_numeric = '276') AS deu_total
FROM indicators
WHERE indicator_code = 'GBIF:total' AND time_period::int >= 2015
GROUP BY 1 ORDER BY 1;

\echo '=== A13 Fiskalquoten über 100 % des BIP ==='
SELECT i.indicator_code, c.iso_code_3, i.time_period, ROUND(i.value::numeric, 1) AS wert
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code IN ('WB:GC.TAX.TOTL.GD.ZS', 'WB:GC.XPN.TOTL.GD.ZS') AND i.value > 100
ORDER BY 1, 2, 3;

\echo '=== A14 EPR: Anteile über 100 % ==='
SELECT i.indicator_code, c.iso_code_3, COUNT(*) AS n, MIN(i.time_period), MAX(i.time_period), ROUND(MAX(i.value)::numeric, 1) AS max
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'EPR:%share' AND i.value > 100
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '=== A15 WHO:MDG_0000000003: Metadaten und Werte 0 ==='
SELECT m.indicator_code, m.name, m.unit,
       (SELECT COUNT(*) FROM indicators i WHERE i.indicator_code = m.indicator_code AND i.value = 0) AS n_null_werte,
       (SELECT COUNT(*) FROM indicators i WHERE i.indicator_code = m.indicator_code) AS n_gesamt
FROM indicator_metadata m WHERE m.indicator_code = 'WHO:MDG_0000000003';

\echo '=== A16 POLITY5: Zeilen im Jahr 2020 (laut Doku endet Polity 2018) ==='
SELECT i.indicator_code, c.iso_code_3, i.time_period, i.value
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'POLITY5:%' AND i.time_period::int > 2018
ORDER BY 1, 2;

\echo '=== A17 Relationale Tabellen: Länderspalten mit anderen Namen (leer/unbekannt) ==='
SELECT format(
  'SELECT %L AS tabelle, %L AS spalte, COUNT(*) AS zeilen, COUNT(*) FILTER (WHERE %I IS NULL) AS leer, COUNT(*) FILTER (WHERE %I IS NOT NULL AND %I::text NOT IN (SELECT iso_numeric FROM countries) AND %I::text NOT IN (SELECT iso_code_3 FROM countries)) AS unbekannt FROM %I.%I',
  table_schema || '.' || table_name, column_name, column_name, column_name, column_name, column_name, table_schema, table_name)
FROM information_schema.columns
WHERE table_schema NOT IN ('public', 'pg_catalog', 'information_schema')
  AND column_name IN ('source_iso', 'target_iso', 'sending_iso', 'destination_iso', 'country_iso', 'partner_iso')
ORDER BY table_schema, table_name, column_name
\gexec

-- ============================ TEIL 4 ============================

\echo '=== B01 Version, Größe, wichtige Einstellungen ==='
SELECT version();
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_groesse;
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem', 'effective_cache_size',
               'listen_addresses', 'port', 'password_encryption', 'ssl', 'autovacuum',
               'max_connections', 'log_min_duration_statement', 'hba_file', 'data_directory')
ORDER BY name;

\echo '=== B02 Größte Tabellen (inkl. Indexe) ==='
SELECT n.nspname || '.' || c.relname AS tabelle,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS gesamt,
       pg_size_pretty(pg_relation_size(c.oid))       AS daten,
       pg_size_pretty(pg_indexes_size(c.oid))        AS indexe
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 15;

\echo '=== B03 Pflege: tote Zeilen, letztes VACUUM/ANALYZE ==='
SELECT schemaname || '.' || relname AS tabelle, n_live_tup, n_dead_tup,
       GREATEST(last_vacuum, last_autovacuum)   AS letztes_vacuum,
       GREATEST(last_analyze, last_autoanalyze) AS letztes_analyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 15;

\echo '=== B04 Indexe und ihre Nutzung ==='
SELECT schemaname || '.' || relname AS tabelle, indexrelname AS index, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS groesse
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 25;

\echo '=== B05 Tabellen ohne Primärschlüssel ==='
SELECT n.nspname || '.' || c.relname AS tabelle
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conrelid = c.oid AND k.contype = 'p')
ORDER BY 1;

\echo '=== B06 Installierte Erweiterungen ==='
SELECT extname, extversion FROM pg_extension ORDER BY 1;

\echo '=== B07 Rechte von ci_agent_readonly je Schema ==='
SELECT n.nspname AS schema,
       has_schema_privilege('ci_agent_readonly', n.nspname, 'USAGE') AS usage,
       COUNT(c.oid) AS tabellen,
       COUNT(c.oid) FILTER (WHERE has_table_privilege('ci_agent_readonly', c.oid, 'SELECT')) AS mit_select,
       COUNT(c.oid) FILTER (WHERE has_table_privilege('ci_agent_readonly', c.oid, 'INSERT,UPDATE,DELETE')) AS mit_schreibrecht
FROM pg_namespace n
LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind IN ('r', 'v', 'm')
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast') AND n.nspname NOT LIKE 'pg_temp%' AND n.nspname NOT LIKE 'pg_toast_temp%'
GROUP BY 1 ORDER BY 1;

\echo '=== B08 Objekte, die ci_agent_readonly nicht lesen kann ==='
SELECT n.nspname || '.' || c.relname AS objekt, c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'v', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND NOT has_table_privilege('ci_agent_readonly', c.oid, 'SELECT')
ORDER BY 1;

\echo '=== B09 Rolleneinstellungen und Default-Privilegien ==='
SELECT r.rolname, s.setconfig FROM pg_db_role_setting s JOIN pg_roles r ON r.oid = s.setrole;
SELECT pg_get_userbyid(defaclrole) AS fuer_rolle, defaclnamespace::regnamespace AS schema, defaclobjtype, defaclacl
FROM pg_default_acl;

\echo '=== B10 Rollen mit gesetztem Passwort (ohne Passwort selbst) ==='
SELECT rolname, rolpassword IS NOT NULL AS hat_passwort, left(rolpassword, 13) AS verfahren, rolvaliduntil
FROM pg_authid WHERE rolname !~ '^pg_' ORDER BY 1;

\echo '=== B11 Anmelderegeln (pg_hba.conf) ==='
SELECT line_number, type, database, user_name, address, auth_method, error
FROM pg_hba_file_rules ORDER BY line_number;

\echo '=== ENDE Teil 3+4 ==='
