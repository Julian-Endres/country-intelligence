-- Quelleninventar für docs/QUELLEN_VORHANDEN.md und scripts/check_quellen.py
-- NUR LESEND. Aufruf (Shell, Repo-Ordner):
--   psql -d country_intelligence -f sql/03_queries/2026-11-10_quelleninventar.sql > scripts/agent/output/2026-11-10_quelleninventar.txt
\pset pager off
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;

\echo '=== I1 Quellen (sources) mit Umfang über die Metadaten (zählt Werte auch ohne source_id) ==='
WITH v AS (
  SELECT indicator_code,
         count(*) AS n,
         min(time_period) FILTER (WHERE time_period ~ '^\d{4}$') AS fp,
         max(time_period) FILTER (WHERE time_period ~ '^\d{4}$') AS lp,
         bool_or(time_period !~ '^\d{4}$') AS hat_sonderperiode
  FROM indicators GROUP BY indicator_code
), l AS (
  SELECT m.source_id, count(DISTINCT i.iso_numeric) AS laender
  FROM indicators i JOIN indicator_metadata m USING (indicator_code)
  GROUP BY m.source_id
)
SELECT s.id, s.short_code, s.name,
       count(m.indicator_code)            AS codes,
       coalesce(sum(v.n), 0)              AS werte,
       coalesce(l.laender, 0)             AS laender,
       min(v.fp)                          AS von,
       max(v.lp)                          AS bis,
       bool_or(v.hat_sonderperiode)       AS sonderperiode,
       s.access_method, s.update_frequency, s.loaded_version, s.loaded_at::date AS geladen_am
FROM sources s
LEFT JOIN indicator_metadata m ON m.source_id = s.id
LEFT JOIN v USING (indicator_code)
LEFT JOIN l ON l.source_id = s.id
GROUP BY s.id, s.short_code, s.name, l.laender, s.access_method, s.update_frequency, s.loaded_version, s.loaded_at
ORDER BY s.short_code;

\echo '=== I2 Domains je Quelle (Anzahl Codes) ==='
SELECT s.short_code, coalesce(m.domain, '∅') AS domain, count(*) AS codes
FROM indicator_metadata m JOIN sources s ON s.id = m.source_id
GROUP BY 1, 2 ORDER BY 1, 3 DESC;

\echo '=== I3 Metadaten-Codes ohne source_id (nach Präfix) ==='
SELECT split_part(indicator_code, ':', 1) AS praefix, count(*) AS codes
FROM indicator_metadata WHERE source_id IS NULL GROUP BY 1 ORDER BY 1;

\echo '=== I4 Relationale Tabellen mit Beschreibung (relational_table_metadata) ==='
SELECT t.schemaname, t.relname, r.description, r.domain, r.source_id
FROM pg_stat_user_tables t
LEFT JOIN relational_table_metadata r ON r.table_name = t.relname AND r.schema_name = t.schemaname
WHERE t.schemaname <> 'public'
ORDER BY 1, 2;

\echo '=== I5 Relationale Tabellen: exakte Zeilenzahl ==='
SELECT format('SELECT %L AS tabelle, count(*) AS zeilen FROM %I.%I', schemaname || '.' || relname, schemaname, relname)
FROM pg_stat_user_tables WHERE schemaname <> 'public' ORDER BY schemaname, relname
\gexec

\echo '=== ENDE ==='
