-- =============================================================================
-- CI-171 Nachtrag Block 3 (24.11.2026, Claude, Entscheidungen Julian 24.11.)
--   a  #128 known_issue: Lebenserwartung mit Krisenjahr-Einbrüchen (UNDP:le, WB:SP.DYN.LE00.IN)
--   b  #128 known_issue: Bolivien-MPI = Erhebung 2023 (Online-Export), nicht 2016 (HDR-2025-Bericht)
--   c  #86  known_issue: ILO-Flags (B, U, mehrdeutiges A) und Modellschätzungen
--   d  #86  obs_status F für die Prognosewerte ILO:HOW_2TOT* 2026/2027 (Soll 366)
--   e  #86  known_issue: Werte für das laufende Jahr (angebrochen)
--   f  #2   Bezugsweg OWID für SIPRI:milex_gdp
-- Belege: logs/2026-11-24_ilo_obs_status.csv (ILO-Verzeichnis), Referenzdatei
--   data/raw/reference/undp_hdr25_composite_indices_time_series.csv, Chat 24.11.
--
-- Probelauf ist Standard (ROLLBACK). Ausführen mit -v ausfuehren=1.
--   Probelauf:  psql -d country_intelligence -X -f sql/05_migrations/2026-11-24_ci171_nachtrag_block3.sql > logs/migrations/2026-11-24_ci171_nachtrag_probelauf.txt 2>&1
--   Ausführen:  psql -d country_intelligence -X -v ausfuehren=1 -f sql/05_migrations/2026-11-24_ci171_nachtrag_block3.sql > logs/migrations/2026-11-24_ci171_nachtrag.txt 2>&1
-- Backup: backups/db_backup_20261124_vor_ci171.dump (heute 11:48) reicht – diese Datei ändert nur obs_status
--   von 366 Werten, Metadaten von 1 Code und legt known_issues an.
-- =============================================================================

\set ON_ERROR_STOP on
\if :{?ausfuehren}
\else
  \set ausfuehren 0
\endif

\echo '=================== VORHER ==================='
SELECT count(*) AS known_issues_gesamt FROM known_issues;
SELECT id, short_code FROM sources WHERE short_code IN ('UNDP','WB','SIPRI') OR id = 59 ORDER BY id;
SELECT indicator_code, count(*) AS werte, min(time_period), max(time_period)
FROM indicators WHERE indicator_code IN ('UNDP:le', 'WB:SP.DYN.LE00.IN', 'SIPRI:milex_gdp') GROUP BY 1 ORDER BY 1;
\echo '-- ILO HOW_2TOT ab 2026 nach obs_status (Soll: 366, alle A)'
SELECT indicator_code, time_period, obs_status, count(*) FROM indicators
WHERE indicator_code LIKE 'ILO:HOW_2TOT%' AND time_period >= '2026' GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

BEGIN;

-- Hilfsprüfung: ILO ist Quelle 59
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM sources WHERE id = 59 AND short_code ILIKE 'ILO%') THEN
    RAISE EXCEPTION 'Quelle 59 ist nicht ILO – Abbruch';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '== a  Lebenserwartung: Krisenjahre'
INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision, decided_by)
SELECT 'indicator', m.source_id, m.indicator_code,
       'Life expectancy: single crisis-year drops as published (UN WPP 2024)',
       'Values match the source. HDR25 time series (data/raw/reference/undp_hdr25_composite_indices_time_series.csv) '
       || 'has drops > 30 % against both neighbouring years in 6 cases: CAF 2009 (14.7), 2019 (31.5), 2022 (18.8); '
       || 'RWA 1994 (12.2); SOM 2011 (32.5); SSD 1998 (19.0). The same values appear in WB SP.DYN.LE00.IN (from UN WPP). '
       || 'CAF 2022 coincides with a nationwide survey reporting 5.6 % of the population died in 2022; CAF 2009 and 2019 '
       || 'not explained. Period life expectancy reacts to crisis mortality; use with care in trends and averages.',
       'accepted', 'Julian'
FROM indicator_metadata m
WHERE m.indicator_code IN ('UNDP:le', 'WB:SP.DYN.LE00.IN')
  AND NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.indicator_code = m.indicator_code
                  AND k.title LIKE 'Life expectancy: single crisis-year drops%');

-- -----------------------------------------------------------------------------
\echo '== b  Bolivien-MPI'
INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision, decided_by)
SELECT 'indicator', m.source_id, 'UNDP:mpi',
       'MPI Bolivia: survey 2023 (online export), not 2016 (HDR 2025 report)',
       'Import file data/raw/demographics/hdr-data_2.csv has Bolivia MPI 0.023 / headcount 5.8 / intensity 39.6 '
       || '(EDSA 2023). HDR 2025 Table 6 shows 0.038 / 9.1 / 41.7 (survey 2016). DB = import file; difference is the data '
       || 'vintage, not a loading error. Which MPI edition is loaded overall: backlog #152.',
       'accepted', 'Julian'
FROM indicator_metadata m
WHERE m.indicator_code = 'UNDP:mpi'
  AND NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.indicator_code = 'UNDP:mpi' AND k.title LIKE 'MPI Bolivia:%');

-- -----------------------------------------------------------------------------
\echo '== c  ILO-Flags'
INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision, decided_by)
SELECT 'source', 59, NULL,
       'ILO obs_status: B/U are ILO flags, A is ambiguous, some datasets are model estimates',
       'ILOSTAT dictionary (logs/2026-11-24_ilo_obs_status.csv): A = Adjusted, B = Break in series, M = Model-based '
       || 'extrapolation, U = Unreliable, R = Real value, I = Imputation. Loader writes flags as delivered, empty -> A. '
       || 'Therefore A on ILO values means either "adjusted" (ILO) or "no flag" (our default) – not distinguishable in the DB. '
       || 'Raw files 14.11.: EMP_2EMP 22,939 rows and HOW_2TOT 4,439 rows flagged A. EMP_2EMP and HOW_2TOT are entirely ILO '
       || 'modelled estimates (source XA:). Forecast years 2026/2027 of HOW_2TOT set to F (24.11.). Clean mapping after v1.0 (#32).',
       'accepted', 'Julian'
WHERE NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.source_id = 59 AND k.title LIKE 'ILO obs_status:%');

-- -----------------------------------------------------------------------------
\echo '== d  F für ILO-Prognosen 2026/2027'
UPDATE indicators SET obs_status = 'F', last_updated = CURRENT_TIMESTAMP
WHERE indicator_code LIKE 'ILO:HOW_2TOT%' AND time_period IN ('2026', '2027') AND obs_status = 'A';

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM indicators
   WHERE indicator_code LIKE 'ILO:HOW_2TOT%' AND time_period IN ('2026', '2027') AND obs_status = 'F';
  RAISE NOTICE 'd: Prognosewerte mit F: %', n;
  IF n <> 366 THEN RAISE EXCEPTION 'd: Soll 366 – Abbruch'; END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '== e  angebrochenes Jahr'
INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision, decided_by)
SELECT 'database', NULL, NULL,
       'Values for the current (incomplete) year and later',
       'Readiness R1.8 (24.11.2026 12:50): 1,207 values with a year after the previous year, e.g. ACLED 2026 (partial year) '
       || 'and ILO HOW_2TOT 2026/2027 (forecasts, obs_status F since 24.11.). Partial-year values are not comparable with full years; '
       || 'filter time_period <= last complete year for comparisons. Not changed in v1.0.',
       'accepted', 'Julian'
WHERE NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.scope = 'database' AND k.title LIKE 'Values for the current (incomplete) year%');

-- -----------------------------------------------------------------------------
\echo '== f  Bezugsweg SIPRI'
UPDATE indicator_metadata
SET loader_script = 'scripts/pipeline/governance/load_fsi_gitoc_owid.py',
    reference = 'Retrieved via Our World in Data (grapher CSV data/raw/governance/sipri_military_expenditure.csv); originator: SIPRI'
                || coalesce(' · ' || nullif(reference, ''), '')
WHERE indicator_code = 'SIPRI:milex_gdp'
  AND coalesce(reference, '') NOT LIKE 'Retrieved via Our World in Data%';

-- -----------------------------------------------------------------------------
\echo '=================== NACHHER (in der Transaktion) ==================='
SELECT count(*) AS known_issues_gesamt FROM known_issues;
\echo '-- Soll: vorher + 5 (a: 2, b: 1, c: 1, e: 1)'
SELECT id, scope, source_id, indicator_code, left(title, 70) AS titel, decision
FROM known_issues WHERE created_at >= now() - interval '1 minute' OR title LIKE ANY (ARRAY[
  'Life expectancy: single crisis-year drops%', 'MPI Bolivia:%', 'ILO obs_status:%', 'Values for the current (incomplete) year%'])
ORDER BY id;
SELECT indicator_code, left(reference, 90) AS reference, loader_script FROM indicator_metadata WHERE indicator_code = 'SIPRI:milex_gdp';

\if :ausfuehren
  COMMIT;
  \echo '>>> COMMIT ausgeführt. Danach Readiness-Check.'
\else
  ROLLBACK;
  \echo '>>> PROBELAUF: alles zurückgerollt, nichts geändert. Ausführen mit -v ausfuehren=1'
\endif
