-- =============================================================================
-- CI-1 Migration 1 (15.11.2026): source_id nachtragen für 7 Quellen, CAF Kolumbien 2011
--
-- Was passiert:
--   a) CAF_WGI: 4 Zeilen von Kanada (124) auf Kolumbien (170) 2011 umhängen.
--      Ursache: Die Quelle schreibt "Columbia", pycountry ordnet das unscharf Kanada zu.
--      Beleg: archive_CAF World Giving Index.zip, 2011.csv, Zeile "Columbia;45;38%;16;64%;73;25%;52;24%".
--   b) source_id aus indicator_metadata nachtragen für WID, PWT, UNHCR, SIPRI, PEW_REL, CAF_WGI
--      (alles Fall A laut Bestandsaufnahme: keine Dubletten, keine Kollisionen).
--   NICHT angefasst: GHI (6.535) und POLITY5 (101.643) – brauchen Loader-Korrektur und Neuladen.
--
-- Voraussetzung: Backup gelaufen (sql/03_queries/2026-11-15_ci1_backup.sql, 627.968 Zeilen mit Kopf).
-- Aufruf (Shell, Repo-Wurzel):
--   mkdir -p logs/migrations
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_ci1_migration1.sql > logs/migrations/2026-11-15_ci1_migration1.txt 2>&1
--
-- Erwartet vorher:  NULL gesamt 627.967; je Quelle wie Bestandsaufnahme B01; CAF-Zeilen Kanada 2011 = 8,
--                   Kolumbien 2011 = 0; Kollisionen = 0.
-- Erwartet nachher: NULL gesamt 108.178 (GHI 6.535 + POLITY5 101.643); 519.789 Zeilen mit neuer source_id;
--                   Kanada 2011 = 4, Kolumbien 2011 = 4; Zeilen in indicators unverändert.
-- Weicht etwas ab, bricht die Transaktion ab und nichts ist geändert.
-- =============================================================================

BEGIN;

CREATE TEMP TABLE ci1_kontrolle (schritt text, wert bigint) ON COMMIT DROP;

\echo '== Vorher: Werte ohne source_id je Quelle (laut Metadaten)'
SELECT s.short_code, count(*) AS null_zeilen
FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
WHERE i.source_id IS NULL GROUP BY 1 ORDER BY 2 DESC;

DO $$
DECLARE
    n_gesamt bigint; n_null bigint; n_wid bigint; n_pwt bigint; n_unhcr bigint; n_sipri bigint;
    n_pew bigint; n_caf bigint; n_ghi bigint; n_polity bigint;
    n_can bigint; n_col bigint; n_falsch bigint; n_koll bigint;
BEGIN
    SELECT count(*) INTO n_gesamt FROM indicators;
    INSERT INTO ci1_kontrolle VALUES ('zeilen_vorher', n_gesamt);

    SELECT count(*) FILTER (WHERE TRUE),
           count(*) FILTER (WHERE s.short_code = 'WID'),
           count(*) FILTER (WHERE s.short_code = 'PWT'),
           count(*) FILTER (WHERE s.short_code = 'UNHCR'),
           count(*) FILTER (WHERE s.short_code = 'SIPRI'),
           count(*) FILTER (WHERE s.short_code = 'PEW_REL'),
           count(*) FILTER (WHERE s.short_code = 'CAF_WGI'),
           count(*) FILTER (WHERE s.short_code = 'GHI'),
           count(*) FILTER (WHERE s.short_code = 'POLITY5')
      INTO n_null, n_wid, n_pwt, n_unhcr, n_sipri, n_pew, n_caf, n_ghi, n_polity
      FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
     WHERE i.source_id IS NULL;

    -- CAF 2011: Kanada (8 Zeilen = 4 echt + 4 Kolumbien), Kolumbien (0)
    SELECT count(*) FILTER (WHERE iso_numeric = '124'), count(*) FILTER (WHERE iso_numeric = '170')
      INTO n_can, n_col
      FROM indicators WHERE indicator_code LIKE 'CAF_WGI:%' AND time_period = '2011';

    -- Die 4 falsch zugeordneten Zeilen: genau diese IDs, Werte und Codes
    SELECT count(*) INTO n_falsch FROM indicators
     WHERE iso_numeric = '124' AND time_period = '2011' AND source_id IS NULL
       AND (id, indicator_code, value) IN ((3356026, 'CAF_WGI:total_score',       38),
                                           (3356027, 'CAF_WGI:helping_stranger',  64),
                                           (3356028, 'CAF_WGI:donating_money',    25),
                                           (3356029, 'CAF_WGI:volunteering_time', 24));

    -- Kollision: NULL-Zeile, deren Schlüssel mit Metadaten-Quelle schon existiert (würde UNIQUE verletzen)
    SELECT count(*) INTO n_koll
      FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
     WHERE i.source_id IS NULL
       AND s.short_code IN ('WID', 'PWT', 'UNHCR', 'SIPRI', 'PEW_REL', 'CAF_WGI')
       AND EXISTS (SELECT 1 FROM indicators q
                    WHERE q.iso_numeric = i.iso_numeric AND q.indicator_code = i.indicator_code
                      AND q.time_period = i.time_period AND q.source_id = x.source_id);

    IF n_null <> 627967 OR n_wid <> 274558 OR n_pwt <> 211399 OR n_unhcr <> 15161 OR n_sipri <> 8523
       OR n_pew <> 3184 OR n_caf <> 6964 OR n_ghi <> 6535 OR n_polity <> 101643
       OR n_can <> 8 OR n_col <> 0 OR n_falsch <> 4 OR n_koll <> 0 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: NULL=% (627967) WID=% (274558) PWT=% (211399) UNHCR=% (15161) SIPRI=% (8523) PEW=% (3184) CAF=% (6964) GHI=% (6535) POLITY5=% (101643) CAN2011=% (8) COL2011=% (0) falsch=% (4) Kollision=% (0)',
            n_null, n_wid, n_pwt, n_unhcr, n_sipri, n_pew, n_caf, n_ghi, n_polity, n_can, n_col, n_falsch, n_koll;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK (Zeilen gesamt %)', n_gesamt;
END $$;

\echo '== a) CAF: 4 Zeilen Kanada → Kolumbien 2011'
DO $$
DECLARE n bigint;
BEGIN
    UPDATE indicators SET iso_numeric = '170'
     WHERE iso_numeric = '124' AND time_period = '2011' AND source_id IS NULL
       AND (id, indicator_code, value) IN ((3356026, 'CAF_WGI:total_score',       38),
                                           (3356027, 'CAF_WGI:helping_stranger',  64),
                                           (3356028, 'CAF_WGI:donating_money',    25),
                                           (3356029, 'CAF_WGI:volunteering_time', 24));
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 4 THEN RAISE EXCEPTION 'CAF umgehängt: % (erwartet 4)', n; END IF;
    RAISE NOTICE 'CAF: % Zeilen auf Kolumbien umgehängt', n;
END $$;

\echo '== b) source_id aus den Metadaten nachtragen (6 Quellen)'
DO $$
DECLARE n bigint;
BEGIN
    UPDATE indicators i SET source_id = x.source_id
      FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
     WHERE i.indicator_code = x.indicator_code AND i.source_id IS NULL
       AND s.short_code IN ('WID', 'PWT', 'UNHCR', 'SIPRI', 'PEW_REL', 'CAF_WGI');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 519789 THEN RAISE EXCEPTION 'source_id nachgetragen: % (erwartet 519789)', n; END IF;
    RAISE NOTICE 'source_id nachgetragen: % Zeilen', n;
END $$;

DO $$
DECLARE n_gesamt bigint; n_vorher bigint; n_null bigint; n_rest6 bigint; n_ghi bigint; n_polity bigint;
        n_can bigint; n_col bigint; n_dubl bigint;
BEGIN
    SELECT count(*) INTO n_gesamt FROM indicators;
    SELECT wert INTO n_vorher FROM ci1_kontrolle WHERE schritt = 'zeilen_vorher';

    SELECT count(*),
           count(*) FILTER (WHERE s.short_code IN ('WID', 'PWT', 'UNHCR', 'SIPRI', 'PEW_REL', 'CAF_WGI')),
           count(*) FILTER (WHERE s.short_code = 'GHI'),
           count(*) FILTER (WHERE s.short_code = 'POLITY5')
      INTO n_null, n_rest6, n_ghi, n_polity
      FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
     WHERE i.source_id IS NULL;

    SELECT count(*) FILTER (WHERE iso_numeric = '124'), count(*) FILTER (WHERE iso_numeric = '170')
      INTO n_can, n_col
      FROM indicators WHERE indicator_code LIKE 'CAF_WGI:%' AND time_period = '2011';

    -- Keine Dubletten in den 6 Quellen nach dem Nachtragen
    SELECT count(*) INTO n_dubl FROM (
        SELECT 1 FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
         WHERE s.short_code IN ('WID', 'PWT', 'UNHCR', 'SIPRI', 'PEW_REL', 'CAF_WGI')
         GROUP BY i.iso_numeric, i.indicator_code, i.time_period HAVING count(*) > 1) d;

    IF n_gesamt <> n_vorher OR n_null <> 108178 OR n_rest6 <> 0 OR n_ghi <> 6535 OR n_polity <> 101643
       OR n_can <> 4 OR n_col <> 4 OR n_dubl <> 0 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: Zeilen=% (vorher %) NULL=% (108178) Rest6=% (0) GHI=% (6535) POLITY5=% (101643) CAN2011=% (4) COL2011=% (4) Dubletten=% (0)',
            n_gesamt, n_vorher, n_null, n_rest6, n_ghi, n_polity, n_can, n_col, n_dubl;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: % Zeilen, davon % noch ohne source_id (GHI %, POLITY5 %)',
        n_gesamt, n_null, n_ghi, n_polity;
END $$;

\echo '== Nachher: Werte je Quelle (die 6 Quellen)'
SELECT s.short_code, i.source_id, count(*) AS zeilen
FROM indicators i JOIN indicator_metadata x USING (indicator_code) JOIN sources s ON s.id = x.source_id
WHERE s.short_code IN ('WID', 'PWT', 'UNHCR', 'SIPRI', 'PEW_REL', 'CAF_WGI', 'GHI', 'POLITY5')
GROUP BY 1, 2 ORDER BY 1, 2 NULLS FIRST;

\echo '== CAF 2011 Kanada und Kolumbien'
SELECT c.iso_code_3, i.indicator_code, i.value, i.source_id
FROM indicators i JOIN countries c USING (iso_numeric)
WHERE i.indicator_code LIKE 'CAF_WGI:%' AND i.time_period = '2011' AND i.iso_numeric IN ('124', '170')
ORDER BY 1, 2;

COMMIT;

REFRESH MATERIALIZED VIEW indicator_coverage;
\echo '== Fertig. indicator_coverage aufgefrischt.'
