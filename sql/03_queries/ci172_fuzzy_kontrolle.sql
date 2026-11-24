-- =====================================================================
-- CI-172 Fuzzy-Ländersuche: Kontrollabfragen (nur lesend)
-- Ausführen: psql -f sql/03_queries/ci172_fuzzy_kontrolle.sql > "Claude outputs/fuzzy_audit/kontrolle_db.txt"
-- Erwartung steht jeweils im Kommentar (Rohwerte von Claude aus den Rohdateien gelesen).
-- =====================================================================

-- 0. Wie heißen die betroffenen Länder in countries? Gibt es Kosovo überhaupt?
SELECT iso_numeric, iso_code_3, name
FROM countries
WHERE iso_code_3 IN ('NGA','NER','SRB','XKX','GBR','CAN','COL','TUR','CIV','COD','CPV','SWZ','TLS')
   OR name ILIKE '%kosovo%'
ORDER BY iso_code_3;

-- 1. Freedom House: Zeilen je Land (Verdacht: NER und XKX fehlen, NGA/SRB tragen fremde Werte)
SELECT c.iso_code_3, i.indicator_code, COUNT(*) AS n, MIN(i.time_period) AS von, MAX(i.time_period) AS bis
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code IN ('FH:PR','FH:CL') AND c.iso_code_3 IN ('NGA','NER','SRB','XKX')
GROUP BY 1,2 ORDER BY 1,2;

-- 1b. Stichprobe. Rohdatei FIW (PR, CL):
--     Niger   2010 (5,4)  2020 (4,4)  2023 (6,4)
--     Nigeria 2010 (4,4)  2020 (4,5)  2023 (4,5)
--     Kosovo  2010 (5,4)  2020 (4,4)  2023 (3,4)
--     Serbia  2010 (2,2)  2020 (4,3)  2023 (4,3)
--     Trägt NGA die Niger-Werte und SRB die Kosovo-Werte, ist der Fehler bestätigt.
SELECT c.iso_code_3, i.time_period,
       MAX(CASE WHEN i.indicator_code='FH:PR' THEN i.value END) AS pr,
       MAX(CASE WHEN i.indicator_code='FH:CL' THEN i.value END) AS cl
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code IN ('FH:PR','FH:CL') AND c.iso_code_3 IN ('NGA','NER','SRB','XKX')
  AND i.time_period IN ('2010','2020','2023')
GROUP BY 1,2 ORDER BY 1,2;

-- 2. HENLEY: Rohdatei visa required: Kosovo 75, Serbia 41.
SELECT c.iso_code_3, i.indicator_code, i.time_period, i.value
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'HENLEY:%' AND c.iso_code_3 IN ('SRB','XKX')
ORDER BY 1,2;

-- 3. TI:CPI (bereits bestätigt, hier nur Kontrollzahl vorher): Zeilen NGA/NER
SELECT c.iso_code_3, COUNT(*) AS n, MIN(time_period), MAX(time_period)
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code = 'TI:CPI' AND c.iso_code_3 IN ('NGA','NER')
GROUP BY 1 ORDER BY 1;

-- 4. SAMAYO: England/Scotland/Wales/Nordirland landen alle auf GBR.
--    country_facts und national_dishes überschreiben (DO UPDATE) → letzter Name gewinnt.
SELECT 'country_facts' AS tab, iso_numeric, country_name, government_type, driving_side, calling_code
FROM culture.country_facts WHERE iso_numeric = (SELECT iso_numeric FROM countries WHERE iso_code_3='GBR');
SELECT 'national_dishes' AS tab, iso_numeric, country_name, dish
FROM culture.national_dishes WHERE iso_numeric = (SELECT iso_numeric FROM countries WHERE iso_code_3='GBR');
SELECT c.iso_code_3, i.indicator_code, i.value
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'SAMAYO:%' AND c.iso_code_3 = 'GBR' ORDER BY 2;

-- 5. Tabellen, die den Rohnamen mitspeichern: jede Zeile, deren Name nicht zum Land passt.
--    (Liste wird lang; interessant sind Paare wie Niger→NGA, Kosovo→SRB, Wales→GBR.)
SELECT 'country_facts' AS tab, f.country_name AS rohname, c.iso_code_3, c.name
FROM culture.country_facts f JOIN countries c USING (iso_numeric)
WHERE LOWER(f.country_name) <> LOWER(c.name)
UNION ALL
SELECT 'national_dishes', d.country_name, c.iso_code_3, c.name
FROM culture.national_dishes d JOIN countries c USING (iso_numeric)
WHERE LOWER(d.country_name) <> LOWER(c.name)
UNION ALL
SELECT DISTINCT 'epr', e.country_name, c.iso_code_3, c.name
FROM history.ethnic_groups e JOIN countries c USING (iso_numeric)
WHERE LOWER(e.country_name) <> LOWER(c.name)
ORDER BY 1,2;

-- 6. CAF: Columbia → Kanada (CI-1 bereits per Migration korrigiert; Kontrolle, dass es so bleibt)
SELECT c.iso_code_3, i.time_period, COUNT(*)
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'CAF_WGI:%' AND c.iso_code_3 IN ('CAN','COL') AND i.time_period = '2011'
GROUP BY 1,2;
