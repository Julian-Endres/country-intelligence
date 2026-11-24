-- Entwurf 15.11.2026 (Claude), ausgeführt 24.11.2026 (Julian, Log logs/migrations/2026-11-24_ci79_coverage.txt) – Backlog #79
-- indicator_coverage: numerische Jahres-Spalten first_year / last_year ergänzen.
-- Grund: first_period/last_period sind MIN/MAX auf Text. Beispiel MADDISON:gdppc zeigt last_period '730' statt 2022,
-- reine 'static'-Codes zeigen 'static'. Prüfung am Dump vom 14.11. 18:05 (lokal ausgewertet):
-- 729 Code/Quelle-Paare, 1 mit falschem last_period (MADDISON:gdppc), 0 mit falschem first_period.
-- first_period/last_period bleiben unverändert (Audit-Abfragen vom 10.11. lesen last_period).
-- Neu erstellen ist nötig, weil eine Materialized View keine Spalten per ALTER bekommt.
-- Abhängigkeiten laut Dump: keine View liest indicator_coverage; Index idx_indicator_coverage,
-- Kommentar und GRANT an ci_agent_readonly werden unten neu gesetzt.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-24_ci79_indicator_coverage_jahre.sql

\set ON_ERROR_STOP on

\echo '== vorher'
SELECT COUNT(*) AS paare, SUM(n_values) AS werte FROM indicator_coverage;
SELECT indicator_code, first_period, last_period FROM indicator_coverage WHERE indicator_code = 'MADDISON:gdppc';

BEGIN;

DROP MATERIALIZED VIEW indicator_coverage;

CREATE MATERIALIZED VIEW indicator_coverage AS
SELECT indicator_code,
       source_id,
       count(*)                     AS n_values,
       count(DISTINCT iso_numeric)  AS n_countries,
       count(DISTINCT time_period)  AS n_periods,
       min(time_period::text)       AS first_period,
       max(time_period::text)       AS last_period,
       min(CASE WHEN time_period ~ '^-?\d+$' THEN time_period::int END) AS first_year,
       max(CASE WHEN time_period ~ '^-?\d+$' THEN time_period::int END) AS last_year,
       min(value)                   AS min_value,
       max(value)                   AS max_value,
       now()                        AS refreshed_at
FROM indicators
GROUP BY indicator_code, source_id;

CREATE UNIQUE INDEX idx_indicator_coverage ON indicator_coverage (indicator_code, source_id);
COMMENT ON MATERIALIZED VIEW indicator_coverage IS
    'Abdeckung pro Indikator. Nach jedem Laden auffrischen: REFRESH MATERIALIZED VIEW indicator_coverage; '
    'Für Jahre first_year/last_year nehmen (numerisch); first_period/last_period sind Textvergleiche.';
GRANT SELECT ON indicator_coverage TO ci_agent_readonly;

COMMIT;

\echo '== nachher (Paare und Werte müssen gleich sein wie vorher)'
SELECT COUNT(*) AS paare, SUM(n_values) AS werte FROM indicator_coverage;
SELECT indicator_code, first_period, last_period, first_year, last_year FROM indicator_coverage WHERE indicator_code = 'MADDISON:gdppc';
SELECT COUNT(*) AS last_period_weicht_ab FROM indicator_coverage WHERE last_period <> last_year::text;
