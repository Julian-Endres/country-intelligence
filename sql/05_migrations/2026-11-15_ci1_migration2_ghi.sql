-- =============================================================================
-- CI-1 Migration 2 (15.11.2026): GHI-Altbestand ohne source_id entfernen, known_issue anlegen
--
-- Voraussetzung:
--   1. Backup gelaufen (backups/2026-11-15_ci1_null_vorher.csv enthält alle 6.535 GHI-Zeilen).
--   2. Neuer Loader hat geschrieben:  python scripts/pipeline/health/load_ghi.py --schreiben
--      → 493 Werte unter source_id GHI (Bericht 2025: 432 A, 61 E für "<5").
--
-- Was passiert:
--   a) DELETE der 6.535 GHI-Zeilen ohne source_id (Ladung 28.05., 5 Ausgaben gemischt, Dubletten).
--   b) known_issue für GHI:score (nur Bericht 2025, "<5" als 2.5 mit obs_status E).
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_ci1_migration2_ghi.sql > logs/migrations/2026-11-15_ci1_migration2_ghi.txt 2>&1
--
-- Erwartet vorher:  GHI ohne source_id 6.535; GHI mit Quelle 493 (A 432, E 61); NULL gesamt 108.178.
-- Erwartet nachher: GHI ohne source_id 0; GHI mit Quelle 493; NULL gesamt 101.643 (nur POLITY5).
-- Weicht etwas ab, bricht die Transaktion ab und nichts ist geändert.
-- =============================================================================

BEGIN;

DO $$
DECLARE n_null_ghi bigint; n_ghi bigint; n_a bigint; n_e bigint; n_null bigint; n_ki bigint; src int;
BEGIN
    SELECT id INTO src FROM sources WHERE short_code = 'GHI';
    SELECT count(*) INTO n_null_ghi FROM indicators WHERE indicator_code = 'GHI:score' AND source_id IS NULL;
    SELECT count(*), count(*) FILTER (WHERE obs_status = 'A'), count(*) FILTER (WHERE obs_status = 'E')
      INTO n_ghi, n_a, n_e FROM indicators WHERE indicator_code = 'GHI:score' AND source_id = src;
    SELECT count(*) INTO n_null FROM indicators WHERE source_id IS NULL;
    SELECT count(*) INTO n_ki FROM known_issues WHERE indicator_code = 'GHI:score';
    IF n_null_ghi <> 6535 OR n_ghi <> 493 OR n_a <> 432 OR n_e <> 61 OR n_null <> 108178 OR n_ki <> 0 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: GHI ohne Quelle=% (6535) GHI mit Quelle=% (493) A=% (432) E=% (61) NULL gesamt=% (108178) known_issues GHI=% (0)',
            n_null_ghi, n_ghi, n_a, n_e, n_null, n_ki;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK';
END $$;

\echo '== a) GHI-Zeilen ohne source_id löschen'
DO $$
DECLARE n bigint;
BEGIN
    DELETE FROM indicators WHERE indicator_code = 'GHI:score' AND source_id IS NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 6535 THEN RAISE EXCEPTION 'Gelöscht: % (erwartet 6535)', n; END IF;
    RAISE NOTICE 'Gelöscht: % Zeilen', n;
END $$;

\echo '== b) known_issue GHI:score'
INSERT INTO known_issues (scope, source_id, indicator_code, title, description, decision)
SELECT 'indicator', s.id, 'GHI:score',
       'GHI: nur Bericht 2025 geladen; "<5" als 2,5 (obs_status E)',
       'GHI-Werte sind laut Herausgeber nur innerhalb eines Berichts vergleichbar, jeder Bericht rechnet die '
       || 'Referenzjahre mit revidierten UN-Daten neu. Deshalb nur der Bericht 2025 mit den Jahren 2000, 2008, 2016, 2025 '
       || '(Entscheidung Julian 15.11.2026). Ältere Berichte liegen in data/raw/health, sind aber nicht geladen. '
       || 'Länder mit sehr niedrigem Hunger veröffentlicht der Bericht nur als "<5"; gespeichert als 2,5 (Mitte 0–5) '
       || 'mit obs_status E. Für Ranglisten nutzbar, für Durchschnitte und Veränderungen ausschließen oder markieren.',
       'accepted'
FROM sources s WHERE s.short_code = 'GHI';

DO $$
DECLARE n_null_ghi bigint; n_ghi bigint; n_null bigint; n_ki bigint;
BEGIN
    SELECT count(*) INTO n_null_ghi FROM indicators WHERE indicator_code = 'GHI:score' AND source_id IS NULL;
    SELECT count(*) INTO n_ghi FROM indicators WHERE indicator_code = 'GHI:score';
    SELECT count(*) INTO n_null FROM indicators WHERE source_id IS NULL;
    SELECT count(*) INTO n_ki FROM known_issues WHERE indicator_code = 'GHI:score' AND decision = 'accepted';
    IF n_null_ghi <> 0 OR n_ghi <> 493 OR n_null <> 101643 OR n_ki <> 1 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: GHI ohne Quelle=% (0) GHI gesamt=% (493) NULL gesamt=% (101643) known_issue=% (1)',
            n_null_ghi, n_ghi, n_null, n_ki;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: GHI 493 Werte, noch % ohne source_id (nur POLITY5)', n_null;
END $$;

\echo '== Nachher: GHI je Jahr und Status'
SELECT time_period, obs_status, count(*) FROM indicators WHERE indicator_code = 'GHI:score'
GROUP BY 1, 2 ORDER BY 1, 2;

COMMIT;

REFRESH MATERIALIZED VIEW indicator_coverage;
\echo '== Fertig. indicator_coverage aufgefrischt.'
