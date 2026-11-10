-- Prüfung vor dem Eintragen der 7 fehlenden Quellen (NUR LESEND)
-- Aufruf: psql -d country_intelligence -f sql/03_queries/2026-11-10_sources_fehlende_pruefen.sql
\pset pager off
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;

\echo '=== P1 Gibt es die Quellen schon (Kürzel oder Name)? Erwartet: 0 Zeilen ==='
SELECT id, short_code, name
FROM sources
WHERE short_code ILIKE ANY (ARRAY['%comtrade%', '%marpor%', '%manifesto%', 'ccp', '%constitution%', '%cline%', '%coup%', '%coldat%', '%colonial%', '%dasid%', 'ddr', '%diplom%'])
   OR name ILIKE ANY (ARRAY['%comtrade%', '%manifesto%', '%constitution%', '%cline%', '%coup%', '%coldat%', '%colonial%', '%dasid%', '%diplom%']);

\echo '=== P2 Sequenz für sources.id: last_value muss >= max(id) sein ==='
SELECT (SELECT max(id) FROM sources) AS max_id,
       pg_get_serial_sequence('sources', 'id') AS sequenz;
SELECT last_value, is_called FROM sources_id_seq;

\echo '=== P3 Anzahl Quellen vorher (erwartet 52) ==='
SELECT count(*) AS quellen FROM sources;
