-- Quelleninventur: Stimmt die Zuordnung Werte ↔ Metadaten ↔ Quelle? (NUR LESEND)
-- Aufruf (Shell, Repo-Ordner):
--   psql -d country_intelligence -f sql/03_queries/2026-11-10_quelleninventur_zuordnung.sql > scripts/agent/output/2026-11-10_quelleninventur.txt
\pset pager off
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;

\echo '=== Z0 Stand sources (52 vorher, 59 nach dem Eintragen der 7 relationalen Quellen) ==='
SELECT count(*) AS quellen,
       count(*) FILTER (WHERE short_code IN ('COMTRADE','MARPOR','CCP','CLINE','COLDAT','DASID','DDR')) AS davon_neu
FROM sources;

\echo '=== Z1 Werte, deren Code nicht in indicator_metadata steht (verwaiste Werte) ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT v.indicator_code, coalesce(s.short_code, '∅') AS quelle_der_werte, v.n
FROM v LEFT JOIN indicator_metadata m USING (indicator_code)
LEFT JOIN sources s ON s.id = v.source_id
WHERE m.indicator_code IS NULL
ORDER BY v.n DESC;

\echo '=== Z2 Metadaten-Codes ohne einen einzigen Wert ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT m.indicator_code, s.short_code AS quelle_meta, m.status
FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
WHERE NOT EXISTS (SELECT 1 FROM v WHERE v.indicator_code = m.indicator_code)
ORDER BY 2, 1;

\echo '=== Z3 Werte-Quelle weicht von der Metadaten-Quelle ab (je Paar Metadaten-Quelle / Werte-Quelle) ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT sm.short_code AS quelle_meta,
       coalesce(sv.short_code, '∅ (keine source_id)') AS quelle_werte,
       count(DISTINCT v.indicator_code) AS codes, sum(v.n) AS werte
FROM v JOIN indicator_metadata m USING (indicator_code)
LEFT JOIN sources sm ON sm.id = m.source_id
LEFT JOIN sources sv ON sv.id = v.source_id
WHERE v.source_id IS DISTINCT FROM m.source_id
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '=== Z4 Codes mit Werten unter mehr als einer Quellen-ID (inkl. NULL) = mögliche Doppelzeilen ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT v.indicator_code,
       string_agg(coalesce(s.short_code, '∅') || ':' || v.n, ', ' ORDER BY v.n DESC) AS quellen_und_werte
FROM v LEFT JOIN sources s ON s.id = v.source_id
GROUP BY v.indicator_code
HAVING count(*) > 1
ORDER BY 1;

\echo '=== Z5 Präfix des Codes passt nicht zum Kürzel der Metadaten-Quelle ==='
SELECT split_part(m.indicator_code, ':', 1) AS praefix, s.short_code AS quelle_meta, count(*) AS codes,
       min(m.indicator_code) AS beispiel
FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
WHERE split_part(m.indicator_code, ':', 1) IS DISTINCT FROM s.short_code
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '=== Z6 Ein Präfix bei mehreren Quellen bzw. eine Quelle mit mehreren Präfixen ==='
WITH p AS (
  SELECT split_part(m.indicator_code, ':', 1) AS praefix, s.short_code
  FROM indicator_metadata m LEFT JOIN sources s ON s.id = m.source_id
  GROUP BY 1, 2
)
SELECT 'Präfix → mehrere Quellen' AS art, praefix AS schluessel, string_agg(coalesce(short_code, '∅'), ', ') AS werte
FROM p GROUP BY praefix HAVING count(*) > 1
UNION ALL
SELECT 'Quelle → mehrere Präfixe', coalesce(short_code, '∅'), string_agg(praefix, ', ')
FROM p GROUP BY short_code HAVING count(*) > 1
ORDER BY 1, 2;

\echo '=== Z7 Quellen ohne Codes in den Metadaten ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT s.id, s.short_code, s.name,
       (SELECT coalesce(sum(n), 0) FROM v WHERE v.source_id = s.id) AS werte_mit_dieser_source_id
FROM sources s
WHERE NOT EXISTS (SELECT 1 FROM indicator_metadata m WHERE m.source_id = s.id)
ORDER BY s.short_code;

\echo '=== Z8 Werte, deren source_id auf keine existierende Quelle zeigt ==='
WITH v AS (SELECT indicator_code, source_id, count(*) AS n FROM indicators GROUP BY indicator_code, source_id)
SELECT v.source_id, count(DISTINCT v.indicator_code) AS codes, sum(v.n) AS werte
FROM v LEFT JOIN sources s ON s.id = v.source_id
WHERE v.source_id IS NOT NULL AND s.id IS NULL
GROUP BY 1;

\echo '=== Z9 Relationale Tabellen: Metadaten-Eintrag und Quellen-Verknüpfung ==='
SELECT t.schemaname || '.' || t.relname AS tabelle,
       CASE WHEN r.table_name IS NULL THEN 'fehlt' ELSE 'ja' END AS rtm_eintrag,
       coalesce(s.short_code, '∅') AS rtm_quelle,
       r.domain
FROM pg_stat_user_tables t
LEFT JOIN relational_table_metadata r ON r.table_name = t.relname AND r.schema_name = t.schemaname
LEFT JOIN sources s ON s.id = r.source_id
WHERE t.schemaname <> 'public'
ORDER BY 1;

\echo '=== Z10 indicator_catalog: Einträge je Quelle vs. tatsächlich geladene Codes ==='
SELECT split_part(c.source_code, ':', 1) AS praefix,
       count(*) AS im_katalog,
       count(*) FILTER (WHERE m.indicator_code IS NOT NULL) AS davon_in_metadaten
FROM indicator_catalog c
LEFT JOIN indicator_metadata m ON m.indicator_code = c.source_code
GROUP BY 1 ORDER BY 2 DESC;

\echo '=== ENDE ==='
