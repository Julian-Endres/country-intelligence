-- =====================================================================
-- ENTWURF (Claude, 25.11.2026) – CI-177 / #140 / #151 / CI-179: Nacharbeit nach load_gitoc.py, load_fsi.py, load_kof.py
-- Aufruf (Shell, Repo-Wurzel), NACH den drei Loadern mit --schreiben:
--   psql -U postgres -d country_intelligence -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/ENTWURF_2026-11-25_ci177_gitoc_fsi_kof.sql > logs/migrations/2026-11-25_ci177_gitoc_fsi_kof.txt 2>&1
-- Setzt die drei CI-172-known_issues auf fixed. Kontrollzahlen = Stand nach den Loadern (Wegwerf-DB 25.11.).
-- =====================================================================
BEGIN;
DO $$
DECLARE
    soll jsonb := jsonb_build_object('gitoc', 9650, 'fsi', 2327, 'kof', 88164,
        'kof_neu5', 1874, 'ki_gitoc', 1, 'ki_fsi', 1, 'ki_kof', 1);
    ist jsonb; key text;
BEGIN
    SELECT jsonb_build_object(
        'gitoc', (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'GITOC:%'),
        'fsi',   (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'FSI:%'),
        'kof',   (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'KOF:%'),
        'kof_neu5', (SELECT count(*) FROM indicators i JOIN countries c USING (iso_numeric)
                     WHERE i.indicator_code LIKE 'KOF:%' AND c.iso_code_3 IN ('COD','ROU','TLS','AND','PSE')),
        'ki_gitoc', (SELECT count(*) FROM known_issues WHERE title = 'CI-172 GITOC: Länder nicht zugeordnet (Backlog #140)' AND decision <> 'fixed'),
        'ki_fsi',   (SELECT count(*) FROM known_issues WHERE title = 'CI-172 FSI: 6 Länder nicht zugeordnet (Backlog #140)' AND decision <> 'fixed'),
        'ki_kof',   (SELECT count(*) FROM known_issues WHERE title = 'CI-172 KOF: DR Kongo, Rumänien, Timor-Leste, Andorra, Palästina ohne Werte' AND decision <> 'fixed')
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint IS DISTINCT FROM (soll ->> key)::bigint THEN
            RAISE EXCEPTION 'Kontrolle vorher: % ist %, soll %', key, ist ->> key, soll ->> key;
        END IF;
    END LOOP;
    RAISE NOTICE 'Kontrolle vorher ok: %', ist;
END $$;

UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026: load_gitoc.py mit Liste GITOC.csv (Komma-Schreibweisen 2023) und Spalten je Ausgabe (#151); 1.540 Werte nachgeladen.'
WHERE title = 'CI-172 GITOC: Länder nicht zugeordnet (Backlog #140)';
UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026: load_fsi.py mit Liste FSI.csv; 6 Länder × 13 Codes nachgeladen. Die Datei enthält weiterhin nur 2022.'
WHERE title = 'CI-172 FSI: 6 Länder nicht zugeordnet (Backlog #140)';
UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026: load_kof.py über ISO3 mit Liste KOF.csv (alte Codes zar, rom, tmp, ado, wbg); 1.874 Werte nachgeladen.'
WHERE title = 'CI-172 KOF: DR Kongo, Rumänien, Timor-Leste, Andorra, Palästina ohne Werte';

DO $$
BEGIN
    IF (SELECT count(*) FROM known_issues WHERE decision = 'fixed' AND title IN (
        'CI-172 GITOC: Länder nicht zugeordnet (Backlog #140)',
        'CI-172 FSI: 6 Länder nicht zugeordnet (Backlog #140)',
        'CI-172 KOF: DR Kongo, Rumänien, Timor-Leste, Andorra, Palästina ohne Werte')) <> 3 THEN
        RAISE EXCEPTION 'Kontrolle nachher fehlgeschlagen';
    END IF;
    RAISE NOTICE 'Kontrolle nachher ok';
END $$;
COMMIT;
