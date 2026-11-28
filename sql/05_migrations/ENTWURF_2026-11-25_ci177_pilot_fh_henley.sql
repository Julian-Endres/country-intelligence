-- =====================================================================
-- ENTWURF (Claude, 24./25.11.2026) – CI-177 Pilot FH und HENLEY, Nacharbeit nach dem Laden – CI-177 Pilot FH und HENLEY, Nacharbeit nach dem Laden
-- NICHT ausgeführt gegen die echte DB. Getestet an der Wegwerf-DB (Dump vor_170 + Indikator-Teil CI-172,
-- 4.091.229 Werte = Live-Stand laut Kontrolle 24.11.).
--
-- Reihenfolge (Julian):
--   1. Neue Dateien aus "Claude outputs/ci177/" übernehmen (siehe README dort), Tests grün.
--   2. Trockenläufe (Shell, Repo-Wurzel, venv):
--        python scripts/pipeline/governance/load_freedom_house.py
--        python scripts/pipeline/international/load_henley.py
--      Erwartung FH:     ausgaben 52, gleich 15.898, neu_FH:PR 1.322, neu_FH:CL 1.322, neu_FH:STATUS 9.271, nur_in_db 0
--                        (PR/CL: Nigeria 1972–2024 und Serbien 2009–2024 = je 60, dazu die Ausgaben 1982–1989 = je 1.262)
--      Erwartung HENLEY: gleich 784, neu 8 (688 Serbien, 748 Eswatini), nur_in_db 0
--   3. Backup (Shell):  pg_dump -Fc -U postgres country_intelligence > backups/db_backup_20261125_vor_ci177.dump
--   4. Schreiben: beide Loader mit --schreiben
--      Erwartung: FH 11.915 neu / 0 geändert / 15.898 unverändert; HENLEY 8 neu / 0 / 784
--   5. Diese Datei (Shell, Repo-Wurzel):
--        psql -U postgres -d country_intelligence -v ON_ERROR_STOP=1 \
--             -f sql/05_migrations/ENTWURF_2026-11-25_ci177_pilot_fh_henley.sql \
--             > logs/migrations/2026-11-25_ci177_pilot.txt 2>&1
--
-- Inhalt: (A) Metadaten FH:STATUS (Kodierung laut Entscheidung 24.11., CI-63),
--         (B) known_issues „CI-172 FH: Nigeria …“ und „CI-172 HENLEY: Serbien …“ auf fixed.
-- Gilt für den Standardlauf MIT den Ausgaben 1982–1989 (Empfehlung Claude, Julian: „umsetzen“ 24.11. 23:03). Mit --ohne-1982-1989: je Code 8.009, fh_nga 132.
-- =====================================================================

BEGIN;

-- Kontrollzahlen vorher (= Stand nach Schritt 4)
DO $$
DECLARE
    soll jsonb := jsonb_build_object(
        'fh_pr',      9271,
        'fh_cl',      9271,
        'fh_status',  9271,
        'fh_nga',     156,     -- 52 Jahre × 3 Codes
        'fh_srb',     57,      -- 19 Jahre (2006–2024) × 3 Codes
        'henley',     792,
        'henley_srb_swz', 8,
        'ki_fh',      1,
        'ki_henley',  1
    );
    ist jsonb;
    key text;
BEGIN
    SELECT jsonb_build_object(
        'fh_pr',     (SELECT count(*) FROM indicators WHERE indicator_code = 'FH:PR'),
        'fh_cl',     (SELECT count(*) FROM indicators WHERE indicator_code = 'FH:CL'),
        'fh_status', (SELECT count(*) FROM indicators WHERE indicator_code = 'FH:STATUS'),
        'fh_nga',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric = '566'),
        'fh_srb',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric = '688'),
        'henley',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'HENLEY:%'),
        'henley_srb_swz', (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'HENLEY:%' AND iso_numeric IN ('688','748')),
        'ki_fh',     (SELECT count(*) FROM known_issues WHERE title = 'CI-172 FH: Nigeria ohne Werte, Serbien ab 2009 ohne Werte (waren Niger bzw. Kosovo)' AND decision <> 'fixed'),
        'ki_henley', (SELECT count(*) FROM known_issues WHERE title = 'CI-172 HENLEY: Serbien ohne Werte (waren Kosovo), Eswatini fehlt' AND decision <> 'fixed')
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint <> (soll ->> key)::bigint THEN
            RAISE EXCEPTION 'Kontrolle vorher: % ist %, soll %', key, ist ->> key, soll ->> key;
        END IF;
    END LOOP;
    RAISE NOTICE 'Kontrolle vorher ok: %', ist;
END $$;

-- (A) FH:STATUS-Metadaten. Kodierung F=1, PF=2, NF=3 (Entscheidung Julian 24.11., CI-63).
--     scale_type 'ordinal' statt 'categorical' (Empfehlung Claude, Julian: „umsetzen“ 24.11. 23:03): die drei Stufen sind
--     geordnet (frei < teilweise frei < nicht frei), Abstände nicht gleich – wie POLITY5:xconst.
UPDATE indicator_metadata SET
    scale_type   = 'ordinal',
    scale_min    = 1,
    scale_max    = 3,
    value_labels = '1 = Free; 2 = Partly Free; 3 = Not Free',
    direction    = 'higher_is_worse',
    unit         = NULL,
    description  = 'Freedom House status of a country: Free, Partly Free or Not Free, derived from the Political Rights and Civil Liberties ratings. Stored as 1 = Free, 2 = Partly Free, 3 = Not Free.',
    loader_script = 'scripts/pipeline/governance/load_freedom_house.py'
WHERE indicator_code = 'FH:STATUS';

-- (B) known_issues: Werte sind zurück
UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026 (CI-177): Loader auf scripts/pipeline/lib/laender.py umgestellt (Liste scripts/pipeline/lib/laender/FH.csv), Nigeria 1972–2024 und Serbien 2009–2024 neu geladen; Kosovo bleibt verworfen (siehe known_issue Kosovo).'
WHERE title = 'CI-172 FH: Nigeria ohne Werte, Serbien ab 2009 ohne Werte (waren Niger bzw. Kosovo)';

UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026 (CI-177): Loader auf scripts/pipeline/lib/laender.py umgestellt (Liste scripts/pipeline/lib/laender/HENLEY.csv), Serbien und Eswatini (Swaziland) geladen; Kosovo bleibt verworfen.'
WHERE title = 'CI-172 HENLEY: Serbien ohne Werte (waren Kosovo), Eswatini fehlt';

-- Kontrolle nachher
DO $$
BEGIN
    IF (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172 FH: Nigeria%' AND decision = 'fixed') <> 1
    OR (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172 HENLEY:%' AND decision = 'fixed') <> 1
    OR (SELECT scale_type FROM indicator_metadata WHERE indicator_code = 'FH:STATUS') IS DISTINCT FROM 'ordinal' THEN
        RAISE EXCEPTION 'Kontrolle nachher fehlgeschlagen';
    END IF;
    RAISE NOTICE 'Kontrolle nachher ok';
END $$;

COMMIT;
