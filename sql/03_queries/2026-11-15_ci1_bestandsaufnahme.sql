-- =============================================================================
-- CI-1 Bestandsaufnahme: Werte ohne source_id (15.11.2026). Liest nur, ändert nichts.
-- Ziel: je Code entscheiden, welcher Fall vorliegt, bevor eine Migration geschrieben wird.
--   Fall A  nur NULL-Zeilen, keine Dubletten           → source_id nachtragen (UPDATE)
--   Fall B  NULL-Zeilen mit Dubletten (gleicher Wert)  → Kopien löschen, dann nachtragen
--   Fall C  NULL-Dubletten mit abweichenden Werten     → Regel nötig (z. B. jüngste Ausgabe)
--   Fall D  Zeile existiert zusätzlich MIT Quelle      → Kollision, NULL-Kopie prüfen/löschen
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-15_ci1_bestandsaufnahme.sql \
--        > logs/migrations/2026-11-15_ci1_bestandsaufnahme.txt 2>&1
-- Kontrollzahl: Summe null_zeilen in B01 muss 627.967 sein (Readiness-Check R2.1, 14:50).
-- =============================================================================

\pset pager off
\pset null '∅'
SET default_transaction_read_only = on;

\echo '=== B00 Kontrolle: Werte ohne source_id gesamt (Soll 627967)'
SELECT count(*) AS null_zeilen FROM indicators WHERE source_id IS NULL;

\echo ''
\echo '=== B01 Je Quelle (laut Metadaten): Zeilen, Codes, Fälle'
WITH n AS (
    SELECT i.id, i.iso_numeric, i.indicator_code, i.time_period, i.value, i.last_updated,
           x.source_id AS meta_src
    FROM indicators i JOIN indicator_metadata x USING (indicator_code)
    WHERE i.source_id IS NULL
),
paare AS (
    SELECT indicator_code, iso_numeric, time_period, meta_src,
           count(*) AS zeilen,
           (max(value) - min(value)) AS spanne,
           bool_or(value = 'NaN'::float) AS hat_nan
    FROM n GROUP BY 1, 2, 3, 4
),
kollision AS (
    SELECT p.indicator_code, p.iso_numeric, p.time_period,
           bool_and(abs(q.value - n2.value) < 1e-9) AS gleich
    FROM paare p
    JOIN indicators q ON q.indicator_code = p.indicator_code AND q.iso_numeric = p.iso_numeric
                     AND q.time_period = p.time_period AND q.source_id = p.meta_src
    JOIN n n2 ON n2.indicator_code = p.indicator_code AND n2.iso_numeric = p.iso_numeric
             AND n2.time_period = p.time_period
    GROUP BY 1, 2, 3
)
SELECT s.short_code AS quelle, p.meta_src,
       count(DISTINCT p.indicator_code)                                 AS codes,
       sum(p.zeilen)                                                    AS null_zeilen,
       count(*)                                                         AS paare,
       count(*) FILTER (WHERE p.zeilen > 1)                             AS dubl_paare,
       count(*) FILTER (WHERE p.zeilen > 1 AND p.spanne > 1e-9)         AS dubl_abweichend,
       sum(p.zeilen - 1)                                                AS ueberzaehlige_zeilen,
       (SELECT count(*) FROM kollision k JOIN indicator_metadata x2 USING (indicator_code)
         WHERE x2.source_id = p.meta_src)                               AS kollision_paare,
       (SELECT count(*) FROM kollision k JOIN indicator_metadata x2 USING (indicator_code)
         WHERE x2.source_id = p.meta_src AND NOT k.gleich)              AS kollision_abweichend
FROM paare p LEFT JOIN sources s ON s.id = p.meta_src
GROUP BY 1, 2
ORDER BY 4 DESC;

\echo ''
\echo '=== B02 Je Code: Zeilen, Dubletten, Zeilen mit Quelle, Ladezeitpunkte der NULL-Zeilen'
SELECT x.indicator_code, s.short_code AS quelle,
       count(*) FILTER (WHERE i.source_id IS NULL)                            AS null_zeilen,
       count(DISTINCT (i.iso_numeric, i.time_period)) FILTER (WHERE i.source_id IS NULL) AS null_paare,
       count(*) FILTER (WHERE i.source_id IS NOT NULL)                        AS zeilen_mit_quelle,
       count(*) FILTER (WHERE i.source_id IS NOT NULL AND i.source_id <> x.source_id) AS mit_fremder_quelle,
       min(i.last_updated) FILTER (WHERE i.source_id IS NULL)::date           AS null_erste_ladung,
       max(i.last_updated) FILTER (WHERE i.source_id IS NULL)::date           AS null_letzte_ladung,
       count(DISTINCT i.last_updated::date) FILTER (WHERE i.source_id IS NULL) AS null_ladetage
FROM indicators i JOIN indicator_metadata x USING (indicator_code)
LEFT JOIN sources s ON s.id = x.source_id
WHERE x.indicator_code IN (SELECT DISTINCT indicator_code FROM indicators WHERE source_id IS NULL)
GROUP BY 1, 2
ORDER BY 2, 1;

\echo ''
\echo '=== B03 Dubletten mit abweichenden Werten: Beispiele (je Code höchstens 5 Paare)'
WITH d AS (
    SELECT indicator_code, iso_numeric, time_period
    FROM indicators WHERE source_id IS NULL
    GROUP BY 1, 2, 3
    HAVING count(*) > 1 AND max(value) - min(value) > 1e-9
),
r AS (
    SELECT d.*, row_number() OVER (PARTITION BY d.indicator_code ORDER BY d.iso_numeric, d.time_period) AS nr
    FROM d
)
SELECT i.indicator_code, c.iso_code_3 AS land, i.time_period, i.id, i.value, i.obs_status,
       i.last_updated
FROM r JOIN indicators i ON i.indicator_code = r.indicator_code AND i.iso_numeric = r.iso_numeric
                        AND i.time_period = r.time_period AND i.source_id IS NULL
LEFT JOIN countries c ON c.iso_numeric = i.iso_numeric
WHERE r.nr <= 5
ORDER BY 1, 2, 3, i.last_updated, i.id;

\echo ''
\echo '=== B04 Dubletten: Verteilung der Ladezeitpunkte (ist "jüngste Zeile" eindeutig?)'
SELECT indicator_code,
       count(*) AS dubl_paare,
       count(*) FILTER (WHERE n_zeitpunkte = zeilen) AS jede_zeile_eigener_zeitpunkt,
       count(*) FILTER (WHERE n_zeitpunkte < zeilen) AS zeitpunkte_mehrdeutig,
       max(zeilen) AS max_zeilen_je_paar
FROM (SELECT indicator_code, iso_numeric, time_period, count(*) AS zeilen,
             count(DISTINCT last_updated) AS n_zeitpunkte
      FROM indicators WHERE source_id IS NULL
      GROUP BY 1, 2, 3 HAVING count(*) > 1) d
GROUP BY 1 ORDER BY 2 DESC;

\echo ''
\echo '=== B05 SIPRI: Metadaten und Herkunft (kein Loader im Repo)'
SELECT x.indicator_code, x.name, x.unit, x.loader_script, s.short_code, s.loaded_version,
       min(i.time_period) AS von, max(i.time_period) AS bis, count(*) AS werte,
       min(i.last_updated)::date AS geladen_am
FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
LEFT JOIN indicators i USING (indicator_code)
WHERE s.short_code = 'SIPRI'
GROUP BY 1, 2, 3, 4, 5, 6;

\echo ''
\echo '=== ENDE CI-1 Bestandsaufnahme'
