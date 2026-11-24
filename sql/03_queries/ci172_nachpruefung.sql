-- =====================================================================
-- CI-172 Nachprüfung der Verdachtsfälle aus ci172_verwechslungspaare.sql (nur lesend)
-- Ausführen (Shell):
--   psql -U postgres -d country_intelligence -f sql/03_queries/ci172_nachpruefung.sql \
--        > "Claude outputs/fuzzy_audit/nachpruefung.txt"
-- =====================================================================

-- 1. WHR: Loader ordnet notfalls per Teilstring zu (load_whr.py Z. 123–125).
--    Rohdatei (whr26_data_figure_2_1.csv), Life evaluation:
--      Congo        2015 4.236 · 2020 5.342 · 2024 5.030 · 2025 4.456
--      DR Congo     2015 4.272 · 2020 –     · 2024 3.469 · 2025 3.761
--      Cyprus       2015 5.546 · 2020 6.223
--      North Cyprus 2015 5.771 · 2020 5.536
--      Hong Kong    2015 5.458 · 2020 5.477 · 2024 5.491 · 2025 5.569
--    Verdacht: COD trägt in manchen Jahren Congo-Werte, COG fehlt; CYP 2015 = North Cyprus.
SELECT c.iso_code_3, i.time_period, i.value
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code = 'WHR:life_evaluation'
  AND c.iso_code_3 IN ('COG','COD','CYP','HKG','CHN')
  AND i.time_period IN ('2015','2020','2024','2025')
ORDER BY 1, 2;

-- 2. KOF: Die Rohdatei nutzt alte Codes (zar, rom, tmp, ado, wbg), der Loader kennt nur heutige ISO3.
--    Erwartung: 0 Werte für COD, ROU, TLS, AND, PSE (Kontrolle DEU: > 0).
SELECT c.iso_code_3, COUNT(i.iso_numeric) AS werte
FROM countries c
LEFT JOIN indicators i ON i.iso_numeric = c.iso_numeric
                      AND i.source_id = (SELECT id FROM sources WHERE short_code = 'KOF')
WHERE c.iso_code_3 IN ('COD','ROU','TLS','AND','PSE','DEU')
GROUP BY 1 ORDER BY 1;

-- 3. EPR und UNESCO_ICH: Nord- und Südkorea mit 100 % gleichen Werten. Echte Gleichheit oder Doppelung?
SELECT s.short_code, i.indicator_code, c.iso_code_3,
       COUNT(*) AS n, MIN(i.value) AS min, MAX(i.value) AS max,
       MIN(i.time_period) AS von, MAX(i.time_period) AS bis
FROM indicators i
JOIN countries c USING (iso_numeric)
JOIN sources s ON s.id = i.source_id
WHERE s.short_code IN ('EPR','UNESCO_ICH') AND c.iso_code_3 IN ('PRK','KOR')
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

-- 4. WVS: Australien fehlt, Österreich ist da. Welche Jahre? (Kontrolle DEU, USA)
SELECT c.iso_code_3, MIN(i.time_period) AS von, MAX(i.time_period) AS bis,
       COUNT(DISTINCT i.time_period) AS jahre
FROM indicators i
JOIN countries c USING (iso_numeric)
JOIN sources s ON s.id = i.source_id
WHERE s.short_code = 'WVS' AND c.iso_code_3 IN ('AUT','AUS','DEU','USA')
GROUP BY 1 ORDER BY 1;

-- 5. Stille Verluste über ALLE Quellen: Länder, die in mindestens 90 % der großen Quellen
--    (je >= 150 Länder) stehen, in einer davon aber fehlen. Findet KOF-Fälle (alte Codes)
--    und verworfene Namen, die die Paar-Abfrage nicht sieht. Verdachtsliste, kein Beweis.
CREATE TEMP TABLE ql AS SELECT DISTINCT source_id, iso_numeric FROM indicators;
CREATE TEMP TABLE gross AS SELECT source_id FROM ql GROUP BY 1 HAVING COUNT(*) >= 150;
CREATE TEMP TABLE verbreitung AS
SELECT q.iso_numeric, COUNT(*)::numeric / (SELECT COUNT(*) FROM gross) AS anteil
FROM ql q JOIN gross g USING (source_id)
GROUP BY 1;

SELECT s.short_code,
       (SELECT COUNT(*) FROM ql WHERE ql.source_id = g.source_id) AS n_laender,
       COUNT(*) AS fehlen,
       string_agg(c.iso_code_3, ' ' ORDER BY c.iso_code_3) AS fehlende_laender
FROM gross g
JOIN sources s ON s.id = g.source_id
JOIN verbreitung v ON v.anteil >= 0.9
JOIN countries c ON c.iso_numeric = v.iso_numeric
WHERE NOT EXISTS (SELECT 1 FROM ql WHERE ql.source_id = g.source_id AND ql.iso_numeric = v.iso_numeric)
GROUP BY s.short_code, g.source_id
ORDER BY fehlen DESC, s.short_code;
