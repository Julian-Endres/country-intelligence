-- =====================================================================
-- ENTWURF (Claude, Nacht 24./25.11.2026) – CI-163: Dubletten unter falschem Ländercode löschen
-- NICHT ausgeführt. LISTE VOR LÖSCHEN: Julian prüft die beiden CSV und bestätigt.
-- Getestet an einer Wegwerf-DB mit politics.coups / politics.constitutional_events aus dem Dump
-- db_backup_20261124_vor_170.dump (CI-172 hat diese Tabellen nicht verändert).
--
-- Listen (je Zeile: id, falscher Code, Name, Jahr, Ereignis, id und Code der korrekten Zwillingszeile):
--   logs/migrations/ci163/loeschen_constitutional_events.csv   211 Zeilen
--   logs/migrations/ci163/loeschen_coups.csv                    38 Zeilen
--
-- Ursache (Befund Claude 25.11.):
--   constitutional_events: load_ccp.py bildet COW-Codes mit dem Python-Paket countrycode ab. Für eine Reihe
--     afrikanischer und pazifischer Staaten ist die Zuordnung um einen Nachbarn verschoben (Tschad → Rep. Kongo,
--     Kongo → DR Kongo, DR Kongo → Uganda, Uganda → Kenia, Kenia → Tansania, Tansania → Somalia, Somalia →
--     Äthiopien, Tonga → Samoa, Nauru → Tonga, Fidschi ↔ Vanuatu, Tschechien ↔ Slowakei …). Ein späterer Lauf mit
--     richtiger Zuordnung fügte die Ereignisse ein zweites Mal ein (Schlüssel iso_numeric, year, evnt_id → kein
--     Konflikt). Abgleich mit der Rohdatei über evnt_id und countries.cow_code: 3.728 Zeilen richtig und einmalig,
--     211 Paare (je eine falsche, eine richtige), 185 Zeilen historischer Einheiten (siehe unten, NICHT gelöscht).
--   coups: Erster Ladelauf (id 1–838) legte Niger ↔ Nigeria vertauscht, Kongo-Brazzaville auf DR Kongo, Moldau auf
--     die Malediven. Ein zweiter Lauf (id > 1000) lud 19 Länder neu; die falschen Zeilen blieben stehen.
--     Abgleich mit der Rohdatei CSPCoupsAnnualv2021 (Land, Jahr, Typ): 840 + 38 richtig, 38 falsch, 37 historisch.
--
-- Nicht Teil dieser Migration (Entscheidung Julian, siehe Chat-Doku 25.11.):
--   (a) Historische Einheiten auf heutige Länder gelegt (P9-Verstoß): constitutional_events 185 Zeilen
--       (Bayern, Baden, Sachsen, BRD, DDR → DEU; Tschechoslowakei → CZE; Jugoslawien → SRB …),
--       coups 37 Zeilen (USSR → RUS, Yemen North/South → YEM, Vietnam South → VNM, Czechoslovakia → CZE …).
--       Liste: logs/migrations/ci163/historische_einheiten_constitutional_events.csv
--   (b) coups: Land-Jahr-Typ mit 2 oder mehr Ereignissen fehlen GANZ (53 Kombinationen, 116 Ereignisse;
--       alle mit Anzahl 1 sind da). Der Coups-Loader fehlt im Repo (#69, CI-180) → Neuaufbau.
--
-- Aufruf (Shell, Repo-Wurzel), NACH Bestätigung der Listen:
--   psql -U postgres -d country_intelligence -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/ENTWURF_2026-11-25_ci163_dubletten.sql > logs/migrations/2026-11-25_ci163.txt 2>&1
-- =====================================================================

\set backup_da `test -e backups/2026-11-25_ci163_vorher_constitutional_events.csv && echo 1 || echo 0`
SELECT :backup_da = 1 AS backup_schon_da \gset
\if :backup_schon_da
    \echo 'ABBRUCH: Backup existiert schon – die Migration lief vermutlich bereits.'
    \quit
\endif

-- 0. Backups (vor BEGIN, nur lesend)
\copy (SELECT * FROM politics.constitutional_events ORDER BY id) TO 'backups/2026-11-25_ci163_vorher_constitutional_events.csv' CSV HEADER
\copy (SELECT * FROM politics.coups ORDER BY id) TO 'backups/2026-11-25_ci163_vorher_coups.csv' CSV HEADER

BEGIN;

CREATE TEMP TABLE l_ce (id int, iso_numeric_db text, country_name text, year int, evnt_id int, cowcode int,
                        id_richtig int, iso_richtig text, grund text) ON COMMIT DROP;
\copy l_ce FROM 'logs/migrations/ci163/loeschen_constitutional_events.csv' CSV HEADER
CREATE TEMP TABLE l_co (id int, iso_numeric_db text, country_name text, year int, coup_type text,
                        id_richtig int, iso_richtig text, grund text) ON COMMIT DROP;
\copy l_co FROM 'logs/migrations/ci163/loeschen_coups.csv' CSV HEADER

-- Kontrolle vorher: Zeilenzahlen, Listen passen exakt, jede Zwillingszeile existiert unverändert
DO $$
DECLARE
    soll jsonb := jsonb_build_object(
        'ce_gesamt', 4335, 'co_gesamt', 957,
        'l_ce', 211, 'l_co', 38,
        'ce_treffer', 211, 'co_treffer', 38,
        'ce_zwilling', 211, 'co_zwilling', 38);
    ist jsonb; key text;
BEGIN
    SELECT jsonb_build_object(
        'ce_gesamt', (SELECT count(*) FROM politics.constitutional_events),
        'co_gesamt', (SELECT count(*) FROM politics.coups),
        'l_ce', (SELECT count(*) FROM l_ce),
        'l_co', (SELECT count(*) FROM l_co),
        'ce_treffer', (SELECT count(*) FROM l_ce l JOIN politics.constitutional_events e
                         ON e.id = l.id AND e.iso_numeric = lpad(l.iso_numeric_db, 3, '0')
                        AND e.evnt_id = l.evnt_id AND e.year = l.year),
        'co_treffer', (SELECT count(*) FROM l_co l JOIN politics.coups c
                         ON c.id = l.id AND c.iso_numeric = lpad(l.iso_numeric_db, 3, '0')
                        AND c.year = l.year AND c.coup_type = l.coup_type),
        'ce_zwilling', (SELECT count(*) FROM l_ce l JOIN politics.constitutional_events e
                         ON e.id = l.id_richtig AND e.iso_numeric = lpad(l.iso_richtig, 3, '0')
                        AND e.evnt_id = l.evnt_id),
        'co_zwilling', (SELECT count(*) FROM l_co l JOIN politics.coups c
                         ON c.id = l.id_richtig AND c.iso_numeric = lpad(l.iso_richtig, 3, '0')
                        AND c.year = l.year AND c.coup_type = l.coup_type)
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint IS DISTINCT FROM (soll ->> key)::bigint THEN
            RAISE EXCEPTION 'Kontrolle vorher: % ist %, soll %', key, ist ->> key, soll ->> key;
        END IF;
    END LOOP;
    RAISE NOTICE 'Kontrolle vorher ok: %', ist;
END $$;

DELETE FROM politics.constitutional_events e USING l_ce l
WHERE e.id = l.id AND e.iso_numeric = lpad(l.iso_numeric_db, 3, '0') AND e.evnt_id = l.evnt_id;

DELETE FROM politics.coups c USING l_co l
WHERE c.id = l.id AND c.iso_numeric = lpad(l.iso_numeric_db, 3, '0') AND c.coup_type = l.coup_type;

-- Kontrolle nachher: keine Dublette mehr (gleiches Ereignis unter zwei Codes)
DO $$
BEGIN
    IF (SELECT count(*) FROM politics.constitutional_events) <> 4124
    OR (SELECT count(*) FROM politics.coups) <> 919
    OR EXISTS (SELECT evnt_id FROM politics.constitutional_events GROUP BY evnt_id HAVING count(*) > 1)
    OR EXISTS (SELECT 1 FROM politics.coups GROUP BY country_name, year, coup_type HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'Kontrolle nachher fehlgeschlagen';
    END IF;
    RAISE NOTICE 'Kontrolle nachher ok: constitutional_events 4124, coups 919, keine Dubletten';
END $$;

COMMIT;
