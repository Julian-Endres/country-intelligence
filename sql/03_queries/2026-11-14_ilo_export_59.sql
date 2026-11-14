-- ILO-Werte unter source_id 59 als CSV, für den Abgleich mit den Rohdaten 2026-11-14. Nur lesend.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -f sql/03_queries/2026-11-14_ilo_export_59.sql 2>&1
\copy (SELECT i.indicator_code, c.iso_code_3, i.time_period, i.value, i.obs_status FROM indicators i JOIN countries c USING (iso_numeric) WHERE i.indicator_code LIKE 'ILO:%' AND i.source_id = 59 ORDER BY 1,2,3) TO 'scripts/agent/output/2026-11-14_ilo/db_59.csv' WITH CSV HEADER
