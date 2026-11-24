-- =====================================================================
-- CI-172 Quarantäne, Schritt 1: Kandidatenlisten und Kontrollzahlen (NUR LESEND)
-- Entscheidung Julian 24.11. (2B, 3B, 4A): falsche Werte umhängen oder löschen, bevor v1.0 steht.
-- Diese Datei ändert nichts. Sie schreibt die Kandidaten als CSV nach logs/migrations/ci172/.
-- Claude gleicht jede Zeile danach mit der Rohdatei ab (umhängen / löschen / behalten).
-- Erst daraus entsteht die Migration (Schritt 2), mit Backup und Kontrollzahlen.
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -U postgres -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/03_queries/ci172_quarantaene_liste.sql > logs/migrations/ci172_liste.txt 2>&1
-- =====================================================================

\! mkdir -p logs/migrations/ci172

-- ---------------------------------------------------------------------
-- 0. Kontrollzahlen gesamt (für die Migration als „vorher“)
-- ---------------------------------------------------------------------
\echo '== 0. Gesamtzahlen'
SELECT (SELECT count(*) FROM indicators)                       AS indicators_gesamt,
       (SELECT count(*) FROM history.ethnic_groups)            AS ethnic_groups_gesamt,
       (SELECT count(*) FROM culture.country_facts)            AS country_facts_gesamt,
       (SELECT count(*) FROM culture.national_dishes)          AS national_dishes_gesamt,
       (SELECT count(*) FROM known_issues)                     AS known_issues_gesamt;

-- ---------------------------------------------------------------------
-- 1. indicators: Kandidaten je Quelle und Land
-- ---------------------------------------------------------------------
CREATE TEMP TABLE k_ind AS
SELECT i.id, s.short_code, c.iso_code_3 AS iso3, i.iso_numeric, i.indicator_code,
       i.time_period, i.value, i.obs_status
FROM indicators i
JOIN sources s   ON s.id = i.source_id
JOIN countries c ON c.iso_numeric = i.iso_numeric
WHERE (s.short_code = 'TI'     AND i.indicator_code = 'TI:CPI' AND c.iso_code_3 IN ('NGA','NER'))
   OR (s.short_code = 'FH'     AND c.iso_code_3 IN ('NGA','NER','SRB'))
   OR (s.short_code = 'HENLEY' AND c.iso_code_3 IN ('SRB'))
   OR (s.short_code = 'EPR'    AND c.iso_code_3 IN ('NGA','NER','SRB'))
   OR (s.short_code = 'WHR'    AND c.iso_code_3 IN ('COD','COG','CYP'))
   OR (s.short_code = 'SAMAYO' AND c.iso_code_3 IN ('GBR'));

\echo '== 1. indicators-Kandidaten je Quelle, Land, Code'
SELECT short_code, iso3, indicator_code, count(*) AS n,
       min(time_period) AS von, max(time_period) AS bis
FROM k_ind GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

\copy (SELECT * FROM k_ind ORDER BY short_code, iso3, indicator_code, time_period) TO 'logs/migrations/ci172/kandidaten_indicators.csv' CSV HEADER

-- ---------------------------------------------------------------------
-- 2. EPR-Gruppen: Niger und Kosovo (falsch zugeordnet) sowie die eigenen Gruppen von NGA, NER, SRB
-- ---------------------------------------------------------------------
CREATE TEMP TABLE k_epr AS
SELECT g.*, c.iso_code_3 AS iso3
FROM history.ethnic_groups g
LEFT JOIN countries c ON c.iso_numeric = g.iso_numeric
WHERE g.country_name IN ('Niger', 'Kosovo')
   OR c.iso_code_3 IN ('NGA', 'NER', 'SRB');

\echo '== 2. EPR-Gruppen je Name, Land, Nachfolger-Kennzeichen'
SELECT country_name, iso3, is_successor, count(*) AS n, min(year_from) AS von, max(year_to) AS bis
FROM k_epr GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

\copy (SELECT * FROM k_epr ORDER BY country_name, group_id, year_from) TO 'logs/migrations/ci172/kandidaten_epr_gruppen.csv' CSV HEADER

-- ---------------------------------------------------------------------
-- 3. SAMAYO: Großbritannien in den beiden Fakten-Tabellen
-- ---------------------------------------------------------------------
\echo '== 3. SAMAYO GBR'
SELECT 'country_facts' AS tab, f.* FROM culture.country_facts f
WHERE f.iso_numeric = (SELECT iso_numeric FROM countries WHERE iso_code_3 = 'GBR');
SELECT 'national_dishes' AS tab, d.* FROM culture.national_dishes d
WHERE d.iso_numeric = (SELECT iso_numeric FROM countries WHERE iso_code_3 = 'GBR');

\copy (SELECT f.* FROM culture.country_facts f JOIN countries c USING (iso_numeric) WHERE c.iso_code_3 = 'GBR') TO 'logs/migrations/ci172/kandidaten_country_facts.csv' CSV HEADER
\copy (SELECT d.* FROM culture.national_dishes d JOIN countries c USING (iso_numeric) WHERE c.iso_code_3 = 'GBR') TO 'logs/migrations/ci172/kandidaten_national_dishes.csv' CSV HEADER

-- ---------------------------------------------------------------------
-- 4. Vorhandene known_issues der betroffenen Quellen (SELECT vor INSERT, keine Dubletten)
-- ---------------------------------------------------------------------
\echo '== 4. vorhandene known_issues'
SELECT k.id, k.scope, s.short_code, k.indicator_code, k.table_name, k.decision, k.title
FROM known_issues k
LEFT JOIN sources s ON s.id = k.source_id
WHERE s.short_code IN ('TI','FH','HENLEY','EPR','WHR','SAMAYO','KOF','CAF_WGI','FSI','GITOC','NOBEL')
   OR k.indicator_code ~ '^(TI|FH|HENLEY|EPR|WHR|SAMAYO|KOF|CAF_WGI|FSI|GITOC|NOBEL):'
   OR k.table_name ILIKE ANY (ARRAY['%ethnic_groups%','%country_facts%','%national_dishes%','%diplomatic%'])
   OR k.title ILIKE '%kosovo%' OR k.description ILIKE '%kosovo%'
ORDER BY 3, 1;

\echo '== fertig: CSV-Dateien in logs/migrations/ci172/'
