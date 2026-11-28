-- =====================================================================
-- CI-172: unabhängige Kontrolle nach der Quarantäne-Migration (nur lesend)
-- Aufruf (Shell, Repo-Wurzel):
--   psql -U postgres -d country_intelligence -X -q -P pager=off -f sql/03_queries/ci172_kontrolle_danach.sql \
--        > logs/migrations/2026-11-24_ci172_kontrolle_danach.txt 2>&1
-- Erwartet: TI NER 13 · TI NGA 0 · FH NER 88 · FH NGA 0 · FH SRB 6 · HENLEY SRB 0 · WHR COG 52 · WHR COD 4
--           WHR CYP 52 · EPR 0 · Gruppen NER 60 · Gruppen Kosovo 0 · GBR-Fakten 0 · known_issues CI-172 14
--           · Werte gesamt 4.091.229
-- =====================================================================

SELECT 'TI NER' AS pruefung, count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '562'
UNION ALL SELECT 'TI NGA', count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '566'
UNION ALL SELECT 'FH NER', count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric = '562'
UNION ALL SELECT 'FH NGA', count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric = '566'
UNION ALL SELECT 'FH SRB', count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric = '688'
UNION ALL SELECT 'HENLEY SRB', count(*) FROM indicators WHERE indicator_code LIKE 'HENLEY:%' AND iso_numeric = '688'
UNION ALL SELECT 'WHR COG', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '178'
UNION ALL SELECT 'WHR COD', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '180'
UNION ALL SELECT 'WHR CYP', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '196'
UNION ALL SELECT 'EPR', count(*) FROM indicators WHERE indicator_code LIKE 'EPR:%'
UNION ALL SELECT 'Gruppen NER', count(*) FROM history.ethnic_groups WHERE iso_numeric = '562'
UNION ALL SELECT 'Gruppen Kosovo', count(*) FROM history.ethnic_groups WHERE country_name = 'Kosovo'
UNION ALL SELECT 'GBR-Fakten', (SELECT count(*) FROM culture.country_facts WHERE iso_numeric = '826')
                             + (SELECT count(*) FROM culture.national_dishes WHERE iso_numeric = '826')
UNION ALL SELECT 'known_issues CI-172', count(*) FROM known_issues WHERE title LIKE 'CI-172%'
UNION ALL SELECT 'Werte gesamt', count(*) FROM indicators;

-- Stichproben gegen die Rohdateien
--   Niger TI 2024 = 34 (TI-Datei), Niger FH PR/CL 2010 = 5/4 (FIW), Republik Kongo WHR life_evaluation 2024 = 5,03,
--   DR Kongo WHR life_evaluation 2015 = 4,272 (blieb)
SELECT c.iso_code_3, i.indicator_code, i.time_period, i.value
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE (i.indicator_code = 'TI:CPI' AND c.iso_code_3 = 'NER' AND i.time_period = '2024')
   OR (i.indicator_code IN ('FH:PR','FH:CL') AND c.iso_code_3 = 'NER' AND i.time_period = '2010')
   OR (i.indicator_code = 'WHR:life_evaluation' AND c.iso_code_3 IN ('COG','COD') AND i.time_period IN ('2015','2024'))
ORDER BY 1, 2, 3;

-- Die 14 neuen known_issues
SELECT k.id, k.scope, s.short_code, k.table_name, k.decision, k.title
FROM known_issues k LEFT JOIN sources s ON s.id = k.source_id
WHERE k.title LIKE 'CI-172%' ORDER BY k.id;
