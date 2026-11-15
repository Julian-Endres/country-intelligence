-- CI-1 Schritt 1: Backup aller Werte ohne source_id (15.11.2026). Liest nur, ändert nichts.
-- Sichert alle 627.967 NULL-Zeilen (auch GHI und POLITY5, die erst später bereinigt werden).
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -v ON_ERROR_STOP=1 -f sql/03_queries/2026-11-15_ci1_backup.sql
--   wc -l backups/2026-11-15_ci1_null_vorher.csv     # erwartet: 627968 (mit Kopfzeile)

SET default_transaction_read_only = on;

\copy (SELECT i.id, i.iso_numeric, i.indicator_code, i.source_id, i.value, i.time_period, i.obs_status, i.last_updated, x.source_id AS meta_source_id FROM indicators i JOIN indicator_metadata x USING (indicator_code) WHERE i.source_id IS NULL ORDER BY i.id) TO 'backups/2026-11-15_ci1_null_vorher.csv' WITH CSV HEADER

\echo 'Backup geschrieben: backups/2026-11-15_ci1_null_vorher.csv'
