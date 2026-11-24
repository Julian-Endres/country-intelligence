-- CI-171 E1 / #8: Ist WB:poverty_3_day (über OWID) dieselbe Reihe wie WB:SI.POV.DDAY (WB direkt)?
-- Nur lesen. Aufruf (Shell):
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-24_poverty_vergleich.sql > logs/2026-11-24_poverty_vergleich.txt

\echo '--- 1) Umfang je Code'
SELECT indicator_code, count(*) AS werte, count(DISTINCT iso_numeric) AS laender,
       min(time_period) AS von, max(time_period) AS bis,
       round(min(value)::numeric, 2) AS min, round(max(value)::numeric, 2) AS max
FROM indicators
WHERE indicator_code IN ('WB:poverty_3_day', 'WB:SI.POV.DDAY')
GROUP BY 1;

-- FULL JOIN: alle Land-Jahr-Paare aus beiden Reihen, auch wenn nur eine einen Wert hat.
\echo ''
\echo '--- 2) Abgleich Land x Jahr'
WITH o AS (SELECT iso_numeric, time_period, value FROM indicators WHERE indicator_code = 'WB:poverty_3_day'),
     w AS (SELECT iso_numeric, time_period, value FROM indicators WHERE indicator_code = 'WB:SI.POV.DDAY'),
     j AS (SELECT coalesce(o.iso_numeric, w.iso_numeric) AS iso, coalesce(o.time_period, w.time_period) AS jahr,
                  o.value AS owid, w.value AS wb
           FROM o FULL JOIN w ON o.iso_numeric = w.iso_numeric AND o.time_period = w.time_period)
SELECT count(*) FILTER (WHERE owid IS NOT NULL AND wb IS NOT NULL)                 AS beide,
       count(*) FILTER (WHERE owid IS NOT NULL AND wb IS NOT NULL
                          AND abs(owid - wb) < 0.05)                               AS gleich_auf_0_05,
       round(max(abs(owid - wb))::numeric, 2)                                      AS max_abweichung,
       count(*) FILTER (WHERE owid IS NOT NULL AND wb IS NULL)                     AS nur_owid,
       count(*) FILTER (WHERE owid IS NULL AND wb IS NOT NULL)                     AS nur_wb
FROM j;

\echo ''
\echo '--- 3) Die 15 größten Abweichungen'
WITH o AS (SELECT iso_numeric, time_period, value FROM indicators WHERE indicator_code = 'WB:poverty_3_day'),
     w AS (SELECT iso_numeric, time_period, value FROM indicators WHERE indicator_code = 'WB:SI.POV.DDAY')
SELECT c.name AS land, o.time_period AS jahr, round(o.value::numeric, 2) AS owid, round(w.value::numeric, 2) AS wb
FROM o JOIN w USING (iso_numeric, time_period)
LEFT JOIN countries c USING (iso_numeric)
ORDER BY abs(o.value - w.value) DESC
LIMIT 15;

\echo ''
\echo '--- 4) Woher kommen die Werte nur bei OWID? (Jahre)'
SELECT o.time_period AS jahr, count(*) AS werte_nur_owid
FROM indicators o
WHERE o.indicator_code = 'WB:poverty_3_day'
  AND NOT EXISTS (SELECT 1 FROM indicators w WHERE w.indicator_code = 'WB:SI.POV.DDAY'
                  AND w.iso_numeric = o.iso_numeric AND w.time_period = o.time_period)
GROUP BY 1 ORDER BY 1;
