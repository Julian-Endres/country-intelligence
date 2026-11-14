-- Prüfung vor dem Neuladen von ND-GAIN (Backlog #93), NUR LESEND
-- Aufruf: psql -d country_intelligence -f sql/03_queries/2026-11-13_ndgain_pruefen.sql
\pset pager off
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;

\echo '=== N1 Gibt es die Quelle noch (Kürzel/Name)? Erwartet laut #93: 0 Zeilen ==='
SELECT id, short_code, name, loaded_version FROM sources
WHERE short_code ILIKE '%gain%' OR name ILIKE '%notre dame%' OR name ILIKE '%nd-gain%';

\echo '=== N2 Reste in Metadaten und Werten? Erwartet: 0 / 0 ==='
SELECT (SELECT count(*) FROM indicator_metadata WHERE indicator_code ILIKE 'NDGAIN%') AS metadaten,
       (SELECT count(*) FROM indicators WHERE indicator_code ILIKE 'NDGAIN%') AS werte;

\echo '=== N3 Sequenz und Anzahl Quellen (erwartet 59) ==='
SELECT (SELECT max(id) FROM sources) AS max_id, (SELECT count(*) FROM sources) AS quellen;
SELECT last_value, is_called FROM sources_id_seq;

\echo '=== N4 Wo hängen Klima-Indikatoren heute in der Taxonomie? ==='
SELECT domain, category, dimension, count(*) AS codes
FROM indicator_metadata
WHERE domain ILIKE '%environment%' OR category ILIKE '%climate%' OR dimension ILIKE '%climate%'
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

\echo '=== N5 Pflichtspalten von indicator_metadata (für den Metadaten-Eintrag) ==='
SELECT column_name, is_nullable, data_type FROM information_schema.columns
WHERE table_name = 'indicator_metadata' ORDER BY ordinal_position;
