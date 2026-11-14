-- ILO-Bestandsaufnahme (#1, #86, #64). Nur lesend.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -f sql/03_queries/2026-11-14_ilo_bestandsaufnahme.sql > scripts/agent/output/2026-11-14_ilo_bestand.txt 2>&1
BEGIN READ ONLY;

\echo '== Q1 Quelle(n) ILO in sources'
SELECT id, short_code, name, loaded_at, loaded_version
FROM sources WHERE short_code ILIKE '%ILO%' OR id = 59;

\echo '== Q2 Kontrollzahl: alle ILO-Werte je source_id (erwartet laut #1: NULL-Anteil 56.398)'
SELECT source_id, COUNT(*) AS werte, COUNT(DISTINCT indicator_code) AS codes
FROM indicators WHERE indicator_code LIKE 'ILO:%'
GROUP BY 1 ORDER BY 1 NULLS LAST;

\echo '== Q3 Je Code und source_id: Werte, Länder, Jahre, Flags'
SELECT indicator_code, source_id, COUNT(*) AS werte,
       COUNT(DISTINCT iso_numeric) AS laender,
       MIN(time_period) AS von, MAX(time_period) AS bis,
       string_agg(DISTINCT COALESCE(obs_status, '∅'), ',') AS flags
FROM indicators WHERE indicator_code LIKE 'ILO:%'
GROUP BY 1, 2 ORDER BY 1, 2 NULLS LAST;

\echo '== Q4 Mehrfachzeilen je Land/Code/Jahr (Unique-Regel greift bei NULL nicht)'
WITH g AS (
  SELECT indicator_code, source_id, iso_numeric, time_period, COUNT(*) AS n
  FROM indicators WHERE indicator_code LIKE 'ILO:%'
  GROUP BY 1, 2, 3, 4)
SELECT indicator_code, source_id, COUNT(*) FILTER (WHERE n > 1) AS gruppen_mehrfach,
       MAX(n) AS max_zeilen
FROM g GROUP BY 1, 2 HAVING MAX(n) > 1 ORDER BY 1, 2 NULLS LAST;

\echo '== Q5 Vergleich 59 gegen NULL je Code: gleich / abweichend / nur 59 / nur NULL (NULL-Seite auf 1 Zeile je Land-Jahr reduziert, wenn eindeutig)'
WITH a AS (SELECT indicator_code, iso_numeric, time_period, value
           FROM indicators WHERE indicator_code LIKE 'ILO:%' AND source_id = 59),
     b AS (SELECT indicator_code, iso_numeric, time_period,
                  MIN(value) AS vmin, MAX(value) AS vmax, COUNT(*) AS n
           FROM indicators WHERE indicator_code LIKE 'ILO:%' AND source_id IS NULL
           GROUP BY 1, 2, 3)
SELECT COALESCE(a.indicator_code, b.indicator_code) AS code,
       COUNT(*) FILTER (WHERE a.value IS NOT NULL AND b.n = 1 AND a.value = b.vmin) AS gleich,
       COUNT(*) FILTER (WHERE a.value IS NOT NULL AND b.n = 1 AND a.value <> b.vmin) AS abweichend,
       COUNT(*) FILTER (WHERE a.value IS NOT NULL AND b.n > 1) AS null_mehrfach,
       COUNT(*) FILTER (WHERE b.n IS NULL) AS nur_59,
       COUNT(*) FILTER (WHERE a.value IS NULL) AS nur_null
FROM a FULL JOIN b USING (indicator_code, iso_numeric, time_period)
GROUP BY 1 ORDER BY 1;

\echo '== Q6 Flags B/U/sonstige je Code und source_id (#86)'
SELECT indicator_code, source_id, obs_status, COUNT(*)
FROM indicators WHERE indicator_code LIKE 'ILO:%' AND COALESCE(obs_status, '') <> 'A'
GROUP BY 1, 2, 3 ORDER BY 1, 2 NULLS LAST, 3;

\echo '== Q7 Werte ab 2026 (Prognosen?, #86)'
SELECT indicator_code, source_id, time_period, COUNT(*)
FROM indicators WHERE indicator_code LIKE 'ILO:%' AND time_period >= '2026'
GROUP BY 1, 2, 3 ORDER BY 1, 2 NULLS LAST, 3;

\echo '== Q8 time_period nicht vierstellig'
SELECT indicator_code, time_period, COUNT(*)
FROM indicators WHERE indicator_code LIKE 'ILO:%' AND time_period !~ '^\d{4}$'
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '== Q9 Metadaten der ILO-Codes'
SELECT indicator_code, source_id, unit, metadata_reviewed_at::date AS geprueft, left(name, 70) AS name
FROM indicator_metadata WHERE indicator_code LIKE 'ILO:%' ORDER BY 1;

\echo '== Q10 Codes mit Werten, aber ohne Metadaten (und umgekehrt)'
SELECT 'ohne Metadaten' AS fall, i.indicator_code FROM (SELECT DISTINCT indicator_code FROM indicators WHERE indicator_code LIKE 'ILO:%') i
LEFT JOIN indicator_metadata m USING (indicator_code) WHERE m.indicator_code IS NULL
UNION ALL
SELECT 'ohne Werte', m.indicator_code FROM indicator_metadata m
WHERE m.indicator_code LIKE 'ILO:%' AND NOT EXISTS (SELECT 1 FROM indicators i WHERE i.indicator_code = m.indicator_code);

\echo '== Q11 Bolivien Informalität (#64)'
SELECT source_id, time_period, value, obs_status
FROM indicators WHERE indicator_code = 'ILO:SDG_0831_SEX_ECO_RT' AND iso_numeric = (SELECT iso_numeric FROM countries WHERE iso_code_3 = 'BOL')
ORDER BY time_period, source_id NULLS LAST;

ROLLBACK;
