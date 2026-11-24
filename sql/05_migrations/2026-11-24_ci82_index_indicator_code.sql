-- Entwurf 15.11.2026 (Claude), ausgeführt 24.11.2026 (Julian, Log logs/migrations/2026-11-24_ci82_index.txt) – Backlog #82
-- Index für Abfragen nach indicator_code ohne Land (Dashboard, API, Audits).
-- Der UNIQUE-Index (iso_numeric, indicator_code, source_id, time_period) hilft nicht, weil iso_numeric vorne steht.
-- CONCURRENTLY: Tabelle bleibt währenddessen beschreibbar; darf NICHT in einer Transaktion laufen.
-- Größe: 4,2 Mio. Zeilen (Dump 14.11.), Dauer Schätzung: unter 1 Minute.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-24_ci82_index_indicator_code.sql

\set ON_ERROR_STOP on

\echo '== vorher: Plan einer typischen Abfrage'
EXPLAIN SELECT iso_numeric, value FROM indicators WHERE indicator_code = 'WB:SP.DYN.LE00.IN' AND time_period = '2022';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indicators_code_period ON indicators (indicator_code, time_period);

\echo '== nachher: Plan muss "Index Scan using idx_indicators_code_period" zeigen'
EXPLAIN SELECT iso_numeric, value FROM indicators WHERE indicator_code = 'WB:SP.DYN.LE00.IN' AND time_period = '2022';
SELECT pg_size_pretty(pg_relation_size('idx_indicators_code_period')) AS indexgroesse;
