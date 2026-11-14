-- Schritt 1 ILO-Bereinigung: Backup aller ILO-Zeilen (source_id 59 und NULL) als CSV. Nur lesend.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 -f sql/03_queries/2026-11-14_ilo_backup.sql 2>&1
-- Erwartet: 59 = 22280, NULL = 56398, Datei mit 78678 Datenzeilen.
\echo '== Kontrollzahlen vor dem Backup'
SELECT source_id, COUNT(*) FROM indicators WHERE indicator_code LIKE 'ILO:%' GROUP BY 1 ORDER BY 1 NULLS LAST;
\copy (SELECT * FROM indicators WHERE indicator_code LIKE 'ILO:%' ORDER BY id) TO 'backups/2026-11-14_ilo_indicators_vorher.csv' WITH CSV HEADER
\echo '== Backup geschrieben: backups/2026-11-14_ilo_indicators_vorher.csv'
