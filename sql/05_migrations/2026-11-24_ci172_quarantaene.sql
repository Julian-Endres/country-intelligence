-- =============================================================================
-- CI-172 Quarantäne (24.11.2026): Werte aus unscharfer Länderzuordnung umhängen oder löschen
-- Entscheidungen Julian 24.11.2026: 2B (Quarantäne vor v1.0), 3B (EPR jetzt Quarantäne, Neuaufbau
-- nach v1.0), 4A (Kosovo verworfen bis Weg A). Block E (alle drei EPR-Codes) NUR mit Zustimmung Julian.
--
-- Voraussetzung:
--   1. Die 17 Loader mit Fuzzy, Paket oder Teilstring sind gesperrt (Zeile „CI-172: Loader gesperrt“).
--      Sonst füllt ein neuer Lauf die frei gewordenen Plätze sofort wieder falsch (DO NOTHING).
--   2. Entscheidungslisten (Claude, jede Zeile gegen die Rohdatei geprüft, 0 unklar):
--        logs/migrations/ci172/entscheidung_indicators.csv   503 Zeilen: 153 umhaengen, 280 loeschen, 70 behalten
--        logs/migrations/ci172/entscheidung_epr_gruppen.csv  214 Zeilen:  60 umhaengen,   6 loeschen, 148 behalten
--
-- Was passiert (eine Transaktion; weicht eine Kontrollzahl ab, ist nichts geändert):
--   0. Backups nach backups/ (vor BEGIN, nur lesend)
--   A. indicators umhängen, Wert gehört nachweislich einem anderen Land der Quelle (153):
--        TI:CPI NGA→NER 13 · FH NGA→NER 88 · WHR COD→COG 52
--   B. indicators löschen, Wert einer Einheit ohne Land oder Mischung (280):
--        FH SRB 32 (Kosovo 2009–2024) · HENLEY SRB 4 (Kosovo) · WHR CYP 4 (Nordzypern)
--        EPR NGA 192 + SRB 48 (Gruppen von Niger bzw. Kosovo mitgezählt)
--   C. history.ethnic_groups: Niger-Gruppen NGA→NER 60, Kosovo-Gruppen löschen 6
--   D. SAMAYO: GBR-Zeile in culture.country_facts und culture.national_dishes löschen (England/Wales)
--   E. EPR: alle übrigen Werte von EPR:n_groups, EPR:discriminated_share, EPR:excluded_share löschen
--      (Definition laut EPR-Codebuch 2021 falsch) – NUR MIT ZUSTIMMUNG, sonst Block E entfernen
--   F. 14 known_issues, Titel beginnen mit „CI-172“
--   G. indicator_coverage auffrischen
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -U postgres -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-24_ci172_quarantaene.sql > logs/migrations/2026-11-24_ci172_quarantaene.txt 2>&1
--
-- Unabhängige Kontrolle danach (psql), erwartet: NER 13 | NER 88 | SRB 6 | COG 52 | COD 4 | CYP 52 | EPR 0 | KI 14
--   SELECT 'TI NER', count(*) FROM indicators WHERE indicator_code='TI:CPI' AND iso_numeric='562'
--   UNION ALL SELECT 'FH NER', count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric='562'
--   UNION ALL SELECT 'FH SRB', count(*) FROM indicators WHERE indicator_code LIKE 'FH:%' AND iso_numeric='688'
--   UNION ALL SELECT 'WHR COG', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric='178'
--   UNION ALL SELECT 'WHR COD', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric='180'
--   UNION ALL SELECT 'WHR CYP', count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric='196'
--   UNION ALL SELECT 'EPR', count(*) FROM indicators WHERE indicator_code LIKE 'EPR:%'
--   UNION ALL SELECT 'KI', count(*) FROM known_issues WHERE title LIKE 'CI-172%';
-- =============================================================================

\set backup_da `test -e backups/2026-11-24_ci172_vorher_indicators.csv && echo 1 || echo 0`
\if :backup_da
    \echo 'ABBRUCH: backups/2026-11-24_ci172_vorher_indicators.csv existiert schon. Die Migration lief vermutlich schon;'
    \echo 'ein zweiter Lauf würde das Original-Backup überschreiben. Nichts geändert.'
    \echo 'Falls der erste Lauf abgebrochen ist (Log prüfen): die vier Backup-Dateien umbenennen und neu starten.'
    \quit
\endif

\echo '== 0. Backups (nur lesend)'
\copy (SELECT i.* FROM indicators i JOIN sources s ON s.id = i.source_id JOIN countries c ON c.iso_numeric = i.iso_numeric WHERE (s.short_code = 'TI' AND i.indicator_code = 'TI:CPI' AND c.iso_code_3 IN ('NGA','NER')) OR (s.short_code = 'FH' AND c.iso_code_3 IN ('NGA','NER','SRB')) OR (s.short_code = 'HENLEY' AND c.iso_code_3 = 'SRB') OR (s.short_code = 'WHR' AND c.iso_code_3 IN ('COD','COG','CYP')) OR (s.short_code = 'SAMAYO' AND c.iso_code_3 = 'GBR') OR s.short_code = 'EPR' ORDER BY i.id) TO 'backups/2026-11-24_ci172_vorher_indicators.csv' CSV HEADER
\copy (SELECT * FROM history.ethnic_groups WHERE country_name IN ('Niger','Kosovo') ORDER BY id) TO 'backups/2026-11-24_ci172_vorher_ethnic_groups.csv' CSV HEADER
\copy (SELECT * FROM culture.country_facts WHERE iso_numeric = '826') TO 'backups/2026-11-24_ci172_vorher_country_facts.csv' CSV HEADER
\copy (SELECT * FROM culture.national_dishes WHERE iso_numeric = '826') TO 'backups/2026-11-24_ci172_vorher_national_dishes.csv' CSV HEADER

BEGIN;

CREATE TEMP TABLE k (name text PRIMARY KEY, wert bigint) ON COMMIT DROP;   -- Kontrollwerte zwischen den Blöcken

\echo '== Vorher-Kontrolle'
DO $$
DECLARE
    soll  jsonb := '{"ind_gesamt":4123747, "ti_nga":13, "ti_ner":0, "fh_nga":88, "fh_ner":0, "fh_srb":38,
                     "henley_srb":4, "whr_cod":56, "whr_cog":0, "whr_cyp":56, "epr_nga":192, "epr_srb":54, "epr_ner":0,
                     "eg_gesamt":10769, "eg_niger_nga":60, "eg_kosovo":6, "eg_ner":0,
                     "cf_gesamt":240, "cf_gbr_england":1, "nd_gesamt":235, "nd_gbr_england":1,
                     "ki_gesamt":24, "ki_ci172":0}';
    ist   jsonb;
    fehler text := '';
    key   text;
BEGIN
    SELECT jsonb_build_object(
        'ind_gesamt',   (SELECT count(*) FROM indicators),
        'ti_nga',       (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '566'),
        'ti_ner',       (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '562'),
        'fh_nga',       (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '566'),
        'fh_ner',       (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '562'),
        'fh_srb',       (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '688'),
        'henley_srb',   (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'HENLEY:%' AND iso_numeric = '688'),
        'whr_cod',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '180'),
        'whr_cog',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '178'),
        'whr_cyp',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '196'),
        'epr_nga',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'EPR:%' AND iso_numeric = '566'),
        'epr_srb',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'EPR:%' AND iso_numeric = '688'),
        'epr_ner',      (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'EPR:%' AND iso_numeric = '562'),
        'eg_gesamt',    (SELECT count(*) FROM history.ethnic_groups),
        'eg_niger_nga', (SELECT count(*) FROM history.ethnic_groups WHERE country_name = 'Niger' AND iso_numeric = '566'),
        'eg_kosovo',    (SELECT count(*) FROM history.ethnic_groups WHERE country_name = 'Kosovo'),
        'eg_ner',       (SELECT count(*) FROM history.ethnic_groups WHERE iso_numeric = '562'),
        'cf_gesamt',    (SELECT count(*) FROM culture.country_facts),
        'cf_gbr_england',(SELECT count(*) FROM culture.country_facts WHERE iso_numeric = '826' AND country_name = 'England'),
        'nd_gesamt',    (SELECT count(*) FROM culture.national_dishes),
        'nd_gbr_england',(SELECT count(*) FROM culture.national_dishes WHERE iso_numeric = '826' AND country_name = 'England' AND dish = 'Cawl'),
        'ki_gesamt',    (SELECT count(*) FROM known_issues),
        'ki_ci172',     (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172%')
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint <> (soll ->> key)::bigint THEN
            fehler := fehler || format(' %s=%s (soll %s);', key, ist ->> key, soll ->> key);
        END IF;
    END LOOP;
    IF fehler <> '' THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch:%  Schon gelaufen oder Daten geändert?', fehler;
    END IF;
    INSERT INTO k VALUES ('ind_gesamt', (ist ->> 'ind_gesamt')::bigint),
                         ('epr_gesamt', (SELECT count(*) FROM indicators
                                         WHERE indicator_code IN ('EPR:n_groups','EPR:discriminated_share','EPR:excluded_share')));
    RAISE NOTICE 'Vorher-Kontrolle OK. EPR-Werte gesamt (3 Codes): %', (SELECT wert FROM k WHERE name = 'epr_gesamt');
END $$;

\echo '== Listen laden'
CREATE TEMP TABLE e_ind (id bigint PRIMARY KEY, short_code text, iso3 text, iso_numeric char(3), indicator_code text,
                         time_period text, value_db double precision, aktion text, ziel_iso_numeric char(3), beleg text)
    ON COMMIT DROP;
\copy e_ind FROM 'logs/migrations/ci172/entscheidung_indicators.csv' CSV HEADER
CREATE TEMP TABLE e_grp (id integer PRIMARY KEY, country_name text, iso_numeric char(3), group_name text,
                         year_from int, year_to int, is_successor boolean, aktion text, ziel_iso_numeric char(3))
    ON COMMIT DROP;
\copy e_grp FROM 'logs/migrations/ci172/entscheidung_epr_gruppen.csv' CSV HEADER

DO $$
DECLARE n_um bigint; n_lo bigint; n_be bigint; n_treffer bigint; g_um bigint; g_lo bigint; g_be bigint;
BEGIN
    SELECT count(*) FILTER (WHERE aktion = 'umhaengen'), count(*) FILTER (WHERE aktion = 'loeschen'),
           count(*) FILTER (WHERE aktion = 'behalten')
      INTO n_um, n_lo, n_be FROM e_ind;
    SELECT count(*) INTO n_treffer
      FROM e_ind e JOIN indicators i ON i.id = e.id AND i.iso_numeric = e.iso_numeric
                                    AND i.indicator_code = e.indicator_code AND i.time_period = e.time_period
                                    AND i.value = e.value_db;
    SELECT count(*) FILTER (WHERE aktion = 'umhaengen'), count(*) FILTER (WHERE aktion = 'loeschen'),
           count(*) FILTER (WHERE aktion = 'behalten')
      INTO g_um, g_lo, g_be FROM e_grp;
    IF n_um <> 153 OR n_lo <> 280 OR n_be <> 70 OR n_treffer <> 503 OR g_um <> 60 OR g_lo <> 6 OR g_be <> 148 THEN
        RAISE EXCEPTION 'Listen falsch: indicators umhaengen=% (153) loeschen=% (280) behalten=% (70) in DB unverändert=% (503); Gruppen umhaengen=% (60) loeschen=% (6) behalten=% (148)',
            n_um, n_lo, n_be, n_treffer, g_um, g_lo, g_be;
    END IF;
    RAISE NOTICE 'Listen OK: alle 503 Zeilen unverändert in der DB';
END $$;

\echo '== A. umhängen (153) und B. löschen (280)'
DO $$
DECLARE n bigint;
BEGIN
    UPDATE indicators i SET iso_numeric = e.ziel_iso_numeric
      FROM e_ind e
     WHERE i.id = e.id AND e.aktion = 'umhaengen' AND i.iso_numeric = e.iso_numeric AND i.value = e.value_db;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 153 THEN RAISE EXCEPTION 'A umhängen: % statt 153', n; END IF;
    RAISE NOTICE 'A: % Werte umgehängt', n;

    DELETE FROM indicators i USING e_ind e
     WHERE i.id = e.id AND e.aktion = 'loeschen' AND i.iso_numeric = e.iso_numeric AND i.value = e.value_db;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 280 THEN RAISE EXCEPTION 'B löschen: % statt 280', n; END IF;
    RAISE NOTICE 'B: % Werte gelöscht', n;
END $$;

\echo '== C. EPR-Gruppen (Niger umhängen 60, Kosovo löschen 6) und D. SAMAYO GBR'
DO $$
DECLARE n bigint;
BEGIN
    UPDATE history.ethnic_groups g SET iso_numeric = e.ziel_iso_numeric
      FROM e_grp e
     WHERE g.id = e.id AND e.aktion = 'umhaengen' AND g.country_name = 'Niger' AND g.iso_numeric = '566';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 60 THEN RAISE EXCEPTION 'C umhängen: % statt 60', n; END IF;

    DELETE FROM history.ethnic_groups g USING e_grp e
     WHERE g.id = e.id AND e.aktion = 'loeschen' AND g.country_name = 'Kosovo';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 6 THEN RAISE EXCEPTION 'C löschen: % statt 6', n; END IF;

    DELETE FROM culture.country_facts WHERE iso_numeric = '826' AND country_name = 'England';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'D country_facts: % statt 1', n; END IF;

    DELETE FROM culture.national_dishes WHERE iso_numeric = '826' AND country_name = 'England' AND dish = 'Cawl';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'D national_dishes: % statt 1', n; END IF;
    RAISE NOTICE 'C und D OK';
END $$;

-- ===== Block E: NUR MIT ZUSTIMMUNG JULIAN (alle drei EPR-Codes zurückziehen) =====
\echo '== E. EPR: übrige Werte der drei Codes löschen'
DO $$
DECLARE n bigint; soll bigint;
BEGIN
    soll := (SELECT wert FROM k WHERE name = 'epr_gesamt') - 240;   -- 240 EPR-Zeilen (NGA 192, SRB 48) sind schon in B gelöscht
    DELETE FROM indicators WHERE indicator_code IN ('EPR:n_groups','EPR:discriminated_share','EPR:excluded_share');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> soll THEN RAISE EXCEPTION 'E EPR löschen: % statt %', n, soll; END IF;
    INSERT INTO k VALUES ('epr_e', n);
    RAISE NOTICE 'E: % EPR-Werte gelöscht', n;
END $$;
-- ===== Ende Block E =====

\echo '== F. known_issues'
INSERT INTO known_issues (scope, source_id, indicator_code, table_name, title, description, decision) VALUES
('source', (SELECT id FROM sources WHERE short_code = 'TI'), NULL, NULL,
 'CI-172 TI:CPI: Nigeria 2012–2024 ohne Werte (Werte waren Niger)',
 'economy/load_cpi.py ordnete „Niger“ per pycountry.search_fuzzy Nigeria zu; mit ON CONFLICT DO NOTHING wurden die Werte Nigerias verworfen. Am 24.11.2026 wurden die 13 Werte 2012–2024 auf Niger (NER) umgehängt (Abgleich mit TI CPI 2025, Zeile Niger). Nigeria hat bis zum Neuladen keine Werte. Loader gesperrt (CI-172); seine OWID-Suche liefert inzwischen einen anderen Datensatz.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'FH'), NULL, NULL,
 'CI-172 FH: Nigeria ohne Werte, Serbien ab 2009 ohne Werte (waren Niger bzw. Kosovo)',
 'governance/load_freedom_house.py ordnete per Fuzzy „Niger“ Nigeria und „Kosovo“ Serbien zu; jeweils gewann die zuerst gelesene Zeile (DO NOTHING). Am 24.11.2026 wurden 88 Werte (PR und CL 1972–2024) auf Niger umgehängt und 32 Kosovo-Werte bei Serbien (2009–2024) gelöscht. Serbien 2006–2008 ist echt. Nigeria und Serbien ab 2009 fehlen bis zum Neuladen; Kosovo wird verworfen (keine Zeile in countries).',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'FH'), NULL, NULL,
 'CI-172 FH: historische Einheiten nicht geladen',
 'Nicht zugeordnet und damit nicht geladen: Czechoslovakia, Germany E., Germany W., Serbia and Montenegro, USSR, Vietnam N., Vietnam S., Yemen N., Yemen S., Yugoslavia. Die BRD („Germany, W.“) ist nicht Deutschland zugeordnet. Gleiche Linie wie POLITY5 (known_issue 11): eigene Einheiten erst mit Weg A (CI-105).',
 'accepted'),
('source', (SELECT id FROM sources WHERE short_code = 'HENLEY'), NULL, NULL,
 'CI-172 HENLEY: Serbien ohne Werte (waren Kosovo), Eswatini fehlt',
 'international/load_henley.py ordnete per Fuzzy „Kosovo“ Serbien zu; die Kosovo-Zeile kam zuerst (DO NOTHING). Am 24.11.2026 wurden die 4 Werte bei Serbien gelöscht (= Kosovo laut passport-index-tidy.csv: visa required 75, e-visa 39, visa on arrival 27). „Swaziland“ wurde nicht zugeordnet, Eswatini fehlt. Beides bis zum Neuladen.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'EPR'), NULL, NULL,
 'CI-172 EPR: Indikatoren zurückgezogen (Definition und Länderzuordnung falsch)',
 'Laut EPR-Codebuch 2021 gelten als ausgeschlossen nur Powerless, Discrimination und Self-exclusion; Irrelevant und State collapse sind eigene Kategorien. history/load_epr.py zählte bei excluded_share IRRELEVANT mit und Self-exclusion nicht (Folge z. B. Korea 100 %), bei discriminated_share auch Powerless, bei n_groups auch irrelevante Gruppen. Dazu: Gruppen von Niger unter Nigeria, von Kosovo unter Serbien (Fuzzy); Russland ohne Werte (GW 365 als UdSSR behandelt). Am 24.11.2026 alle Werte von EPR:n_groups, EPR:discriminated_share und EPR:excluded_share gelöscht (Backup). Neuaufbau nach v1.0.',
 'to_fix'),
('table', (SELECT id FROM sources WHERE short_code = 'EPR'), NULL, 'history.ethnic_groups',
 'CI-172 history.ethnic_groups: Nachfolger-Logik und Russland nach 1991',
 'Am 24.11.2026 wurden 60 Zeilen mit country_name „Niger“ von Nigeria auf Niger umgehängt und 6 Zeilen „Kosovo“ gelöscht. Offen: GW 365 („Russia (Soviet Union)“, bei EPR eine durchgehende Einheit) wird als UdSSR behandelt und mit is_successor auf 15 Nachfolger verteilt, auch für Zeiträume nach 1991; Jugoslawien (GW 345) ebenso auf 6 Nachfolger. Neuaufbau nach v1.0 mit Gültigkeitsjahren in der Länderliste.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'WHR'), NULL, NULL,
 'CI-172 WHR: DR Kongo trug Werte der Republik Kongo, Zypern teils Nordzypern',
 'culture/load_whr.py ordnete per Teilstring „Congo“ DR Kongo und „North Cyprus“ Zypern zu; je Jahr und Spalte gewann die erste Zeile der Datei (DO NOTHING). Am 24.11.2026 wurden 52 Werte (2016–2025) von DR Kongo auf die Republik Kongo (COG) umgehängt und 4 Nordzypern-Werte bei Zypern (life_evaluation 2014–2017) gelöscht. DR Kongo hat nur noch 4 Werte (life_evaluation 2011, 2012, 2014, 2015). Beides bis zum Neuladen; Nordzypern wird verworfen.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'SAMAYO'), NULL, NULL,
 'CI-172 SAMAYO: GBR-Fakten gelöscht (stammten von England/Wales), DR Kongo fehlt',
 'culture/load_samayo.py und load_national_dishes.py ordneten per Fuzzy England, Schottland, Wales und Nordirland Großbritannien zu. culture.country_facts und culture.national_dishes trugen für GBR Angaben dieser Teile (country_name England, Fahrseite right, Gericht Cawl). Am 24.11.2026 beide GBR-Zeilen gelöscht; GBR fehlt dort bis zum Neuladen. Die Indikatoren has_national_dish (1) und landlocked (0) bleiben, sie gelten für GBR gleich. „The Democratic Republic of Congo“ wurde nicht zugeordnet, DR Kongo fehlt.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'KOF'), NULL, NULL,
 'CI-172 KOF: DR Kongo, Rumänien, Timor-Leste, Andorra, Palästina ohne Werte',
 'Die Rohdatei (kof_data_export_2026-05-28) nutzt alte Codes (zar, rom, tmp, ado, wbg); international/load_kof.py kennt nur heutige ISO3-Codes und verwirft unbekannte still. Ohne Werte bis zum Neuladen mit Länderliste.',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'CAF_WGI'), NULL, NULL,
 'CI-172 CAF_WGI: DR Kongo fehlt, Kongo lückenhaft, weitere Schreibweisen verworfen',
 'Nicht zugeordnet (Anzahl Werte): Congo Brazzaville 44, Democratic Republic of the Congo 40, Palestinian Territory 20, Palestinian Territories 16, Northern Cyprus 24, Somaliland 8, Somaliland (Region) 8, State of Libya 8, Central Africa Republic 4, CÔte d’Ivoire 4, Hong Kong S.A.R. of China 4, Swaziland 4, Nagorno-Karabakh Region 4; Kosovo 52 (bewusst, keine Zeile in countries). Der Loader ordnet „Columbia“ weiter Kanada zu (DB seit 15.11. korrigiert).',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'FSI'), NULL, NULL,
 'CI-172 FSI: 6 Länder nicht zugeordnet (Backlog #140)',
 'Namenszuordnung ohne Normalisierung, Fehlende werden still übersprungen: Congo Democratic Republic, Congo Republic, Guinea Bissau, Côte d''Ivoire, Sao Tome and Principe, Brunei Darussalam (Stand 15.11.2026).',
 'to_fix'),
('source', (SELECT id FROM sources WHERE short_code = 'GITOC'), NULL, NULL,
 'CI-172 GITOC: Länder nicht zugeordnet (Backlog #140)',
 'Alle Jahre: Sao Tome and Principe, Côte d''Ivoire, St. Kitts and Nevis, St. Lucia, St. Vincent and the Grenadines, Korea DPR, Korea Rep., Micronesia (Federated States of); 2023 zusätzlich beide Kongos und Schreibweisen mit Kommas (Stand 15.11.2026).',
 'to_fix'),
('table', NULL, NULL, 'public.diplomatic_representation',
 'CI-172 diplomatic_representation: Länder ohne Zuordnung verworfen',
 'international/load_ddr.py (Kopie: history/load_coups.py) verwirft nicht zugeordnete Namen still. Betroffen (Zeilen der Rohdatei, Sender und Empfänger zusammen): Holy See (Vatican) 9.463, Côte d''Ivoire 4.622, German Democratic Republic 2.927, Serbia and Montenegro 2.155, Yemen, People''s Democratic Republic of 866, Kosovo 657, Viet Nam, Republic of 545, Northern Cyprus 69, Viet Nam, Democratic Rep 21. Historische Einheiten und Kosovo bleiben bis Weg A verworfen; Côte d''Ivoire und Heiliger Stuhl sind echte Lücken.',
 'to_fix'),
('database', NULL, NULL, NULL,
 'CI-172 Kosovo: keine Zeile in countries, Werte aller Quellen verworfen',
 'Kosovo hat keinen ISO-Zahlencode; countries (Primärschlüssel iso_numeric) führt Kosovo nicht. Kosovo-Werte werden bis Weg A (CI-105) verworfen, Entscheidung Julian 24.11.2026. Kosovo-Daten haben u. a. FH, HENLEY, EPR, CAF_WGI, DDR, ILO (Code KOS), VDEM (XKX, known_issue 9), WB (XKX), WHR. Bei FH, HENLEY und EPR lagen sie bis 24.11.2026 fälschlich auf Serbien.',
 'accepted');

\echo '== Nachher-Kontrolle'
DO $$
DECLARE
    n_e   bigint := COALESCE((SELECT wert FROM k WHERE name = 'epr_e'), 0);
    soll  jsonb;
    ist   jsonb;
    fehler text := '';
    key   text;
BEGIN
    soll := jsonb_build_object(
        'ind_gesamt', (SELECT wert FROM k WHERE name = 'ind_gesamt') - 280 - n_e,
        'ti_nga', 0, 'ti_ner', 13, 'fh_nga', 0, 'fh_ner', 88, 'fh_srb', 6, 'henley_srb', 0,
        'whr_cod', 4, 'whr_cog', 52, 'whr_cyp', 52,
        'epr_3codes', CASE WHEN n_e > 0 THEN 0 ELSE (SELECT wert FROM k WHERE name = 'epr_gesamt') - 240 END,
        'eg_gesamt', 10763, 'eg_ner', 60, 'eg_kosovo', 0, 'eg_nga', 72,
        'cf_gesamt', 239, 'nd_gesamt', 234, 'ki_gesamt', 38, 'ki_ci172', 14);
    SELECT jsonb_build_object(
        'ind_gesamt', (SELECT count(*) FROM indicators),
        'ti_nga',     (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '566'),
        'ti_ner',     (SELECT count(*) FROM indicators WHERE indicator_code = 'TI:CPI' AND iso_numeric = '562'),
        'fh_nga',     (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '566'),
        'fh_ner',     (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '562'),
        'fh_srb',     (SELECT count(*) FROM indicators WHERE indicator_code IN ('FH:PR','FH:CL') AND iso_numeric = '688'),
        'henley_srb', (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'HENLEY:%' AND iso_numeric = '688'),
        'whr_cod',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '180'),
        'whr_cog',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '178'),
        'whr_cyp',    (SELECT count(*) FROM indicators WHERE indicator_code LIKE 'WHR:%' AND iso_numeric = '196'),
        'epr_3codes', (SELECT count(*) FROM indicators WHERE indicator_code IN ('EPR:n_groups','EPR:discriminated_share','EPR:excluded_share')),
        'eg_gesamt',  (SELECT count(*) FROM history.ethnic_groups),
        'eg_ner',     (SELECT count(*) FROM history.ethnic_groups WHERE iso_numeric = '562'),
        'eg_kosovo',  (SELECT count(*) FROM history.ethnic_groups WHERE country_name = 'Kosovo'),
        'eg_nga',     (SELECT count(*) FROM history.ethnic_groups WHERE iso_numeric = '566'),
        'cf_gesamt',  (SELECT count(*) FROM culture.country_facts),
        'nd_gesamt',  (SELECT count(*) FROM culture.national_dishes),
        'ki_gesamt',  (SELECT count(*) FROM known_issues),
        'ki_ci172',   (SELECT count(*) FROM known_issues WHERE title LIKE 'CI-172%')
    ) INTO ist;
    FOR key IN SELECT jsonb_object_keys(soll) LOOP
        IF (ist ->> key)::bigint <> (soll ->> key)::bigint THEN
            fehler := fehler || format(' %s=%s (soll %s);', key, ist ->> key, soll ->> key);
        END IF;
    END LOOP;
    IF fehler <> '' THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch:% Nichts geändert.', fehler;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: % Werte gesamt', ist ->> 'ind_gesamt';
END $$;

\echo '== G. indicator_coverage auffrischen'
REFRESH MATERIALIZED VIEW indicator_coverage;

COMMIT;
\echo '== fertig'
