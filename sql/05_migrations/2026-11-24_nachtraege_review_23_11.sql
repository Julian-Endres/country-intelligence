-- =============================================================================
-- #170 Nachträge zum Review der Sekretär-Läufe vom 23./24.11. (24.11.2026, Claude, Entscheidungen Julian 24.11.)
--
--   A  EMBER:renewables_share_energy -> EI:renewables_share_energy
--      (Codebook: einzige Quelle Energy Institute; Regel 24.11. Präfix = Urheber)
--      Metadaten, Werte und known_issues auf den neuen Code UND auf die Quelle EI.
--   B  Name NOBEL:total: "(excl. Economics)", solange der Loader den Wirtschaftspreis nicht zählt
--   C  Name HENLEY:visa_free_total: "(no prior visa)" ist falsch (e-Visa wird vorab beantragt)
--   D  Bezugsweg OWID wieder vor reference setzen (Regel CI-171 G): Die Läufe vom 23.11. ersetzen
--      reference für EI (6), EMBER (5), EIA (1), TI (1), RSF (1) und verlieren damit den Bezugsweg.
--      Gleiche Texte wie CI-171, nur wo er fehlt; läuft NACH A (EI:renewables_share_energy bekommt EI).
--
-- VORAUSSETZUNG: review.py + apply.py für EMBER 2113, NOBEL 1846, HENLEY 2144 sind gelaufen.
--   Jede Änderung ist an den Wert gebunden, den diese Läufe gesetzt haben. Sonst Abbruch (A)
--   bzw. UPDATE 0 (B, C) – nichts lässt sich doppelt ausführen.
-- Loader: load_owid_energy.py Z. 30 im selben Commit auf EI umgestellt.
--
-- PROBELAUF ist Standard (ROLLBACK). Erst mit -v ausfuehren=1 wird COMMIT gemacht.
-- Aufruf (Shell, Repo-Wurzel):
--   Probelauf:  psql -d country_intelligence -X -f sql/05_migrations/2026-11-24_nachtraege_review_23_11.sql > logs/migrations/2026-11-24_nachtraege_170_probelauf.txt 2>&1
--   Backup:     pg_dump -Fc -d country_intelligence -f backups/db_backup_20261124_vor_170.dump
--   Ausführen:  psql -d country_intelligence -X -v ausfuehren=1 -f sql/05_migrations/2026-11-24_nachtraege_review_23_11.sql > logs/migrations/2026-11-24_nachtraege_170.txt 2>&1
--   Danach:     psql -d country_intelligence -X -c "REFRESH MATERIALIZED VIEW indicator_coverage;"
-- =============================================================================

\set ON_ERROR_STOP on
\if :{?ausfuehren}
\else
  \set ausfuehren 0
\endif

\echo '=================== VORHER ==================='
SELECT count(*) AS werte_gesamt FROM indicators;
SELECT count(*) AS codes_gesamt FROM indicator_metadata;
SELECT indicator_code, source_id, count(*) AS werte FROM indicators
WHERE indicator_code IN ('EMBER:renewables_share_energy','EI:renewables_share_energy')
GROUP BY 1, 2;
SELECT id, short_code FROM sources WHERE short_code IN ('EI','EMBER') ORDER BY id;

BEGIN;

-- -----------------------------------------------------------------------------
\echo '== A  EMBER:renewables_share_energy -> EI:renewables_share_energy'
DO $$
DECLARE n_meta int; n_ziel int; n_werte bigint; n_ei int;
BEGIN
  SELECT count(*) INTO n_meta FROM indicator_metadata
  WHERE indicator_code = 'EMBER:renewables_share_energy'
    AND name = 'Share of primary energy consumption that comes from renewables';   -- gesetzt von Lauf 2113
  SELECT count(*) INTO n_ziel FROM indicator_metadata WHERE indicator_code = 'EI:renewables_share_energy';
  SELECT count(*) INTO n_werte FROM indicators WHERE indicator_code = 'EMBER:renewables_share_energy';
  SELECT count(*) INTO n_ei FROM sources WHERE short_code = 'EI';
  RAISE NOTICE 'A vorher: Metadaten aus Lauf 2113 %, Zielcode schon da %, Werte %, Quelle EI %', n_meta, n_ziel, n_werte, n_ei;
  IF n_meta <> 1 THEN RAISE EXCEPTION 'A: Lauf 2113 ist nicht übertragen (oder Code schon umbenannt) – Abbruch'; END IF;
  IF n_ziel <> 0 THEN RAISE EXCEPTION 'A: EI:renewables_share_energy gibt es schon – Abbruch'; END IF;
  IF n_ei <> 1 THEN RAISE EXCEPTION 'A: Quelle EI nicht eindeutig – Abbruch'; END IF;
  IF n_werte <> 4459 THEN RAISE EXCEPTION 'A: Soll 4.459 Werte (Lauf 2113), ist % – Abbruch', n_werte; END IF;
END $$;

-- 1. neue Metadaten-Zeile als Kopie, Quelle EI
INSERT INTO indicator_metadata (indicator_code, name, description, unit, source_id, category, domain, dimension,
       direction, scale_type, scale_min, scale_max, data_origin, temporal_type, is_lead_indicator, keywords,
       reference, loader_script, status, metadata_reviewed_at, added_at, key_info, producer_definition, value_labels)
SELECT 'EI:renewables_share_energy', m.name, m.description, m.unit,
       (SELECT id FROM sources WHERE short_code = 'EI'),
       m.category, m.domain, m.dimension,
       m.direction, m.scale_type, m.scale_min, m.scale_max, m.data_origin, m.temporal_type, m.is_lead_indicator, m.keywords,
       m.reference, m.loader_script, m.status, m.metadata_reviewed_at, m.added_at,
       -- key_info-Punkt zur Quelle passt nach der Umbenennung nicht mehr wörtlich
       array_replace(m.key_info,
         'According to the codebook the only underlying source is the Energy Institute Statistical Review, not Ember.',
         'According to the codebook the only underlying source is the Energy Institute Statistical Review (code formerly EMBER:renewables_share_energy).'),
       m.producer_definition, m.value_labels
FROM indicator_metadata m WHERE m.indicator_code = 'EMBER:renewables_share_energy';

-- 2. Werte und known_issues umhängen (Code und Quelle)
UPDATE indicators
SET indicator_code = 'EI:renewables_share_energy', source_id = (SELECT id FROM sources WHERE short_code = 'EI')
WHERE indicator_code = 'EMBER:renewables_share_energy';
UPDATE known_issues
SET indicator_code = 'EI:renewables_share_energy', source_id = (SELECT id FROM sources WHERE short_code = 'EI')
WHERE indicator_code = 'EMBER:renewables_share_energy';

-- 3. alte Metadaten-Zeile löschen
DELETE FROM indicator_metadata WHERE indicator_code = 'EMBER:renewables_share_energy';

DO $$
DECLARE n_alt int; n_neu int; n_werte bigint; n_falsch bigint; n_ki int;
BEGIN
  SELECT count(*) INTO n_alt FROM indicator_metadata WHERE indicator_code = 'EMBER:renewables_share_energy';
  SELECT count(*) INTO n_neu FROM indicator_metadata m JOIN sources s ON s.id = m.source_id
  WHERE m.indicator_code = 'EI:renewables_share_energy' AND s.short_code = 'EI';
  SELECT count(*) INTO n_werte FROM indicators WHERE indicator_code = 'EI:renewables_share_energy';
  SELECT count(*) INTO n_falsch FROM indicators i JOIN indicator_metadata m USING (indicator_code)
  WHERE i.indicator_code = 'EI:renewables_share_energy' AND i.source_id IS DISTINCT FROM m.source_id;
  SELECT count(*) INTO n_ki FROM indicator_metadata
  WHERE indicator_code = 'EI:renewables_share_energy' AND array_to_string(key_info, ' ') LIKE '%not Ember%';
  RAISE NOTICE 'A nachher: alt %, neu (Quelle EI) %, Werte %, Werte mit falscher Quelle %, key_info alt %',
               n_alt, n_neu, n_werte, n_falsch, n_ki;
  IF n_alt <> 0 OR n_neu <> 1 OR n_werte <> 4459 OR n_falsch <> 0 OR n_ki <> 0 THEN
    RAISE EXCEPTION 'A: Kontrollzahlen nach dem Umbenennen falsch – Abbruch';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '== B  Name NOBEL:total (Soll: UPDATE 1)'
UPDATE indicator_metadata
SET name = 'Nobel Prize Laureates – Total (excl. Economics)'
WHERE indicator_code = 'NOBEL:total'
  AND name = 'Nobel Prize Laureates – Total';

-- -----------------------------------------------------------------------------
\echo '== C  Name HENLEY:visa_free_total (Soll: UPDATE 1)'
UPDATE indicator_metadata
SET name = 'Passport: Destinations without a required visa (incl. e-visa and visa on arrival)'
WHERE indicator_code = 'HENLEY:visa_free_total'
  AND name = 'Passport: Total accessible destinations (no prior visa)';

-- -----------------------------------------------------------------------------
\echo '== D  Bezugsweg OWID wieder vor reference (Regel CI-171 G)'
\echo '-- vorher: Codes ohne Bezugsweg je Präfix'
SELECT split_part(indicator_code, ':', 1) AS praefix, count(*) AS codes,
       count(*) FILTER (WHERE coalesce(reference, '') NOT LIKE 'Retrieved via Our World in Data%') AS ohne_bezugsweg
FROM indicator_metadata
WHERE split_part(indicator_code, ':', 1) IN ('TI','RSF','EI','EMBER','EIA','OWID_CO2')
GROUP BY 1 ORDER BY 1;

UPDATE indicator_metadata m
SET reference = v.weg || coalesce(' · ' || nullif(m.reference, ''), '')
FROM (VALUES
  ('TI',       'Retrieved via Our World in Data (owid.catalog, search "corruption"); originator: Transparency International'),
  ('RSF',      'Retrieved via Our World in Data (grapher press-freedom-index-rsf.csv, file as of 2022); originator: RSF'),
  ('EI',       'Retrieved via Our World in Data (owid-energy-data); originator: Energy Institute'),
  ('EMBER',    'Retrieved via Our World in Data (owid-energy-data); originator: Ember'),
  ('EIA',      'Retrieved via Our World in Data (owid-energy-data); originator: U.S. EIA'),
  ('OWID_CO2', 'Retrieved via Our World in Data (owid-co2-data); originators per variable (GCP, PRIMAP, Maddison, …)')
) AS v(praefix, weg)
WHERE split_part(m.indicator_code, ':', 1) = v.praefix
  AND coalesce(m.reference, '') NOT LIKE 'Retrieved via Our World in Data%';
\echo '-- Soll: UPDATE 14 (EI 6, EMBER 4, EIA 1, TI 1, RSF 1, dazu EI:renewables_share_energy aus A)'

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM indicator_metadata
  WHERE split_part(indicator_code, ':', 1) IN ('TI','RSF','EI','EMBER','EIA','OWID_CO2')
    AND coalesce(reference, '') NOT LIKE 'Retrieved via Our World in Data%';
  RAISE NOTICE 'D nachher: Codes ohne Bezugsweg %', n;
  IF n <> 0 THEN RAISE EXCEPTION 'D: Es fehlen noch Bezugswege – Abbruch'; END IF;
END $$;

-- -----------------------------------------------------------------------------
\echo '=================== NACHHER ==================='
SELECT count(*) AS werte_gesamt FROM indicators;
\echo '-- Soll: wie vorher'
SELECT count(*) AS codes_gesamt FROM indicator_metadata;
\echo '-- Soll: wie vorher (1 neu, 1 weg)'
SELECT count(*) AS r2_2 FROM indicators i JOIN indicator_metadata m USING (indicator_code)
WHERE i.source_id IS DISTINCT FROM m.source_id;
\echo '-- R2.2: Soll 0'
SELECT count(*) AS r3_4 FROM indicator_metadata x JOIN sources s ON s.id = x.source_id
WHERE split_part(x.indicator_code, ':', 1) <> s.short_code;
\echo '-- R3.4: Soll 0'
SELECT indicator_code, name FROM indicator_metadata
WHERE indicator_code IN ('EI:renewables_share_energy','NOBEL:total','HENLEY:visa_free_total') ORDER BY 1;

\if :ausfuehren
  COMMIT;
  \echo '>>> COMMIT ausgeführt. Jetzt: REFRESH MATERIALIZED VIEW indicator_coverage;'
\else
  ROLLBACK;
  \echo '>>> PROBELAUF: alles zurückgerollt, nichts geändert. Ausführen mit -v ausfuehren=1'
\endif
