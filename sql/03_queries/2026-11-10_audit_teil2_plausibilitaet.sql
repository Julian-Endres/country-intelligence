-- DB-Audit Teil 2: Plausibilität der Werte (10.11.2026)
-- Nur lesend. Ausführen mit psql -f, Ausgabe in eine Datei (siehe Anleitung im Chat).
-- Einige Abfragen gehen über alle 4,2 Mio. Werte; Laufzeit mehrere Minuten möglich.

SET default_transaction_read_only = on;
SET statement_timeout = '600s';
SET work_mem = '256MB';
\pset pager off
\pset null '∅'

\echo '=== P01 Doppelzeilen (gleiches Land, Code, Periode): weichen die Werte voneinander ab? ==='
WITH d AS (
  SELECT indicator_code, iso_numeric, time_period,
         COUNT(*) AS n, MIN(value) AS vmin, MAX(value) AS vmax,
         array_agg(COALESCE(source_id::text, 'NULL') ORDER BY source_id) AS quellen
  FROM indicators
  GROUP BY 1, 2, 3
  HAVING COUNT(*) > 1
)
SELECT indicator_code,
       COUNT(*)                                        AS doppelte,
       COUNT(*) FILTER (WHERE vmax - vmin > 1e-9)      AS mit_abweichung,
       MAX(n)                                          AS max_zeilen_je_fall,
       (array_agg(DISTINCT array_to_string(quellen, '+')))[1:3] AS quellen_muster,
       (array_agg(iso_numeric || ' ' || time_period || ': ' || vmin || ' / ' || vmax
                  ORDER BY vmax - vmin DESC))[1]       AS groesste_abweichung
FROM d
GROUP BY 1
ORDER BY 2 DESC;

\echo '=== P02 obs_status B und U: welche Codes, welche Jahre? ==='
SELECT obs_status, indicator_code, source_id, COUNT(*) AS n, MIN(time_period), MAX(time_period)
FROM indicators
WHERE obs_status <> 'A'
GROUP BY 1, 2, 3
ORDER BY 1, 2;

\echo '=== P03 Einheit 0-1 (Index), aber Werte außerhalb [0,1] ==='
SELECT m.indicator_code, m.unit, c.min_value, c.max_value, c.n_values
FROM indicator_metadata m
JOIN indicator_coverage c USING (indicator_code)
WHERE (m.unit ILIKE '%0-1%' OR m.unit ILIKE '%0 to 1%' OR m.unit ILIKE '%0–1%')
  AND (c.min_value < 0 OR c.max_value > 1)
ORDER BY 1;

\echo '=== P04 Prozent-Einheit, aber Werte < 0 oder > 100 (zur Durchsicht, nicht alles ist falsch) ==='
SELECT m.indicator_code, m.unit, ROUND(c.min_value::numeric, 2) AS min, ROUND(c.max_value::numeric, 2) AS max, c.n_values
FROM indicator_metadata m
JOIN indicator_coverage c USING (indicator_code)
WHERE (m.unit ILIKE '%\%%' OR m.unit ILIKE '%percent%' OR m.name ILIKE '%(\%%')
  AND (c.min_value < 0 OR c.max_value > 100)
ORDER BY c.max_value DESC
LIMIT 60;

\echo '=== P05 Negative Werte bei Einheiten, die nicht negativ sein können (Anzahl, Personen, Fläche, Index ...) ==='
SELECT m.indicator_code, m.unit, ROUND(c.min_value::numeric, 3) AS min, c.n_values
FROM indicator_metadata m
JOIN indicator_coverage c USING (indicator_code)
WHERE c.min_value < 0
  AND (m.unit ILIKE ANY (ARRAY['%person%', '%people%', '%number%', '%count%', '%km%', '%hectare%',
                               '%tonne%', '%years%', '%per 100%', '%per 1000%', '%per 1,000%', '%kcal%', '%rate%'])
       OR m.indicator_code ILIKE ANY (ARRAY['%POP.TOTL%', '%_count%', '%n_%']))
ORDER BY 1
LIMIT 60;

\echo '=== P06 Sprünge von Jahr zu Jahr (Faktor > 10 oder < 0,1, beide Werte > 0) ==='
WITH s AS (
  SELECT indicator_code, iso_numeric, time_period::int AS y, value,
         LAG(value)                OVER w AS prev,
         LAG(time_period::int)     OVER w AS prev_y
  FROM indicators
  WHERE time_period ~ '^\d{4}$' AND value <> 'NaN'::float8
  WINDOW w AS (PARTITION BY indicator_code, iso_numeric, source_id ORDER BY time_period::int)
)
SELECT indicator_code,
       COUNT(*) AS n_spruenge,
       COUNT(DISTINCT iso_numeric) AS n_laender,
       (array_agg(iso_numeric || ' ' || prev_y || '→' || y || ': ' || ROUND(prev::numeric, 3) || ' → ' || ROUND(value::numeric, 3)
                  ORDER BY GREATEST(value / prev, prev / value) DESC))[1] AS extremster
FROM s
WHERE prev_y = y - 1 AND prev > 0 AND value > 0
  AND (value / prev > 10 OR value / prev < 0.1)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 50;

\echo '=== P07 Ausreißer: Maximum weit über dem 99. Perzentil (bzw. Minimum weit unter P1) ==='
WITH p AS (
  SELECT indicator_code,
         percentile_cont(0.01) WITHIN GROUP (ORDER BY value) AS p01,
         percentile_cont(0.99) WITHIN GROUP (ORDER BY value) AS p99,
         MIN(value) AS vmin, MAX(value) AS vmax, COUNT(*) AS n
  FROM indicators
  WHERE value <> 'NaN'::float8
  GROUP BY 1
  HAVING COUNT(*) >= 100
)
SELECT indicator_code, n,
       ROUND(vmin::numeric, 3) AS min, ROUND(p01::numeric, 3) AS p01,
       ROUND(p99::numeric, 3) AS p99, ROUND(vmax::numeric, 3) AS max,
       ROUND(((vmax - p99) / NULLIF(p99 - p01, 0))::numeric, 1) AS ueberstand_oben,
       ROUND(((p01 - vmin) / NULLIF(p99 - p01, 0))::numeric, 1) AS ueberstand_unten
FROM p
WHERE (vmax - p99) > 10 * NULLIF(p99 - p01, 0)
   OR (p01 - vmin) > 10 * NULLIF(p99 - p01, 0)
ORDER BY GREATEST(COALESCE((vmax - p99) / NULLIF(p99 - p01, 0), 0),
                  COALESCE((p01 - vmin) / NULLIF(p99 - p01, 0), 0)) DESC
LIMIT 50;

\echo '=== P08 Eingefrorene Reihen: Land mit >= 10 Jahren und immer demselben Wert ==='
WITH r AS (
  SELECT indicator_code, iso_numeric, COUNT(*) AS n, MIN(value) AS vmin, MAX(value) AS vmax
  FROM indicators
  WHERE time_period ~ '^\d{4}$'
  GROUP BY 1, 2
  HAVING COUNT(*) >= 10 AND MIN(value) = MAX(value)
)
SELECT indicator_code, COUNT(*) AS n_laender_konstant,
       (SELECT COUNT(DISTINCT iso_numeric) FROM indicators i WHERE i.indicator_code = r.indicator_code) AS n_laender_gesamt,
       (array_agg(iso_numeric || '=' || vmin))[1:3] AS beispiele
FROM r
GROUP BY 1
ORDER BY 2 DESC
LIMIT 40;

\echo '=== P09 Unvollständiges letztes Jahr (Länderzahl < 50 % des Maximums) ==='
WITH j AS (
  SELECT indicator_code, time_period::int AS y, COUNT(DISTINCT iso_numeric) AS n
  FROM indicators
  WHERE time_period ~ '^\d{4}$'
  GROUP BY 1, 2
), a AS (
  SELECT indicator_code, MAX(n) AS n_max, MAX(y) AS y_last
  FROM j GROUP BY 1
)
SELECT a.indicator_code, a.y_last, j.n AS n_letztes_jahr, a.n_max,
       (SELECT j2.n FROM j j2 WHERE j2.indicator_code = a.indicator_code AND j2.y = a.y_last - 1) AS n_vorjahr
FROM a JOIN j ON j.indicator_code = a.indicator_code AND j.y = a.y_last
WHERE j.n < 0.5 * a.n_max
ORDER BY a.y_last DESC, a.indicator_code
LIMIT 80;

\echo '=== P10 Lücken: Jahre zwischen erstem und letztem Jahr ohne einen einzigen Wert ==='
WITH j AS (
  SELECT indicator_code, COUNT(DISTINCT time_period::int) AS n_jahre,
         MIN(time_period::int) AS y0, MAX(time_period::int) AS y1
  FROM indicators
  WHERE time_period ~ '^\d{4}$' AND time_period::int >= 1900
  GROUP BY 1
)
SELECT indicator_code, y0, y1, n_jahre, (y1 - y0 + 1) - n_jahre AS fehlende_jahre
FROM j
WHERE (y1 - y0 + 1) - n_jahre > 0
ORDER BY 5 DESC
LIMIT 50;

\echo '=== P11 Länder mit auffällig wenig Daten (weniger als 20 Indikatoren) ==='
SELECT c.iso_code_3, c.name, c.region, COUNT(DISTINCT i.indicator_code) AS n_codes, COUNT(*) AS n_werte
FROM countries c
JOIN indicators i USING (iso_numeric)
GROUP BY 1, 2, 3
HAVING COUNT(DISTINCT i.indicator_code) < 20
ORDER BY 4;

\echo '=== P12 Relationale Tabellen: Länder-Spalten leer oder nicht in countries ==='
SELECT format(
  'SELECT %L AS tabelle, %L AS spalte, COUNT(*) AS zeilen, COUNT(*) FILTER (WHERE %I IS NULL) AS leer, COUNT(*) FILTER (WHERE %I IS NOT NULL AND %I::text NOT IN (SELECT iso_numeric FROM countries)) AS unbekannt FROM %I.%I',
  table_schema || '.' || table_name, column_name, column_name, column_name, column_name, table_schema, table_name)
FROM information_schema.columns
WHERE table_schema NOT IN ('public', 'pg_catalog', 'information_schema')
  AND column_name IN ('iso_numeric', 'partner_iso_numeric', 'iso_numeric_src', 'iso_numeric_tgt', 'colonizer_iso', 'colony_iso')
ORDER BY table_schema, table_name, column_name
\gexec

\echo '=== P13 Relationale Tabellen: Spalten mit Ländercodes (zur Kontrolle der Liste in P12) ==='
SELECT table_schema || '.' || table_name AS tabelle, string_agg(column_name, ', ' ORDER BY ordinal_position) AS spalten
FROM information_schema.columns
WHERE table_schema NOT IN ('public', 'pg_catalog', 'information_schema')
GROUP BY 1
ORDER BY 1;

\echo '=== P14 Relationale Tabellen: Jahresbereich ==='
SELECT format('SELECT %L AS tabelle, %L AS spalte, MIN(%I) AS von, MAX(%I) AS bis, COUNT(*) FILTER (WHERE %I IS NULL) AS leer FROM %I.%I',
              table_schema || '.' || table_name, column_name, column_name, column_name, column_name, table_schema, table_name)
FROM information_schema.columns
WHERE table_schema NOT IN ('public', 'pg_catalog', 'information_schema')
  AND column_name IN ('year', 'year_from', 'year_to', 'election_year', 'start_year', 'end_year')
ORDER BY table_schema, table_name, column_name
\gexec

\echo '=== P15 Comtrade: Wertebereich und Jahre je Fluss ==='
SELECT 'trade_products' AS tabelle, flow_code, COUNT(*) AS n, MIN(year), MAX(year),
       COUNT(*) FILTER (WHERE fob_value IS NULL) AS fob_leer,
       COUNT(*) FILTER (WHERE fob_value < 0) AS fob_negativ,
       COUNT(DISTINCT iso_numeric) AS n_laender
FROM trade.trade_products GROUP BY 1, 2
UNION ALL
SELECT 'trade_partners', flow_code, COUNT(*), MIN(year), MAX(year),
       COUNT(*) FILTER (WHERE fob_value IS NULL),
       COUNT(*) FILTER (WHERE fob_value < 0),
       COUNT(DISTINCT iso_numeric)
FROM trade.trade_partners GROUP BY 1, 2
ORDER BY 1, 2;

\echo '=== P16 Comtrade: Länder je Jahr (Produkte), um Meldelücken zu sehen ==='
SELECT year, COUNT(DISTINCT iso_numeric) AS n_laender_produkte,
       (SELECT COUNT(DISTINCT iso_numeric) FROM trade.trade_partners tp WHERE tp.year = t.year) AS n_laender_partner
FROM trade.trade_products t
GROUP BY year
ORDER BY year;

\echo '=== P17 Bolivien-Stichprobe: letzte Werte der Leitindikatoren aus der Encyclopedia ==='
SELECT DISTINCT ON (indicator_code) indicator_code, time_period, ROUND(value::numeric, 3) AS wert, source_id
FROM indicators
WHERE iso_numeric = '068'
  AND indicator_code IN ('WB:SP.POP.TOTL', 'WB:NY.GDP.PCAP.CD', 'WB:FI.RES.TOTL.MO', 'WB:PA.NUS.FCRF',
                         'VDEM:v2x_polyarchy', 'VDEM:v2x_libdem', 'UNODC:homicide_rate', 'UNODC:prison_occupancy',
                         'ILO:SDG_0831_SEX_ECO_RT', 'WB:SL.TLF.CACT.ZS')
  AND time_period ~ '^\d{4}$'
ORDER BY indicator_code, time_period::int DESC;

\echo '=== ENDE Teil 2 ==='
