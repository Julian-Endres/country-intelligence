-- =============================================================================
-- Hofstede neu (15.11.2026): falsch zugeordnete Altwerte entfernen, known_issues anlegen
-- Backlog #102
--
-- Voraussetzung (in dieser Reihenfolge):
--   1. Backup der Altwerte (Shell, Repo-Wurzel):
--        psql -d country_intelligence -X -c "\copy (SELECT * FROM indicators WHERE indicator_code LIKE 'HOFSTEDE:%' ORDER BY id) TO 'backups/2026-11-15_hofstede_vorher.csv' CSV HEADER"
--      erwartet: COPY 293
--   2. Trockenlauf:   python scripts/pipeline/culture/load_hofstede.py
--      schreibt die Löschliste logs/migrations/2026-11-15_hofstede_altbestand.csv (293 Zeilen)
--   3. Schreiben:     python scripts/pipeline/culture/load_hofstede.py --schreiben
--      → 461 Werte unter time_period '2015'
--
-- Was passiert:
--   a) DELETE der 293 Altzeilen mit time_period 'static' (Ladung 25.05.2026). Gelöscht wird nur, was
--      genau so in der Löschliste steht (Land, Code, Wert). 71 davon lagen am falschen Land (z. B.
--      Deutschland mit den Werten Dänemarks), 78 bei Ländern ohne Wert in der Quelle (z. B. Bolivien,
--      Afghanistan, Guam), 144 waren zufällig richtig und sind im Neuladen enthalten.
--   b) Drei known_issues (scope source) für HOFSTEDE.
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_hofstede_neu.sql > logs/migrations/2026-11-15_hofstede_neu.txt 2>&1
--
-- Erwartet vorher:  HOFSTEDE 'static' 293, '2015' 461, andere time_period 0, known_issues HOFSTEDE 0.
-- Erwartet nachher: HOFSTEDE nur '2015', 461 Werte (pdi/idv/mas/uai je 69, lto 92, ivr 93), 101 Länder,
--                   3 known_issues. Weicht etwas ab, bricht die Transaktion ab und nichts ist geändert.
-- Unabhängige Kontrolle danach (psql):
--   SELECT time_period, count(*), count(DISTINCT iso_numeric) FROM indicators
--   WHERE indicator_code LIKE 'HOFSTEDE:%' GROUP BY 1;          -- erwartet: 2015 | 461 | 101
-- =============================================================================

BEGIN;

DO $$
DECLARE n_static bigint; n_2015 bigint; n_andere bigint; n_ki bigint; src int;
BEGIN
    SELECT id INTO src FROM sources WHERE short_code = 'HOFSTEDE';
    SELECT count(*) FILTER (WHERE time_period = 'static'),
           count(*) FILTER (WHERE time_period = '2015'),
           count(*) FILTER (WHERE time_period NOT IN ('static', '2015'))
      INTO n_static, n_2015, n_andere
      FROM indicators WHERE indicator_code LIKE 'HOFSTEDE:%';
    SELECT count(*) INTO n_ki FROM known_issues WHERE source_id = src OR indicator_code LIKE 'HOFSTEDE:%';
    IF src IS NULL OR n_static <> 293 OR n_2015 <> 461 OR n_andere <> 0 OR n_ki <> 0 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: source_id=% static=% (293) 2015=% (461) andere=% (0) known_issues HOFSTEDE=% (0). Loader schon gelaufen?',
            src, n_static, n_2015, n_andere, n_ki;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK (source_id HOFSTEDE = %)', src;
END $$;

\echo '== a) Altzeilen (static) nach Liste löschen'
CREATE TEMP TABLE hof_alt (iso_numeric char(3), iso3 text, land text, indicator_code text,
                           time_period text, value_db double precision, wert_quelle double precision,
                           urteil text) ON COMMIT DROP;
\copy hof_alt FROM 'logs/migrations/2026-11-15_hofstede_altbestand.csv' CSV HEADER

DO $$
DECLARE n_liste bigint; n bigint;
BEGIN
    SELECT count(*) INTO n_liste FROM hof_alt WHERE time_period = 'static';
    IF n_liste <> 293 THEN RAISE EXCEPTION 'Löschliste hat % static-Zeilen (erwartet 293)', n_liste; END IF;
    DELETE FROM indicators i USING hof_alt z
     WHERE i.indicator_code = z.indicator_code AND i.iso_numeric = z.iso_numeric
       AND i.time_period = 'static' AND z.time_period = 'static' AND i.value = z.value_db;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 293 THEN RAISE EXCEPTION 'Gelöscht: % (erwartet 293). Werte in der DB weichen von der Liste ab.', n; END IF;
    RAISE NOTICE 'Gelöscht: % Zeilen', n;
END $$;

\echo '== b) known_issues HOFSTEDE'
INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'HOFSTEDE: Regionen und Teilgruppen nicht geladen',
       'Die Datei der Dimension Data Matrix enthält neben Ländern 3 Regionen (Africa East, Africa West, Arab countries) '
       || 'und 7 Teilgruppen eines Landes (Belgium French, Belgium Netherl, Canada French, Germany East, South Africa white, '
       || 'Switzerland French, Switzerland German). Sie sind nicht geladen (44 Werte), weil die DB nur Länder kennt; der '
       || 'Landeswert steht jeweils in einer eigenen Zeile (Belgium, Canada, Germany, South Africa, Switzerland). Folge: '
       || 'Arabische, ost- und westafrikanische Länder ohne eigene Zeile haben keine Hofstede-Werte. Die Kürzel der Datei '
       || '(Spalte ctr) sind keine ISO-Codes (BEN = Belgien flämisch, CAF = Kanada französisch, MNG = Montenegro, '
       || 'SLV = Slowenien, MAC = Nordmazedonien). Zuordnung nur über die feste Liste in load_hofstede.py.',
       'accepted'
FROM sources s WHERE s.short_code = 'HOFSTEDE';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'HOFSTEDE: Fassung ohne 0–100-Begrenzung, 6 Werte über 100',
       'Geladen ist die Hauptdatei der Dimension Data Matrix, nicht die Zusatzfassung „0-100“. Laut Website liegen einige '
       || 'Werte aus Replikationsstudien außerhalb 0–100; in der Zusatzfassung sind sie angepasst. Über 100 in der DB: '
       || 'Malaysia pdi 104, Slowakei pdi 104 und mas 110, Griechenland uai 112, Portugal uai 104, Guatemala uai 101 '
       || '(dazu Uruguay uai 100, in der Zusatzfassung 98). Für Rankings unschädlich, für Darstellungen mit fester '
       || 'Skala 0–100 beachten. Quelle: geerthofstede.com/research-and-vsm/dimension-data-matrix (gelesen 15.11.2026).',
       'accepted'
FROM sources s WHERE s.short_code = 'HOFSTEDE';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'HOFSTEDE: Zeitbezug = Ausgabe 2015, kein Erhebungsjahr; lto ist die WVS-Fassung',
       'Die Werte sind ein Querschnitt ohne Erhebungsjahr. Laut Website entsprechen sie dem Buch Cultures and Organizations, '
       || '3. Auflage 2010; die Datei trägt die Version 2015. time_period ist deshalb ''2015'' (Jahr der Ausgabe, Regel '
       || 'P19), nicht das Jahr einer Messung. HOFSTEDE:lto stammt aus der Spalte ltowvs der Datei (Langzeitorientierung '
       || 'auf Basis des World Values Survey). Abdeckung je Dimension verschieden: pdi, idv, mas, uai je 69 Länder, '
       || 'lto 92, ivr 93. Die Website rät selbst, die Werte „with a grain of salt“ zu nehmen.',
       'accepted'
FROM sources s WHERE s.short_code = 'HOFSTEDE';

DO $$
DECLARE n bigint; n_static bigint; n_laender bigint; n_ki bigint; src int;
        c_pdi bigint; c_idv bigint; c_mas bigint; c_uai bigint; c_lto bigint; c_ivr bigint;
        deu_pdi double precision; usa_idv double precision; dnk_pdi double precision; n_bol bigint;
BEGIN
    SELECT id INTO src FROM sources WHERE short_code = 'HOFSTEDE';
    SELECT count(*), count(*) FILTER (WHERE time_period <> '2015'), count(DISTINCT iso_numeric),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:pdi'),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:idv'),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:mas'),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:uai'),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:lto'),
           count(*) FILTER (WHERE indicator_code = 'HOFSTEDE:ivr'),
           count(*) FILTER (WHERE iso_numeric = '068')
      INTO n, n_static, n_laender, c_pdi, c_idv, c_mas, c_uai, c_lto, c_ivr, n_bol
      FROM indicators WHERE indicator_code LIKE 'HOFSTEDE:%';
    SELECT value INTO deu_pdi FROM indicators WHERE indicator_code = 'HOFSTEDE:pdi' AND iso_numeric = '276';
    SELECT value INTO dnk_pdi FROM indicators WHERE indicator_code = 'HOFSTEDE:pdi' AND iso_numeric = '208';
    SELECT value INTO usa_idv FROM indicators WHERE indicator_code = 'HOFSTEDE:idv' AND iso_numeric = '840';
    SELECT count(*) INTO n_ki FROM known_issues WHERE source_id = src;
    IF n <> 461 OR n_static <> 0 OR n_laender <> 101 OR c_pdi <> 69 OR c_idv <> 69 OR c_mas <> 69 OR c_uai <> 69
       OR c_lto <> 92 OR c_ivr <> 93 OR n_bol <> 0 OR deu_pdi IS DISTINCT FROM 35 OR dnk_pdi IS DISTINCT FROM 18
       OR usa_idv IS DISTINCT FROM 91 OR n_ki <> 3 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: gesamt=% (461) nicht 2015=% (0) Länder=% (101) pdi=% idv=% mas=% uai=% (je 69) lto=% (92) ivr=% (93) Bolivien=% (0) DEU pdi=% (35) DNK pdi=% (18) USA idv=% (91) known_issues=% (3)',
            n, n_static, n_laender, c_pdi, c_idv, c_mas, c_uai, c_lto, c_ivr, n_bol, deu_pdi, dnk_pdi, usa_idv, n_ki;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: HOFSTEDE 461 Werte, 101 Länder, nur 2015, Stichproben DEU/DNK/USA gleich der Datei, 3 known_issues';
END $$;

COMMIT;

REFRESH MATERIALIZED VIEW indicator_coverage;
\echo '== Fertig. indicator_coverage aufgefrischt.'
