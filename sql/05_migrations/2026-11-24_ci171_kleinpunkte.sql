-- =============================================================================
-- CI-171 Gebündelte Migration "Kleinpunkte" (24.11.2026, Claude, Entscheidungen Julian 24.11.)
--
--   A  #2   9 Codes: Werte von Quelle 53 (OWID_SOCIAL) auf die Quelle der Metadaten (WHO 2, UNODC 58, WB 1)
--           + Bezugsweg OWID in loader_script/reference (Regel 24.11.: Präfix = Urheber, Bezugsweg Pflicht)
--   B  #8   WB:poverty_3_day deprecated (Doppelung zu WB:SI.POV.DDAY, 1.732/1.750 gleich)
--   C  #63  COW:intrastate_wars, COW:total_wars deprecated (nie geladen, #77)
--   D  #84  Ember -> EMBER (short_code); 32 Codes umbenennen: WEF: -> WEF_GGGI: (5),
--           FAO_FOOD: -> FAO_FOOD_GRP: (26, nur Quelle 50), CULTURE:has_national_dish -> SAMAYO:
--   E  #85  47 NaN-Werte in UNDP:mpi_* löschen (vorher als CSV gesichert)
--   F  #91  Name WB:SI.POV.DDAY auf 3,00 USD / 2021 PPP (SI.POV.GAPS ist schon richtig)
--   G  Bezugsweg OWID für TI, RSF, EI, EMBER, EIA, OWID_CO2 (loader_script + reference)
--   H  Quelle 53 bleibt stehen, Beschreibung: nur noch Bezugsweg
--
-- NICHT hier: #82 Index (CONCURRENTLY, eigene Datei), #79 indicator_coverage (eigene Datei),
--             FH:STATUS laden (Loader-Schritt), Loader-Anpassungen (Python, eigener Commit).
--
-- Vorab-Prüfung: logs/2026-11-24_ci171_vorab.txt, logs/2026-11-24_ci171_vorab_umbenennen.txt
--   Fremdschlüssel auf indicator_code: nur indicators, known_issues. Zielcodes existieren nicht.
--
-- PROBELAUF ist Standard: alles läuft in einer Transaktion und wird am Ende ZURÜCKGEROLLT.
-- Erst mit -v ausfuehren=1 wird COMMIT gemacht.
--
-- Aufruf (Shell, Repo-Wurzel):
--   Probelauf:  psql -d country_intelligence -X -f sql/05_migrations/2026-11-24_ci171_kleinpunkte.sql > logs/migrations/2026-11-24_ci171_probelauf.txt 2>&1
--   Backup:     pg_dump -Fc -d country_intelligence -f backups/db_backup_20261124_vor_ci171.dump
--   Ausführen:  psql -d country_intelligence -X -v ausfuehren=1 -f sql/05_migrations/2026-11-24_ci171_kleinpunkte.sql > logs/migrations/2026-11-24_ci171.txt 2>&1
--   Danach:     psql -d country_intelligence -X -c "REFRESH MATERIALIZED VIEW indicator_coverage;"
-- =============================================================================

\set ON_ERROR_STOP on
\if :{?ausfuehren}
\else
  \set ausfuehren 0
\endif

\echo '=================== VORHER ==================='
SELECT count(*) AS werte_gesamt FROM indicators;
SELECT count(*) AS codes_gesamt, count(*) FILTER (WHERE status = 'active') AS aktiv FROM indicator_metadata;
\echo '-- R2.2 Werte, deren Quelle nicht zur Metadaten-Quelle passt (soll vorher 26.152)'
SELECT count(*) AS r2_2 FROM indicators i JOIN indicator_metadata m USING (indicator_code)
WHERE i.source_id IS DISTINCT FROM m.source_id;
\echo '-- R3.4 Präfix passt nicht zum short_code (soll vorher 37)'
SELECT count(*) AS r3_4 FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
WHERE split_part(x.indicator_code, ':', 1) <> s.short_code;
\echo '-- NaN-Werte (soll vorher 47)'
SELECT count(*) AS nan FROM indicators WHERE value = 'NaN'::float;

-- NaN-Zeilen vor dem Löschen sichern (außerhalb der Transaktion, nur lesen)
\copy (SELECT * FROM indicators WHERE value = 'NaN'::float ORDER BY indicator_code, iso_numeric, time_period) TO 'logs/migrations/2026-11-24_ci171_undp_nan_geloescht.csv' WITH CSV HEADER

BEGIN;

-- -----------------------------------------------------------------------------
\echo '== A  #2: Werte von Quelle 53 auf die Quelle der Metadaten'
-- Erwartung: WHO 13.072, UNODC 10.806, WB 2.274 = 26.152
UPDATE indicators i
SET source_id = m.source_id
FROM indicator_metadata m
WHERE m.indicator_code = i.indicator_code
  AND i.source_id = 53
  AND m.source_id IN (1, 2, 58);

DO $$
DECLARE n_53 int; n_who int; n_unodc int; n_wb int;
BEGIN
  SELECT count(*) INTO n_53 FROM indicators WHERE source_id = 53;
  SELECT count(*) INTO n_who FROM indicators
   WHERE indicator_code IN ('WHO:alcohol_per_capita','WHO:binge_drinking','WHO:drug_deaths','WHO:tobacco_prevalence') AND source_id = 2;
  SELECT count(*) INTO n_unodc FROM indicators
   WHERE indicator_code IN ('UNODC:homicide_count','UNODC:homicide_rate','UNODC:prison_occupancy','UNODC:prison_rate') AND source_id = 58;
  SELECT count(*) INTO n_wb FROM indicators WHERE indicator_code = 'WB:poverty_3_day' AND source_id = 1;
  RAISE NOTICE 'A: Quelle 53 noch % Werte, WHO %, UNODC %, WB %', n_53, n_who, n_unodc, n_wb;
  IF n_53 <> 0 OR n_who <> 13072 OR n_unodc <> 10806 OR n_wb <> 2274 THEN
    RAISE EXCEPTION 'A: Kontrollzahlen stimmen nicht (Soll 0 / 13072 / 10806 / 2274) – Abbruch, nichts geändert';
  END IF;
END $$;

-- Bezugsweg für die 9 Codes (Dateien laut docs/RAW_INVENTUR_2026-11.md)
UPDATE indicator_metadata m
SET loader_script = 'scripts/pipeline/governance/load_fsi_gitoc_owid.py',
    reference = 'Retrieved via Our World in Data (grapher CSV ' || v.datei || '); originator: ' || v.urheber
                || coalesce(' · ' || nullif(m.reference, ''), '')
FROM (VALUES
  ('WHO:alcohol_per_capita',   'data/raw/health/owid_alcohol_consumption_per_capita.csv', 'WHO'),
  ('WHO:binge_drinking',       'data/raw/health/owid_alcohol_binge_drinking.csv',         'WHO'),
  ('WHO:tobacco_prevalence',   'data/raw/health/owid_tobacco_prevalence.csv',             'WHO'),
  ('WHO:drug_deaths',          'data/raw/health/owid_drug_deaths_who.csv',                'WHO'),
  ('UNODC:homicide_rate',      'data/raw/governance/owid_homicide_rate.csv',              'UNODC'),
  ('UNODC:homicide_count',     'data/raw/governance/owid_homicide_count.csv',             'UNODC'),
  ('UNODC:prison_rate',        'data/raw/governance/owid_prison_population_rate.csv',     'UNODC'),
  ('UNODC:prison_occupancy',   'data/raw/governance/owid_prison_occupancy_capacity.csv',  'UNODC'),
  ('WB:poverty_3_day',         'data/raw/economy/owid_poverty_headcount.csv',             'World Bank (PIP)')
) AS v(code, datei, urheber)
WHERE m.indicator_code = v.code;

-- -----------------------------------------------------------------------------
\echo '== B/C  #8, #63: deprecated mit Grund (Grund als known_issue, scope indicator)'
UPDATE indicator_metadata SET status = 'deprecated'
WHERE indicator_code IN ('WB:poverty_3_day', 'COW:intrastate_wars', 'COW:total_wars');

INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision, decided_by)
VALUES
 ('indicator', 1, 'WB:poverty_3_day',
  'Deprecated: duplicate of WB:SI.POV.DDAY',
  'Same series ($3.00/day, 2021 PPP), retrieved via OWID. Comparison 24.11.2026: 1,732 of 1,750 common country-years equal (< 0.05). '
  || 'Extra OWID years 1963–1999 come from our WB date range starting 2000 (#106). Values kept, code inactive.',
  'accepted', 'Julian'),
 ('indicator', 42, 'COW:intrastate_wars',
  'Deprecated: never loaded',
  'Metadata exists but no values (COW intrastate download blocked, backlog #77). Reload after v1.0, then set active again.',
  'accepted', 'Julian'),
 ('indicator', 42, 'COW:total_wars',
  'Deprecated: never loaded',
  'Metadata exists but no values (depends on COW intrastate data, backlog #77). Reload after v1.0, then set active again.',
  'accepted', 'Julian');

-- -----------------------------------------------------------------------------
\echo '== D  #84: Ember -> EMBER und 32 Codes umbenennen'
UPDATE sources SET short_code = 'EMBER' WHERE id = 91 AND short_code = 'Ember';

CREATE TEMP TABLE umbenennen ON COMMIT DROP AS
SELECT m.indicator_code AS alt,
       CASE WHEN m.indicator_code LIKE 'WEF:%'      THEN 'WEF_GGGI:'     || split_part(m.indicator_code, ':', 2)
            WHEN m.indicator_code LIKE 'FAO_FOOD:%' THEN 'FAO_FOOD_GRP:' || split_part(m.indicator_code, ':', 2)
            ELSE 'SAMAYO:has_national_dish' END AS neu
FROM indicator_metadata m
WHERE (m.indicator_code LIKE 'WEF:%' AND m.source_id = 130)
   OR (m.indicator_code LIKE 'FAO_FOOD:%' AND m.source_id = 50)
   OR (m.indicator_code = 'CULTURE:has_national_dish' AND m.source_id = 132);

DO $$
DECLARE n int; n_werte bigint;
BEGIN
  SELECT count(*) INTO n FROM umbenennen;
  SELECT count(*) INTO n_werte FROM indicators WHERE indicator_code IN (SELECT alt FROM umbenennen);
  RAISE NOTICE 'D: % Codes, % Werte zum Umbenennen', n, n_werte;
  IF n <> 32 OR n_werte <> 62713 THEN
    RAISE EXCEPTION 'D: Soll 32 Codes / 62.713 Werte – Abbruch';
  END IF;
END $$;

-- 1. neue Metadaten-Zeilen als Kopie (alle Spalten laut Vorab-Prüfung Teil 3)
INSERT INTO indicator_metadata (indicator_code, name, description, unit, source_id, category, domain, dimension,
       direction, scale_type, scale_min, scale_max, data_origin, temporal_type, is_lead_indicator, keywords,
       reference, loader_script, status, metadata_reviewed_at, added_at, key_info, producer_definition, value_labels)
SELECT u.neu, m.name, m.description, m.unit, m.source_id, m.category, m.domain, m.dimension,
       m.direction, m.scale_type, m.scale_min, m.scale_max, m.data_origin, m.temporal_type, m.is_lead_indicator, m.keywords,
       m.reference, m.loader_script, m.status, m.metadata_reviewed_at, m.added_at, m.key_info, m.producer_definition, m.value_labels
FROM indicator_metadata m JOIN umbenennen u ON u.alt = m.indicator_code;

-- 2. Werte und known_issues umhängen (known_issues laut Vorab-Prüfung 0, der Vollständigkeit halber)
UPDATE indicators i   SET indicator_code = u.neu FROM umbenennen u WHERE i.indicator_code = u.alt;
UPDATE known_issues k SET indicator_code = u.neu FROM umbenennen u WHERE k.indicator_code = u.alt;

-- 3. alte Metadaten-Zeilen löschen
DELETE FROM indicator_metadata WHERE indicator_code IN (SELECT alt FROM umbenennen);

DO $$
DECLARE n_alt int; n_neu int; n_werte bigint;
BEGIN
  SELECT count(*) INTO n_alt FROM indicator_metadata WHERE indicator_code IN (SELECT alt FROM umbenennen);
  SELECT count(*) INTO n_neu FROM indicator_metadata WHERE indicator_code IN (SELECT neu FROM umbenennen);
  SELECT count(*) INTO n_werte FROM indicators WHERE indicator_code IN (SELECT neu FROM umbenennen);
  RAISE NOTICE 'D nachher: alte Codes %, neue Codes %, Werte unter neuen Codes %', n_alt, n_neu, n_werte;
  IF n_alt <> 0 OR n_neu <> 32 OR n_werte <> 62713 THEN
    RAISE EXCEPTION 'D: Kontrollzahlen nach dem Umbenennen falsch – Abbruch';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '== E  #85: 47 NaN-Werte in UNDP:mpi_* löschen'
DELETE FROM indicators WHERE value = 'NaN'::float AND indicator_code LIKE 'UNDP:mpi%';

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM indicators WHERE value = 'NaN'::float;
  RAISE NOTICE 'E: NaN-Werte danach %', n;
  IF n <> 0 THEN RAISE EXCEPTION 'E: Es gibt noch NaN-Werte außerhalb UNDP:mpi_* – Abbruch'; END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '== F  #91: Name WB:SI.POV.DDAY'
UPDATE indicator_metadata
SET name = 'Poverty headcount ratio at $3.00 a day (2021 PPP) (% of population)'
WHERE indicator_code = 'WB:SI.POV.DDAY'
  AND name = 'Poverty headcount ratio at $2.15 a day (2017 PPP) (% of population)';

-- -----------------------------------------------------------------------------
\echo '== G  Bezugsweg OWID für TI, RSF, EI, EMBER, EIA, OWID_CO2'
UPDATE indicator_metadata m
SET loader_script = v.loader,
    reference = v.weg || coalesce(' · ' || nullif(m.reference, ''), '')
FROM (VALUES
  ('TI',       'scripts/pipeline/economy/load_cpi.py',
               'Retrieved via Our World in Data (owid.catalog, search "corruption"); originator: Transparency International'),
  ('RSF',      'scripts/pipeline/governance/load_rsf.py',
               'Retrieved via Our World in Data (grapher press-freedom-index-rsf.csv, file as of 2022); originator: RSF'),
  ('EI',       'scripts/pipeline/environment/load_owid_energy.py',
               'Retrieved via Our World in Data (owid-energy-data); originator: Energy Institute'),
  ('EMBER',    'scripts/pipeline/environment/load_owid_energy.py',
               'Retrieved via Our World in Data (owid-energy-data); originator: Ember'),
  ('EIA',      'scripts/pipeline/environment/load_owid_energy.py',
               'Retrieved via Our World in Data (owid-energy-data); originator: U.S. EIA'),
  ('OWID_CO2', 'scripts/pipeline/economy/load_owid_co2.py',
               'Retrieved via Our World in Data (owid-co2-data); originators per variable (GCP, PRIMAP, Maddison, …)')
) AS v(praefix, loader, weg)
WHERE split_part(m.indicator_code, ':', 1) = v.praefix
  AND coalesce(m.reference, '') NOT LIKE 'Retrieved via Our World in Data%';   -- nicht doppelt bei Wiederholung

-- -----------------------------------------------------------------------------
\echo '== H  Quelle 53 nur noch Bezugsweg'
UPDATE sources
SET description = 'Not used as a source since 24.11.2026 (rule: prefix = originator). OWID was the retrieval path for '
                  || '4 WHO, 4 UNODC codes and WB:poverty_3_day; see indicator_metadata.reference. Previous description: '
                  || coalesce(description, '–')
WHERE id = 53 AND coalesce(description, '') NOT LIKE 'Not used as a source since 24.11.2026%';

-- -----------------------------------------------------------------------------
\echo '=================== NACHHER (in der Transaktion) ==================='
SELECT count(*) AS werte_gesamt FROM indicators;
\echo '-- Werte gesamt: Soll = vorher − 47'
SELECT count(*) AS codes_gesamt, count(*) FILTER (WHERE status = 'active') AS aktiv FROM indicator_metadata;
\echo '-- Codes gesamt: Soll = vorher (32 neu, 32 weg); aktiv: Soll = vorher − 3'
SELECT count(*) AS r2_2 FROM indicators i JOIN indicator_metadata m USING (indicator_code)
WHERE i.source_id IS DISTINCT FROM m.source_id;
\echo '-- R2.2: Soll 0'
SELECT count(*) AS r3_4 FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
WHERE split_part(x.indicator_code, ':', 1) <> s.short_code;
\echo '-- R3.4: Soll 0'
SELECT split_part(indicator_code, ':', 1) AS praefix, count(*) AS codes,
       count(*) FILTER (WHERE reference LIKE 'Retrieved via Our World in Data%') AS mit_bezugsweg
FROM indicator_metadata
WHERE split_part(indicator_code, ':', 1) IN ('TI','RSF','EI','EMBER','EIA','OWID_CO2')
   OR indicator_code IN ('WHO:alcohol_per_capita','WHO:binge_drinking','WHO:drug_deaths','WHO:tobacco_prevalence',
                         'UNODC:homicide_count','UNODC:homicide_rate','UNODC:prison_occupancy','UNODC:prison_rate','WB:poverty_3_day')
GROUP BY 1 ORDER BY 1;
\echo '-- Bezugsweg: codes = mit_bezugsweg in jeder Zeile'

\if :ausfuehren
  COMMIT;
  \echo '>>> COMMIT ausgeführt. Jetzt: REFRESH MATERIALIZED VIEW indicator_coverage; dann Readiness-Check.'
\else
  ROLLBACK;
  \echo '>>> PROBELAUF: alles zurückgerollt, nichts geändert. Ausführen mit -v ausfuehren=1'
\endif
