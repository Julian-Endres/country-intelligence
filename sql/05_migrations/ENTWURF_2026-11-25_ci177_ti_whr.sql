-- =====================================================================
-- ENTWURF (Claude, Nacht 24./25.11.2026) – CI-177 Schritt 2: TI und WHR neu, Nacharbeit nach dem Laden
-- NICHT ausgeführt gegen die echte DB. Getestet an der Wegwerf-DB (Live-Stand 4.091.229 + Pilot FH/HENLEY).
--
-- Reihenfolge (Julian), NACH dem Pilot FH/HENLEY:
--   1. Trockenläufe (Shell, Repo-Wurzel, venv):
--        python scripts/pipeline/economy/load_cpi.py
--        python scripts/pipeline/culture/load_whr.py
--      Erwartung TI:  gleich 2.270, neu 194 (181 × 2025, 13 × Nigeria 2012–2024),
--                     wert_geaendert 13 (Serbien 2012–2024, waren KOSOVO-Werte – neuer Befund),
--                     nur_in_db 3 (Puerto Rico 2012–2014, echte TI-Werte aus älteren Ausgaben, bleiben)
--      Erwartung WHR: gleich 8.087, neu 46 (COD 38, COG 4, CYP 4),
--                     wert_geaendert 4 (Mali life_evaluation 2011/2012/2014/2015, waren SOMALILAND – neuer Befund),
--                     nur_in_db 0
--   2. Backup (Shell): pg_dump -Fc -U postgres country_intelligence > backups/db_backup_20261125_vor_ci177_ti_whr.dump
--   3. Beide Loader mit --schreiben. Erwartung: TI 194 neu / 13 geändert / 2.270 unverändert;
--      WHR 46 neu / 4 geändert / 8.087 unverändert.
--   4. Diese Datei (Shell, Repo-Wurzel):
--        psql -U postgres -d country_intelligence -v ON_ERROR_STOP=1 \
--             -f sql/05_migrations/ENTWURF_2026-11-25_ci177_ti_whr.sql > logs/migrations/2026-11-25_ci177_ti_whr.txt 2>&1
-- =====================================================================

BEGIN;

DO $$
DECLARE
    soll jsonb := jsonb_build_object(
        'ti',            2480,
        'ti_nga',        14,      -- 2012–2025
        'ti_srb_2024',   35,      -- Wert, nicht Anzahl (Kosovo hatte 44)
        'ti_2025',       181,
        'whr',           8137,
        'mli_2011_x1000', 3967,   -- Mali life_evaluation 2011 × 1000 (Somaliland hatte 4691)
        'ki_ti',         1,
        'ki_whr',        1,
        'ki_whr_health', 0
    );
    ist jsonb;
    key text;
BEGIN
    SELECT jsonb_build_object(
        'ti',          (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI'),
        'ti_nga',      (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '566'),
        'ti_srb_2024', (SELECT value::int FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '688' AND time_period = '2024'),
        'ti_2025',     (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND time_period = '2025'),
        'whr',         (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%'),
        'mli_2011_x1000', (SELECT round(value * 1000)::int FROM indicators WHERE indicator_code = 'WHR:life_evaluation' AND iso_numeric = '466' AND time_period = '2011'),
        'ki_ti',       (SELECT count(*) FROM known_issues WHERE title = 'CI-172 TI:CPI: Nigeria 2012–2024 ohne Werte (Werte waren Niger)' AND decision <> 'fixed'),
        'ki_whr',      (SELECT count(*) FROM known_issues WHERE title = 'CI-172 WHR: DR Kongo trug Werte der Republik Kongo, Zypern teils Nordzypern' AND decision <> 'fixed'),
        'ki_whr_health', (SELECT count(*) FROM known_issues WHERE title LIKE 'WHR:health%Null%')
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint IS DISTINCT FROM (soll ->> key)::bigint THEN
            RAISE EXCEPTION 'Kontrolle vorher: % ist %, soll %', key, ist ->> key, soll ->> key;
        END IF;
    END LOOP;
    RAISE NOTICE 'Kontrolle vorher ok: %', ist;
END $$;

UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026 (CI-177): load_cpi.py neu aus der TI-Datei CPI2025_Results.xlsx (ISO3-Spalte der Quelle, Liste TI.csv), Nigeria 2012–2025 geladen, 2025 ergänzt. Dabei gefunden und behoben: Serbien 2012–2024 trug die Werte des Kosovo (13 Werte, alter Fuzzy-Weg). Kosovo bleibt verworfen.'
WHERE title = 'CI-172 TI:CPI: Nigeria 2012–2024 ohne Werte (Werte waren Niger)';

UPDATE known_issues SET decision = 'fixed', resolved_at = now(),
       description = description || ' — BEHOBEN 25.11.2026 (CI-177): load_whr.py ohne Teilstring-Abgleich (Liste WHR.csv), DR Kongo, Republik Kongo und Zypern aus der Datei. Dabei gefunden und behoben: Mali 2011/2012/2014/2015 (life_evaluation) trug die Werte von „Somaliland Region“ („mali“ ⊂ „somaliland“). Nordzypern, Somaliland und Kosovo werden verworfen.'
WHERE title = 'CI-172 WHR: DR Kongo trug Werte der Republik Kongo, Zypern teils Nordzypern';

-- Nebenbefund 15.11. geklärt: WHR:health hat je Jahr genau einen Wert 0 – das ist Methode, kein Ladefehler.
INSERT INTO known_issues (scope, indicator_code, title, description, decision)
VALUES ('indicator', 'WHR:health',
        'WHR:health: je Jahr ein Wert 0 (Bezugsland der Zerlegung)',
        'Die „Explained by“-Komponenten des World Happiness Report messen den Beitrag eines Faktors gegenüber dem Land mit dem niedrigsten Wert (Dystopia-Bezug). Das Land mit dem niedrigsten Wert bekommt deshalb genau 0, z. B. Lesotho 2021 und 2023–2025, Mosambik 2022, Tschad 2020, Zentralafrikanische Republik 2019. Geprüft an WHR26_Data_Figure_2.1.xlsx (25.11.2026). Gilt sinngemäß für alle WHR-Komponenten.',
        'accepted');

DO $$
BEGIN
    IF (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172 TI:CPI%' AND decision = 'fixed') <> 1
    OR (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172 WHR:%' AND decision = 'fixed') <> 1
    OR (SELECT count(*) FROM known_issues WHERE indicator_code = 'WHR:health') <> 1 THEN
        RAISE EXCEPTION 'Kontrolle nachher fehlgeschlagen';
    END IF;
    RAISE NOTICE 'Kontrolle nachher ok';
END $$;

COMMIT;
