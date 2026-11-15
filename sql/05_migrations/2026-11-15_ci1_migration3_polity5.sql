-- =============================================================================
-- CI-1 Migration 3 (15.11.2026): POLITY5-Altbestand ohne source_id entfernen, known_issues anlegen
-- Backlog #1 (letzte Quelle ohne source_id) und #89 (Sondercodes, zusammengelegte Staaten)
--
-- Voraussetzung:
--   1. Backup: backups/2026-11-15_ci1_null_vorher.csv enthält alle 101.643 POLITY5-Zeilen ohne source_id
--      (geprüft 15.11.: 101.643 Zeilen, 101.058 Land/Code/Jahr-Paare).
--   2. Neuer Loader hat geschrieben:  python scripts/pipeline/governance/load_polity5.py --schreiben
--      → 92.439 Werte unter source_id POLITY5 (Trockenlauf 17:14: alle 92.439 gleich dem Altbestand).
--
-- Was passiert:
--   a) DELETE der 101.643 POLITY5-Zeilen ohne source_id (Ladung 27.05.). Darin: 3.160 Sondercode-Zeilen
--      (-66/-77/-88), 585 Dubletten-Zeilen (DDR+BRD → DEU u. a.), Fehlzuordnungen (Baden → Barbados,
--      Modena → Moldau, Sardinien → Saudi-Arabien, Parma → Panama, Zentralamerika → Uganda) und die
--      Vorgängerstaaten. Liste: logs/migrations/2026-11-15_polity5_altbestand_ohne_entsprechung.csv
--   b) Drei known_issues (scope source) für POLITY5.
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_ci1_migration3_polity5.sql > logs/migrations/2026-11-15_ci1_migration3_polity5.txt 2>&1
--
-- Erwartet vorher:  POLITY5 ohne source_id 101.643; mit source_id 92.439; NULL gesamt 101.643.
-- Erwartet nachher: NULL gesamt 0 (Backlog #1 erledigt); POLITY5 92.439; keine Sondercodes; keine Dubletten.
-- Weicht etwas ab, bricht die Transaktion ab und nichts ist geändert.
-- =============================================================================

BEGIN;

DO $$
DECLARE n_null_p bigint; n_p bigint; n_null bigint; n_ki bigint; src int;
BEGIN
    SELECT id INTO src FROM sources WHERE short_code = 'POLITY5';
    SELECT count(*) INTO n_null_p FROM indicators WHERE indicator_code LIKE 'POLITY5:%' AND source_id IS NULL;
    SELECT count(*) INTO n_p      FROM indicators WHERE indicator_code LIKE 'POLITY5:%' AND source_id = src;
    SELECT count(*) INTO n_null   FROM indicators WHERE source_id IS NULL;
    SELECT count(*) INTO n_ki     FROM known_issues WHERE source_id = src OR indicator_code LIKE 'POLITY5:%';
    IF n_null_p <> 101643 OR n_p <> 92439 OR n_null <> 101643 OR n_ki <> 0 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: POLITY5 ohne Quelle=% (101643) mit Quelle=% (92439) NULL gesamt=% (101643) known_issues POLITY5=% (0)',
            n_null_p, n_p, n_null, n_ki;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK (source_id POLITY5 = %)', src;
END $$;

\echo '== a) POLITY5-Zeilen ohne source_id löschen'
DO $$
DECLARE n bigint;
BEGIN
    DELETE FROM indicators WHERE indicator_code LIKE 'POLITY5:%' AND source_id IS NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 101643 THEN RAISE EXCEPTION 'Gelöscht: % (erwartet 101643)', n; END IF;
    RAISE NOTICE 'Gelöscht: % Zeilen', n;
END $$;

\echo '== b) known_issues POLITY5'
INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'POLITY5: Vorgängerstaaten und historische Einheiten nicht geladen',
       'Polity führt Staaten bei Teilung, Vereinigung oder Abspaltung als neue Einheit mit eigenem Code (Handbuch v2018, '
       || 'Anhang A). Geladen sind nur die 166 Einheiten, die einem heutigen Staat entsprechen, jeweils mit ihrer ganzen Reihe '
       || '(z. B. GMY: Preußen 1800–1867, Deutsches Reich bis 1945, Deutschland ab 1990; RUS: Russisches Reich bis 1922, '
       || 'Russland ab 1992; SER: Serbien 1830–1920 und ab 2006). Nicht geladen (8.112 Werte, Entscheidung Julian 15.11.2026): '
       || 'Vorgängerstaaten GFR und GDR (1945–1990), USR (1922–1991), YUG (1921–1991), YGS (1991–2006), CZE Tschechoslowakei '
       || '(1918–1992), YAR und YPR (Jemen bis 1990), DRV und RVN (Vietnam bis 1976), ETH Äthiopien mit Eritrea (1855–1993), '
       || 'PKS Pakistan mit Bangladesch (1947–1971), SUD Sudan mit Südsudan (1956–2011); historische Einheiten ohne heutigen Staat '
       || '(Baden, Bayern, Sachsen, Württemberg, Modena, Parma, Kirchenstaat, Sardinien, Beide Sizilien, Toskana, Großkolumbien, '
       || 'Zentralamerikanische Föderation, Oranje-Freistaat, Korea 1800–1910); Kosovo (2008–2018, fehlt in countries). '
       || 'Folge: z. B. keine POLITY5-Werte für Deutschland 1946–1989 und Russland 1922–1991. Nachladen als eigene historische '
       || 'Einheiten mit ISO-Zahlencode (278, 280, 810, 890 …) und Gültigkeitszeitraum: Backlog #105. Rohdatei unverändert in '
       || 'data/raw/history, Liste im Trockenlauf logs/migrations/2026-11-15_polity5_trocken.txt.',
       'to_fix'
FROM sources s WHERE s.short_code = 'POLITY5';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'POLITY5: Sondercodes -66/-77/-88 nicht als Werte geladen',
       'In democ, autoc, xconst und polcomp stehen in der Quelle bei besonderen Lagen Standardcodes statt Skalenwerten: '
       || '-66 Fremdherrschaft/Besatzung, -77 Interregnum (Zusammenbruch der Zentralgewalt), -88 Übergangsphase (Handbuch v2018, '
       || 'Abschnitt 3). Sie werden nicht geladen (2.992 Werte der geladenen Einheiten); das Land-Jahr fehlt dann in diesen vier Codes. '
       || 'polity2 enthält die Codes nicht: Polity setzt -66 auf leer, -77 auf 0 und verteilt -88 linear über die Übergangsjahre. '
       || 'Für Zeitreihen deshalb polity2 nehmen; Lücken in democ/autoc sind Absicht, keine Ladefehler.',
       'accepted'
FROM sources s WHERE s.short_code = 'POLITY5';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'POLITY5: Datenstand 2018, nur USA bis 2020; Projekt ohne reguläre Updates',
       'Die Datei p5v2018 reicht bis 2018, nur die USA haben Werte für 2019 und 2020. Querschnittsvergleiche nach 2018 sind '
       || 'nicht möglich. Laut Center for Systemic Peace endete die US-Regierungsfinanzierung im Februar 2020, weitere Updates '
       || 'sind verzögert (Webseite, nicht wörtlich geprüft; Leitfaden-Lauf 2026-11-15_1713). Für aktuelle Jahre V-Dem nutzen. '
       || 'FLAG 1/2 markiert in der Quelle vorläufige bzw. unsichere Codierungen, ist nicht geladen.',
       'accepted'
FROM sources s WHERE s.short_code = 'POLITY5';

DO $$
DECLARE n_null bigint; n_p bigint; n_sonder bigint; n_dubl bigint; n_ki bigint; src int;
        c_pol2 bigint; c_dem bigint; c_aut bigint; c_dur bigint; c_xc bigint; c_pc bigint;
BEGIN
    SELECT id INTO src FROM sources WHERE short_code = 'POLITY5';
    SELECT count(*) INTO n_null FROM indicators WHERE source_id IS NULL;
    SELECT count(*),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:polity2'),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:democ'),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:autoc'),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:durable'),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:xconst'),
           count(*) FILTER (WHERE indicator_code = 'POLITY5:polcomp'),
           count(*) FILTER (WHERE value IN (-66, -77, -88))
      INTO n_p, c_pol2, c_dem, c_aut, c_dur, c_xc, c_pc, n_sonder
      FROM indicators WHERE indicator_code LIKE 'POLITY5:%';
    SELECT count(*) INTO n_dubl FROM (
        SELECT 1 FROM indicators WHERE indicator_code LIKE 'POLITY5:%'
        GROUP BY iso_numeric, indicator_code, time_period HAVING count(*) > 1) d;
    SELECT count(*) INTO n_ki FROM known_issues WHERE source_id = src;
    IF n_null <> 0 OR n_p <> 92439 OR c_pol2 <> 15909 OR c_dem <> 15394 OR c_aut <> 15394 OR c_dur <> 15080
       OR c_xc <> 15394 OR c_pc <> 15268 OR n_sonder <> 0 OR n_dubl <> 0 OR n_ki <> 3 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: NULL gesamt=% (0) POLITY5=% (92439) polity2=% (15909) democ=% (15394) autoc=% (15394) durable=% (15080) xconst=% (15394) polcomp=% (15268) Sondercodes=% (0) Dubletten=% (0) known_issues=% (3)',
            n_null, n_p, c_pol2, c_dem, c_aut, c_dur, c_xc, c_pc, n_sonder, n_dubl, n_ki;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: 0 Werte ohne source_id, POLITY5 92439 Werte, 3 known_issues';
END $$;

COMMIT;

REFRESH MATERIALIZED VIEW indicator_coverage;
\echo '== Fertig. indicator_coverage aufgefrischt.'
