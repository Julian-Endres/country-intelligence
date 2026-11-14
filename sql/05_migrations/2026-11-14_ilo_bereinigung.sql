-- Schritt 3 ILO-Bereinigung (#1): NULL-Dubletten und von der ILO zurückgezogene Werte löschen.
-- Voraussetzung: Schritt 1 (Backup) und Schritt 2 (load_ilostat.py --rohdaten 2026-11-14) gelaufen.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 -f sql/05_migrations/2026-11-14_ilo_bereinigung.sql 2>&1
-- Erwartet vorher: 59 = 22539 (22280 + 259 neu), NULL = 56398.
-- Erwartet nachher: 59 = 22248, NULL = 0. Weicht etwas ab, bricht die Transaktion ab und nichts ist geändert.
-- Liste der zurückgezogenen Werte: scripts/agent/output/2026-11-14_ilo/nur_in_db.csv (291 Zeilen,
-- erzeugt aus dem Abgleich DB gegen data/raw/ilo/2026-11-14).

BEGIN;

\echo '== Vorher'
SELECT source_id, COUNT(*) FROM indicators WHERE indicator_code LIKE 'ILO:%' GROUP BY 1 ORDER BY 1 NULLS LAST;

CREATE TEMP TABLE ilo_zurueckgezogen (
    indicator_code text, iso_code_3 text, time_period text, value_db float, obs_status_db text
) ON COMMIT DROP;
\copy ilo_zurueckgezogen FROM 'scripts/agent/output/2026-11-14_ilo/nur_in_db.csv' WITH CSV HEADER

DO $$
DECLARE n59 int; nnull int; nliste int; ntreffer int;
BEGIN
    SELECT COUNT(*) FILTER (WHERE source_id = 59), COUNT(*) FILTER (WHERE source_id IS NULL)
      INTO n59, nnull FROM indicators WHERE indicator_code LIKE 'ILO:%';
    SELECT COUNT(*) INTO nliste FROM ilo_zurueckgezogen;
    SELECT COUNT(*) INTO ntreffer
      FROM indicators i JOIN countries c USING (iso_numeric)
      JOIN ilo_zurueckgezogen z ON z.indicator_code = i.indicator_code
       AND z.iso_code_3 = c.iso_code_3 AND z.time_period = i.time_period
     WHERE i.source_id = 59 AND i.value = z.value_db;
    IF n59 <> 22539 OR nnull <> 56398 OR nliste <> 291 OR ntreffer <> 291 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: 59=% (erw. 22539), NULL=% (erw. 56398), Liste=% (erw. 291), Treffer=% (erw. 291)',
            n59, nnull, nliste, ntreffer;
    END IF;
END $$;

\echo '== Lösche NULL-Dubletten'
DELETE FROM indicators WHERE indicator_code LIKE 'ILO:%' AND source_id IS NULL;

\echo '== Lösche zurückgezogene Werte (nur bei unverändertem Wert)'
DELETE FROM indicators i
 USING countries c, ilo_zurueckgezogen z
 WHERE c.iso_numeric = i.iso_numeric
   AND z.indicator_code = i.indicator_code AND z.iso_code_3 = c.iso_code_3
   AND z.time_period = i.time_period AND i.source_id = 59 AND i.value = z.value_db;

DO $$
DECLARE n59 int; nnull int;
BEGIN
    SELECT COUNT(*) FILTER (WHERE source_id = 59), COUNT(*) FILTER (WHERE source_id IS NULL)
      INTO n59, nnull FROM indicators WHERE indicator_code LIKE 'ILO:%';
    IF n59 <> 22248 OR nnull <> 0 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: 59=% (erw. 22248), NULL=% (erw. 0)', n59, nnull;
    END IF;
END $$;

\echo '== Nachher'
SELECT indicator_code, source_id, COUNT(*) FROM indicators WHERE indicator_code LIKE 'ILO:%' GROUP BY 1, 2 ORDER BY 1, 2;

COMMIT;

REFRESH MATERIALIZED VIEW indicator_coverage;
\echo '== Fertig. indicator_coverage aufgefrischt.'
