-- =============================================================================
-- Readiness-Check DB v1.0 (v2, 15.11.2026)
-- Misst die sechs Prüfpunkte des Meilensteins "DB v1.0". Liest nur, ändert nichts
-- (die Sitzung wird auf read only gesetzt).
--
-- Änderungen v2 (nach dem ersten Lauf 14:42):
--   R1.5  Jahre mit 1–4 Ziffern sind gültig (MADDISON hat echte Jahre 1 und 730).
--   R1.x  "Behoben oder dokumentiert": Codes mit known_issue (scope indicator,
--         decision accepted/wont_fix) zählen in den Pflichtprüfungen R1.1–R1.5 nicht mit.
--         R1.9 zeigt, wie viele Codes so ausgenommen sind. Gilt nur für Prüfpunkt 1;
--         Zuordnung (2), Struktur (3) und Metadaten (4) muss behoben werden.
--   R1.4  NaN-Werte ausgenommen (stehen schon in R1.1).
--   R1.6  Ohne latente Skalen und Skalen mit negativem Minimum (Verhältnis sinnlos um 0),
--         ohne Jahrespaare, in denen sich die Länderzahl mehr als halbiert/verdoppelt
--         (angebrochene Jahre, siehe Backlog #95).
--
-- Aufruf (Shell, Repo-Wurzel). Die Ausgabe landet in einer Datei, die Claude lesen kann:
--   mkdir -p scripts/agent/output/2026-11-15_readiness
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-15_readiness_check.sql \
--        > scripts/agent/output/2026-11-15_readiness/stand_$(date +%Y%m%d_%H%M).txt 2>&1
--
-- Aufbau:
--   Teil 1  Übersicht: eine Zeile je Prüfung mit Ist, Soll und Art.
--           Art "Pflicht" muss für v1.0 auf Soll stehen (oder als known_issue begründet sein).
--           Art "Info" ist eine Kennzahl ohne Soll; Julian entscheidet, ob sie Pflicht wird.
--   Teil 2  Einzellisten zu jeder Prüfung (je höchstens 40 Zeilen), damit man sieht, WAS fehlt.
--
-- Prüfpunkt 6 (Backup, Git-Tag) ist nicht in SQL prüfbar und steht deshalb nicht hier.
-- Fehler einer einzelnen Abfrage brechen das Skript nicht ab; sie stehen als ERROR in der
-- Ausgabe und müssen gemeldet werden (ein fehlender Wert in der Übersicht ist ein Befund).
-- Laufzeit: mehrere vollständige Durchläufe über indicators (ca. 4,1 Mio. Zeilen),
-- Schätzung 1–3 Minuten.
-- =============================================================================

\pset pager off
\pset null '∅'
SET default_transaction_read_only = on;
SET statement_timeout = '10min';

\echo '=== R00 Zeitpunkt und Grundzahlen'
SELECT now()                                    AS geprueft_am,
       (SELECT count(*) FROM indicators)        AS werte,
       (SELECT count(*) FROM indicator_metadata) AS codes_metadaten,
       (SELECT count(*) FROM sources)           AS quellen,
       (SELECT max(refreshed_at) FROM indicator_coverage) AS coverage_stand;


-- =============================================================================
-- TEIL 1: ÜBERSICHT
-- =============================================================================
\echo ''
\echo '=== TEIL 1: ÜBERSICHT (Pflicht = muss auf Soll, Info = Kennzahl)'

WITH
m AS (SELECT * FROM indicator_metadata WHERE status = 'active'),
wert_codes AS (SELECT DISTINCT indicator_code FROM indicators),
doku AS (                      -- per known_issue akzeptierte Codes ("dokumentiert")
    SELECT DISTINCT indicator_code FROM known_issues
    WHERE scope = 'indicator' AND decision IN ('accepted', 'wont_fix')
),
befund_codes AS (              -- Codes mit Befund in R1.1–R1.5 (vor Ausnahme)
    SELECT DISTINCT i.indicator_code
    FROM indicators i JOIN indicator_metadata x USING (indicator_code)
    WHERE i.value = 'NaN'::float
       OR (i.indicator_code LIKE 'POLITY5:%' AND i.value IN (-66, -77, -88))
       OR (i.value <> 'NaN'::float AND ((x.scale_min IS NOT NULL AND i.value < x.scale_min)
                                     OR (x.scale_max IS NOT NULL AND i.value > x.scale_max)))
       OR (i.time_period !~ '^-?\d{1,4}$' AND i.time_period <> 'static')
),
jahr_median AS (               -- Median je Code und Jahr, nur Jahre mit mind. 20 Ländern
    SELECT i.indicator_code, i.time_period::int AS jahr,
           count(DISTINCT i.iso_numeric) AS laender,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY i.value) AS median
    FROM indicators i JOIN indicator_metadata x USING (indicator_code)
    WHERE i.time_period ~ '^-?\d{1,4}$' AND i.value IS NOT NULL AND i.value <> 'NaN'::float
      AND x.scale_type IS DISTINCT FROM 'latent' AND coalesce(x.scale_min, 0) >= 0
    GROUP BY i.indicator_code, i.time_period
    HAVING count(DISTINCT i.iso_numeric) >= 20
),
spruenge AS (
    SELECT a.indicator_code
    FROM jahr_median a
    JOIN jahr_median b ON b.indicator_code = a.indicator_code AND b.jahr = a.jahr + 1
    WHERE a.median > 0 AND b.median > 0
      AND b.laender BETWEEN a.laender / 2.0 AND a.laender * 2.0
      AND (b.median / a.median > 5 OR b.median / a.median < 0.2)
),
pruefungen (punkt, id, pruefung, ist, soll, art) AS (
    -- ---------- Prüfpunkt 1: keine bekannten Ladefehler (messbare Symptome) ----------
    SELECT 1, 'R1.1', 'Werte = NaN',
           (SELECT count(*) FROM indicators WHERE value = 'NaN'::float
               AND indicator_code NOT IN (SELECT indicator_code FROM doku)), 0, 'Pflicht'
    UNION ALL
    SELECT 1, 'R1.2', 'POLITY5-Sondercodes -66/-77/-88 als Werte',
           (SELECT count(*) FROM indicators
             WHERE indicator_code LIKE 'POLITY5:%' AND value IN (-66, -77, -88)
               AND indicator_code NOT IN (SELECT indicator_code FROM doku)), 0, 'Pflicht'
    UNION ALL
    SELECT 1, 'R1.3', 'Dubletten Land/Code/Jahr (über source_id hinweg)',
           (SELECT count(*) FROM (SELECT 1 FROM indicators
                                  WHERE indicator_code NOT IN (SELECT indicator_code FROM doku)
                                  GROUP BY iso_numeric, indicator_code, time_period
                                  HAVING count(*) > 1) d), 0, 'Pflicht'
    UNION ALL
    SELECT 1, 'R1.4', 'Werte außerhalb scale_min/scale_max (ohne NaN)',
           (SELECT count(*) FROM indicators i JOIN indicator_metadata x USING (indicator_code)
             WHERE i.value <> 'NaN'::float
               AND ((x.scale_min IS NOT NULL AND i.value < x.scale_min)
                 OR (x.scale_max IS NOT NULL AND i.value > x.scale_max))
               AND i.indicator_code NOT IN (SELECT indicator_code FROM doku)), 0, 'Pflicht'
    UNION ALL
    SELECT 1, 'R1.5', 'time_period weder Jahr (1–4 Ziffern) noch static',
           (SELECT count(*) FROM indicators
             WHERE time_period !~ '^-?\d{1,4}$' AND time_period <> 'static'
               AND indicator_code NOT IN (SELECT indicator_code FROM doku)), 0, 'Pflicht'
    UNION ALL
    SELECT 1, 'R1.6', 'Codes mit Sprung des Länder-Medians > Faktor 5 zum Vorjahr',
           (SELECT count(DISTINCT indicator_code) FROM spruenge), NULL, 'Info'
    UNION ALL
    SELECT 1, 'R1.7', 'Codes mit Werten in nur einem Jahr (ohne static)',
           (SELECT count(*) FROM (SELECT indicator_code FROM indicators
                                  WHERE time_period <> 'static'
                                  GROUP BY indicator_code
                                  HAVING count(DISTINCT time_period) = 1) e), NULL, 'Info'
    UNION ALL
    SELECT 1, 'R1.8', 'Werte mit Jahr nach dem Vorjahr (laufendes Jahr oder Zukunft)',
           (SELECT count(*) FROM indicators
             WHERE time_period ~ '^\d{4}$'
               AND time_period::int >= extract(year FROM current_date)::int), NULL, 'Info'
    UNION ALL
    SELECT 1, 'R1.9', 'Codes mit Befund in R1.1–R1.5, per known_issue dokumentiert (ausgenommen)',
           (SELECT count(*) FROM befund_codes WHERE indicator_code IN (SELECT indicator_code FROM doku)),
           NULL, 'Info'

    -- ---------- Prüfpunkt 2: jeder Wert ist zugeordnet ----------
    UNION ALL
    SELECT 2, 'R2.1', 'Werte ohne source_id',
           (SELECT count(*) FROM indicators WHERE source_id IS NULL), 0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.2', 'Werte, deren source_id nicht zur Metadaten-Quelle passt',
           (SELECT count(*) FROM indicators i JOIN indicator_metadata x USING (indicator_code)
             WHERE i.source_id IS DISTINCT FROM x.source_id), 0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.3', 'Codes in Metadaten ohne source_id',
           (SELECT count(*) FROM indicator_metadata WHERE source_id IS NULL), 0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.4', 'Aktive Codes ohne einen einzigen Wert',
           (SELECT count(*) FROM m WHERE indicator_code NOT IN (SELECT indicator_code FROM wert_codes)),
           0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.5', 'Relationale Tabellen ohne Eintrag in relational_table_metadata',
           (SELECT count(*) FROM pg_stat_user_tables t
             WHERE t.schemaname NOT IN ('public')
               AND NOT EXISTS (SELECT 1 FROM relational_table_metadata r
                               WHERE r.schema_name = t.schemaname AND r.table_name = t.relname)),
           0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.6', 'relational_table_metadata ohne source_id',
           (SELECT count(*) FROM relational_table_metadata WHERE source_id IS NULL), 0, 'Pflicht'
    UNION ALL
    SELECT 2, 'R2.7', 'Quellen ohne Werte in indicators und ohne relationale Tabelle',
           (SELECT count(*) FROM sources s
             WHERE NOT EXISTS (SELECT 1 FROM indicator_metadata x
                               WHERE x.source_id = s.id
                                 AND x.indicator_code IN (SELECT indicator_code FROM wert_codes))
               AND NOT EXISTS (SELECT 1 FROM relational_table_metadata r WHERE r.source_id = s.id)),
           NULL, 'Info'

    -- ---------- Prüfpunkt 3: Struktur ist fest ----------
    UNION ALL
    SELECT 3, 'R3.1', 'Aktive Codes mit leerer domain, category oder dimension',
           (SELECT count(*) FROM m
             WHERE coalesce(trim(domain), '') = '' OR coalesce(trim(category), '') = ''
                OR coalesce(trim(dimension), '') = ''), 0, 'Pflicht'
    UNION ALL
    SELECT 3, 'R3.2', 'Categories, die in mehr als einer Domain hängen',
           (SELECT count(*) FROM (SELECT category FROM m WHERE category IS NOT NULL
                                  GROUP BY category HAVING count(DISTINCT domain) > 1) c), 0, 'Pflicht'
    UNION ALL
    SELECT 3, 'R3.3', 'Dimensions, die in mehr als einer Category hängen',
           (SELECT count(*) FROM (SELECT dimension FROM m WHERE dimension IS NOT NULL
                                  GROUP BY dimension HAVING count(DISTINCT category) > 1) d), 0, 'Pflicht'
    UNION ALL
    SELECT 3, 'R3.4', 'Code-Präfix passt nicht zum short_code der Quelle',
           (SELECT count(*) FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
             WHERE split_part(x.indicator_code, ':', 1) <> s.short_code), 0, 'Pflicht'
    UNION ALL
    SELECT 3, 'R3.5', 'Anzahl Domains / Categories / Dimensions (zum Abgleich mit SIF v2)',
           NULL, NULL, 'Info: '
             || (SELECT count(DISTINCT domain) FROM m) || ' / '
             || (SELECT count(DISTINCT (domain, category)) FROM m) || ' / '
             || (SELECT count(DISTINCT (domain, category, dimension)) FROM m)

    -- ---------- Prüfpunkt 4: Metadaten vollständig ----------
    UNION ALL
    SELECT 4, 'R4.1', 'Aktive Codes ohne description',
           (SELECT count(*) FROM m WHERE coalesce(trim(description), '') = ''), 0, 'Pflicht'
    UNION ALL
    SELECT 4, 'R4.2', 'Aktive Codes ohne unit',
           (SELECT count(*) FROM m WHERE coalesce(trim(unit), '') = ''), 0, 'Pflicht'
    UNION ALL
    SELECT 4, 'R4.3', 'Aktive Codes ohne direction',
           (SELECT count(*) FROM m WHERE direction IS NULL), NULL, 'Info'
    UNION ALL
    SELECT 4, 'R4.4', 'Aktive Codes ohne scale_type',
           (SELECT count(*) FROM m WHERE scale_type IS NULL), NULL, 'Info'
    UNION ALL
    SELECT 4, 'R4.5', 'Aktive Codes ohne data_origin',
           (SELECT count(*) FROM m WHERE data_origin IS NULL), NULL, 'Info'
    UNION ALL
    SELECT 4, 'R4.6', 'Aktive Codes nicht von Julian freigegeben (metadata_reviewed_at)',
           (SELECT count(*) FROM m WHERE metadata_reviewed_at IS NULL), NULL, 'Info'
    UNION ALL
    SELECT 4, 'R4.7', 'Quellen ohne loaded_version',
           (SELECT count(*) FROM sources WHERE coalesce(trim(loaded_version), '') = ''), NULL, 'Info'
    UNION ALL
    SELECT 4, 'R4.8', 'Quellen ohne publisher oder license',
           (SELECT count(*) FROM sources
             WHERE coalesce(trim(publisher), '') = '' OR coalesce(trim(license), '') = ''), NULL, 'Info'

    -- ---------- Prüfpunkt 5: Grenzen dokumentiert ----------
    UNION ALL
    SELECT 5, 'R5.1', 'known_issues mit decision = to_fix (offen)',
           (SELECT count(*) FROM known_issues WHERE decision = 'to_fix'), 0, 'Pflicht'
    UNION ALL
    SELECT 5, 'R5.2', 'known_issues gesamt (accepted / wont_fix / fixed)',
           NULL, NULL, 'Info: '
             || (SELECT count(*) FILTER (WHERE decision = 'accepted') FROM known_issues) || ' / '
             || (SELECT count(*) FILTER (WHERE decision = 'wont_fix') FROM known_issues) || ' / '
             || (SELECT count(*) FILTER (WHERE decision = 'fixed')    FROM known_issues)
    UNION ALL
    SELECT 5, 'R5.3', 'Deprecated Codes, die noch Werte haben',
           (SELECT count(*) FROM indicator_metadata
             WHERE status = 'deprecated' AND indicator_code IN (SELECT indicator_code FROM wert_codes)),
           NULL, 'Info'
)
SELECT punkt, id, pruefung, ist, soll,
       CASE WHEN art <> 'Pflicht' THEN art
            WHEN ist IS NULL      THEN 'Pflicht: FEHLT'
            WHEN ist = soll       THEN 'Pflicht: OK'
            ELSE 'Pflicht: OFFEN' END AS bewertung
FROM pruefungen
ORDER BY punkt, id;


-- =============================================================================
-- TEIL 2: EINZELLISTEN (je höchstens 40 Zeilen)
-- =============================================================================
\echo ''
\echo '=== TEIL 2: EINZELLISTEN'

\echo ''
\echo '--- R1.1 NaN je Code'
SELECT indicator_code, count(*) AS nan_werte
FROM indicators WHERE value = 'NaN'::float
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;

\echo ''
\echo '--- R1.2 POLITY5-Sondercodes je Code'
SELECT indicator_code,
       count(*) FILTER (WHERE value = -66) AS m66,
       count(*) FILTER (WHERE value = -77) AS m77,
       count(*) FILTER (WHERE value = -88) AS m88
FROM indicators
WHERE indicator_code LIKE 'POLITY5:%' AND value IN (-66, -77, -88)
GROUP BY 1 ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R1.3 Dubletten je Code (Anzahl Land/Jahr-Paare mit mehr als einer Zeile)'
SELECT indicator_code, count(*) AS doppelte_paare,
       string_agg(DISTINCT srcs, ' ; ') AS source_id_kombinationen
FROM (SELECT indicator_code, iso_numeric, time_period,
             array_to_string(array_agg(source_id ORDER BY source_id NULLS FIRST), ',', 'NULL') AS srcs
      FROM indicators
      GROUP BY indicator_code, iso_numeric, time_period
      HAVING count(*) > 1) d
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;

\echo ''
\echo '--- R1.4 Werte außerhalb der Skala je Code (ohne NaN; known_issue = dokumentiert, zählt nicht)'
SELECT x.indicator_code, x.scale_min, x.scale_max,
       count(*) AS ausserhalb, min(i.value) AS min_wert, max(i.value) AS max_wert,
       (SELECT string_agg(k.id::text, ',') FROM known_issues k
         WHERE k.indicator_code = x.indicator_code AND k.decision IN ('accepted', 'wont_fix')) AS known_issue
FROM indicators i JOIN indicator_metadata x USING (indicator_code)
WHERE i.value <> 'NaN'::float
  AND ((x.scale_min IS NOT NULL AND i.value < x.scale_min)
    OR (x.scale_max IS NOT NULL AND i.value > x.scale_max))
GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 40;

\echo ''
\echo '--- R1.5 Ungültige time_period (Beispiele)'
SELECT indicator_code, time_period, count(*) AS zeilen
FROM indicators
WHERE time_period !~ '^-?\d{1,4}$' AND time_period <> 'static'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 40;

\echo ''
\echo '--- R1.9 Codes mit Befund in R1.1–R1.5, die per known_issue ausgenommen sind'
SELECT k.id AS known_issue, k.indicator_code, k.decision, k.title
FROM known_issues k
WHERE k.scope = 'indicator' AND k.decision IN ('accepted', 'wont_fix')
  AND EXISTS (SELECT 1 FROM indicators i JOIN indicator_metadata x USING (indicator_code)
              WHERE i.indicator_code = k.indicator_code
                AND (i.value = 'NaN'::float
                  OR (i.indicator_code LIKE 'POLITY5:%' AND i.value IN (-66, -77, -88))
                  OR (i.value <> 'NaN'::float AND ((x.scale_min IS NOT NULL AND i.value < x.scale_min)
                                                OR (x.scale_max IS NOT NULL AND i.value > x.scale_max)))
                  OR (i.time_period !~ '^-?\d{1,4}$' AND i.time_period <> 'static')))
ORDER BY 1;

\echo ''
\echo '--- R1.6 Sprünge des Länder-Medians > Faktor 5 (Kandidaten, kein Beweis; ohne latente Skalen und Länderzahl-Brüche)'
WITH jm AS (
    SELECT i.indicator_code, i.time_period::int AS jahr, count(DISTINCT i.iso_numeric) AS laender,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY i.value) AS median
    FROM indicators i JOIN indicator_metadata x USING (indicator_code)
    WHERE i.time_period ~ '^-?\d{1,4}$' AND i.value IS NOT NULL AND i.value <> 'NaN'::float
      AND x.scale_type IS DISTINCT FROM 'latent' AND coalesce(x.scale_min, 0) >= 0
    GROUP BY i.indicator_code, i.time_period
    HAVING count(DISTINCT i.iso_numeric) >= 20
)
SELECT a.indicator_code, a.jahr AS von, b.jahr AS nach,
       round(a.median::numeric, 3) AS median_von, round(b.median::numeric, 3) AS median_nach,
       round((b.median / a.median)::numeric, 2) AS faktor, a.laender, b.laender AS laender_nach
FROM jm a JOIN jm b ON b.indicator_code = a.indicator_code AND b.jahr = a.jahr + 1
WHERE a.median > 0 AND b.median > 0
  AND b.laender BETWEEN a.laender / 2.0 AND a.laender * 2.0
  AND (b.median / a.median > 5 OR b.median / a.median < 0.2)
ORDER BY greatest(b.median / a.median, a.median / b.median) DESC LIMIT 40;

\echo ''
\echo '--- R1.7 Codes mit nur einem Jahr'
SELECT indicator_code, min(time_period) AS jahr, count(*) AS werte
FROM indicators WHERE time_period <> 'static'
GROUP BY 1 HAVING count(DISTINCT time_period) = 1
ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R1.8 Werte im laufenden Jahr oder in der Zukunft je Code'
SELECT indicator_code, time_period, count(*) AS werte
FROM indicators
WHERE time_period ~ '^\d{4}$' AND time_period::int >= extract(year FROM current_date)::int
GROUP BY 1, 2 ORDER BY 1, 2 LIMIT 40;

\echo ''
\echo '--- R2.1 Werte ohne source_id je Code'
SELECT indicator_code, count(*) AS werte
FROM indicators WHERE source_id IS NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;

\echo ''
\echo '--- R2.2 source_id der Werte ≠ Metadaten-Quelle je Code'
SELECT i.indicator_code, x.source_id AS quelle_metadaten, i.source_id AS quelle_werte, count(*) AS werte
FROM indicators i JOIN indicator_metadata x USING (indicator_code)
WHERE i.source_id IS DISTINCT FROM x.source_id
GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 40;

\echo ''
\echo '--- R2.3 Codes ohne source_id in den Metadaten'
SELECT indicator_code, name FROM indicator_metadata WHERE source_id IS NULL
ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R2.4 Aktive Codes ohne Werte'
SELECT x.indicator_code, s.short_code, x.name
FROM indicator_metadata x LEFT JOIN sources s ON s.id = x.source_id
WHERE x.status = 'active'
  AND NOT EXISTS (SELECT 1 FROM indicators i WHERE i.indicator_code = x.indicator_code)
ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R2.5 Tabellen außerhalb public ohne relational_table_metadata'
SELECT t.schemaname, t.relname, t.n_live_tup AS zeilen_geschaetzt
FROM pg_stat_user_tables t
WHERE t.schemaname NOT IN ('public')
  AND NOT EXISTS (SELECT 1 FROM relational_table_metadata r
                  WHERE r.schema_name = t.schemaname AND r.table_name = t.relname)
ORDER BY 1, 2 LIMIT 40;

\echo ''
\echo '--- R2.6 relational_table_metadata ohne source_id'
SELECT schema_name, table_name FROM relational_table_metadata WHERE source_id IS NULL
ORDER BY 1, 2 LIMIT 40;

\echo ''
\echo '--- R2.7 Quellen ohne Werte und ohne relationale Tabelle'
SELECT s.id, s.short_code, s.name
FROM sources s
WHERE NOT EXISTS (SELECT 1 FROM indicator_metadata x
                  WHERE x.source_id = s.id
                    AND EXISTS (SELECT 1 FROM indicators i WHERE i.indicator_code = x.indicator_code))
  AND NOT EXISTS (SELECT 1 FROM relational_table_metadata r WHERE r.source_id = s.id)
ORDER BY 2 LIMIT 40;

\echo ''
\echo '--- R3.1 Leere Hierarchie je Quelle'
SELECT s.short_code, count(*) AS codes,
       count(*) FILTER (WHERE coalesce(trim(x.domain), '') = '')    AS ohne_domain,
       count(*) FILTER (WHERE coalesce(trim(x.category), '') = '')  AS ohne_category,
       count(*) FILTER (WHERE coalesce(trim(x.dimension), '') = '') AS ohne_dimension
FROM indicator_metadata x LEFT JOIN sources s ON s.id = x.source_id
WHERE x.status = 'active'
  AND (coalesce(trim(x.domain), '') = '' OR coalesce(trim(x.category), '') = ''
       OR coalesce(trim(x.dimension), '') = '')
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;

\echo ''
\echo '--- R3.2 Categories in mehreren Domains'
SELECT category, string_agg(DISTINCT domain, ' | ') AS domains, count(*) AS codes
FROM indicator_metadata WHERE status = 'active' AND category IS NOT NULL
GROUP BY 1 HAVING count(DISTINCT domain) > 1 ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R3.3 Dimensions in mehreren Categories'
SELECT dimension, string_agg(DISTINCT category, ' | ') AS categories, count(*) AS codes
FROM indicator_metadata WHERE status = 'active' AND dimension IS NOT NULL
GROUP BY 1 HAVING count(DISTINCT category) > 1 ORDER BY 1 LIMIT 40;

\echo ''
\echo '--- R3.4 Präfix ≠ short_code'
SELECT split_part(x.indicator_code, ':', 1) AS praefix, s.short_code, count(*) AS codes,
       min(x.indicator_code) AS beispiel
FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
WHERE split_part(x.indicator_code, ':', 1) <> s.short_code
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 40;

\echo ''
\echo '--- R3.5 Hierarchie komplett (Domain › Category › Dimension, Anzahl Codes)'
SELECT domain, category, dimension, count(*) AS codes
FROM indicator_metadata WHERE status = 'active'
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

\echo ''
\echo '--- R4 Metadaten-Lücken je Quelle (aktive Codes)'
SELECT s.short_code, count(*) AS codes,
       count(*) FILTER (WHERE coalesce(trim(x.description), '') = '') AS ohne_description,
       count(*) FILTER (WHERE coalesce(trim(x.unit), '') = '')        AS ohne_unit,
       count(*) FILTER (WHERE x.direction IS NULL)                     AS ohne_direction,
       count(*) FILTER (WHERE x.scale_type IS NULL)                    AS ohne_scale_type,
       count(*) FILTER (WHERE x.data_origin IS NULL)                   AS ohne_data_origin,
       count(*) FILTER (WHERE x.metadata_reviewed_at IS NULL)          AS nicht_freigegeben
FROM indicator_metadata x LEFT JOIN sources s ON s.id = x.source_id
WHERE x.status = 'active'
GROUP BY 1
HAVING count(*) FILTER (WHERE coalesce(trim(x.description), '') = '' OR coalesce(trim(x.unit), '') = ''
                           OR x.metadata_reviewed_at IS NULL) > 0
ORDER BY 3 DESC, 4 DESC;

\echo ''
\echo '--- R4.7/R4.8 Quellen-Register (leere Felder)'
SELECT short_code,
       (coalesce(trim(loaded_version), '') = '') AS ohne_version,
       (loaded_at IS NULL)                       AS ohne_ladedatum,
       (coalesce(trim(publisher), '') = '')      AS ohne_publisher,
       (coalesce(trim(license), '') = '')        AS ohne_license
FROM sources
WHERE coalesce(trim(loaded_version), '') = '' OR loaded_at IS NULL
   OR coalesce(trim(publisher), '') = '' OR coalesce(trim(license), '') = ''
ORDER BY 1;

\echo ''
\echo '--- R5 known_issues (alle)'
SELECT id, scope, coalesce(indicator_code, table_name, source_id::text, '') AS bezug,
       decision, title
FROM known_issues ORDER BY id;

\echo ''
\echo '=== ENDE Readiness-Check'
