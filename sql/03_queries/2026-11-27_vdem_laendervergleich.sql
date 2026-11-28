-- ============================================================
-- V-Dem Ländervergleich: Südafrika, Nigeria, Paraguay, Indonesien, Belgien
-- Stand: 27.11.2026 · nur lesend (SELECT), ausführen in DBeaver oder psql
-- Aufruf psql:  psql -d <db> -f sql/03_queries/2026-11-27_vdem_laendervergleich.sql
--
-- Skalen: alle v2x_-Indizes 0–1 (höher = mehr Demokratie/Freiheit),
--         AUSNAHME v2x_corr: höher = MEHR Korruption (läuft umgekehrt!)
--         v2x_regime: 0 = geschl. Autokratie, 1 = Wahlautokratie,
--                     2 = Wahldemokratie, 3 = liberale Demokratie
-- ============================================================


-- ------------------------------------------------------------
-- Schritt 0: Kontrolle – sind alle 5 Länder und alle Codes da?
-- Erwartung: 5 Länder × 12 Codes = 60 Zeilen, jede mit letztem Jahr.
-- Fehlt eine Zeile → Befund, nicht ignorieren.
-- ------------------------------------------------------------
SELECT c.iso_code_3, i.indicator_code,
       COUNT(*)                       AS jahre,
       MIN(i.time_period::int)        AS von,
       MAX(i.time_period::int)        AS bis
FROM indicators i
JOIN countries c USING (iso_numeric)
WHERE c.iso_code_3 IN ('ZAF','NGA','PRY','IDN','BEL')
  AND i.indicator_code IN ('VDEM:v2x_polyarchy','VDEM:v2x_libdem','VDEM:v2x_partipdem',
                           'VDEM:v2x_delibdem','VDEM:v2x_egaldem','VDEM:v2x_regime',
                           'VDEM:v2x_rule','VDEM:v2x_corr','VDEM:v2x_civlib',
                           'VDEM:v2x_freexp','VDEM:v2x_gender','VDEM:v2cacamps')
GROUP BY 1,2
ORDER BY 1,2;


-- ------------------------------------------------------------
-- Vergleich 1: Demokratie-Profil im letzten verfügbaren Jahr
-- Fünf Demokratie-"Brillen" nebeneinander + Regimetyp.
-- Frage: Wo ist Wahl-Demokratie stark, aber liberal/egalitär schwach?
-- ------------------------------------------------------------
WITH letzte AS (
  SELECT i.iso_numeric, MAX(i.time_period::int) AS jahr
  FROM indicators i
  WHERE i.indicator_code = 'VDEM:v2x_polyarchy'
  GROUP BY 1
)
SELECT c.name, l.jahr,
  ROUND(MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_polyarchy')::numeric,3) AS wahl_dem,
  ROUND(MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_libdem')::numeric,3)    AS liberal,
  ROUND(MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_partipdem')::numeric,3) AS partizipativ,
  ROUND(MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_delibdem')::numeric,3)  AS deliberativ,
  ROUND(MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_egaldem')::numeric,3)   AS egalitaer,
  CASE MAX(i.value) FILTER (WHERE i.indicator_code='VDEM:v2x_regime')
       WHEN 0 THEN 'geschl. Autokratie' WHEN 1 THEN 'Wahlautokratie'
       WHEN 2 THEN 'Wahldemokratie'     WHEN 3 THEN 'liberale Demokratie' END AS regime
FROM indicators i
JOIN countries c USING (iso_numeric)
JOIN letzte l ON l.iso_numeric = i.iso_numeric AND l.jahr = i.time_period::int
WHERE c.iso_code_3 IN ('ZAF','NGA','PRY','IDN','BEL')
  AND i.indicator_code LIKE 'VDEM:v2x_%'
GROUP BY c.name, l.jahr
ORDER BY wahl_dem DESC;


-- ------------------------------------------------------------
-- Vergleich 2: Demokratisierungs-Pfade 1975–heute (Wahl-Demokratie)
-- Je Land eine Spalte, alle 5 Jahre plus letztes Jahr.
-- Erwartbare Wendepunkte: PRY 1989 (Stroessner), ZAF 1994 (Apartheid-Ende),
-- IDN 1998 (Reformasi), NGA 1999 (Ende Militärherrschaft); BEL als Kontrollfall.
-- ------------------------------------------------------------
SELECT i.time_period::int AS jahr,
  ROUND(MAX(i.value) FILTER (WHERE c.iso_code_3='BEL')::numeric,2) AS belgien,
  ROUND(MAX(i.value) FILTER (WHERE c.iso_code_3='ZAF')::numeric,2) AS suedafrika,
  ROUND(MAX(i.value) FILTER (WHERE c.iso_code_3='IDN')::numeric,2) AS indonesien,
  ROUND(MAX(i.value) FILTER (WHERE c.iso_code_3='PRY')::numeric,2) AS paraguay,
  ROUND(MAX(i.value) FILTER (WHERE c.iso_code_3='NGA')::numeric,2) AS nigeria
FROM indicators i
JOIN countries c USING (iso_numeric)
WHERE i.indicator_code = 'VDEM:v2x_polyarchy'
  AND c.iso_code_3 IN ('ZAF','NGA','PRY','IDN','BEL')
  AND i.time_period::int >= 1975
  AND (i.time_period::int % 5 = 0
       OR i.time_period::int IN (1989,1994,1998,1999)
       OR i.time_period::int = (SELECT MAX(time_period::int) FROM indicators
                                WHERE indicator_code='VDEM:v2x_polyarchy'))
GROUP BY 1
ORDER BY 1;


-- ------------------------------------------------------------
-- Vergleich 3: Rechtsstaat, Freiheiten, Polarisierung – 2015 vs. letztes Jahr
-- Zeigt, wer sich in 10 Jahren verbessert/verschlechtert hat.
-- v2x_corr: Δ positiv = MEHR Korruption (schlechter)!
-- v2cacamps: Polarisierung, ungefähr –4 bis +4, höher = polarisierter.
-- ------------------------------------------------------------
WITH basis AS (
  SELECT c.name, i.indicator_code, i.time_period::int AS jahr, i.value
  FROM indicators i
  JOIN countries c USING (iso_numeric)
  WHERE c.iso_code_3 IN ('ZAF','NGA','PRY','IDN','BEL')
    AND i.indicator_code IN ('VDEM:v2x_rule','VDEM:v2x_corr','VDEM:v2x_civlib',
                             'VDEM:v2x_freexp','VDEM:v2x_gender','VDEM:v2cacamps')
),
letzt AS (SELECT MAX(jahr) AS j FROM basis)
SELECT b.name,
       REPLACE(b.indicator_code,'VDEM:','')                                   AS indikator,
       ROUND(MAX(b.value) FILTER (WHERE b.jahr = 2015)::numeric,2)             AS w_2015,
       ROUND(MAX(b.value) FILTER (WHERE b.jahr = l.j)::numeric,2)              AS w_letzt,
       ROUND((MAX(b.value) FILTER (WHERE b.jahr = l.j)
            - MAX(b.value) FILTER (WHERE b.jahr = 2015))::numeric,2)           AS delta,
       l.j                                                                     AS letztes_jahr
FROM basis b CROSS JOIN letzt l
GROUP BY b.name, b.indicator_code, l.j
ORDER BY b.indicator_code, w_letzt DESC;
