-- Trägt 7 Quellen in sources ein, die bisher nur als relationale Tabellen existieren
-- (Abgleich 10.11.2026, docs/SOURCES_AVAILABLE.md). Backlog: #20, #74, #81.
-- Erst ausführen, wenn sql/03_queries/2026-11-10_sources_fehlende_pruefen.sql ohne Treffer bei P1 war.
--
-- Aufruf (eine Transaktion, bricht beim ersten Fehler ab):
--   psql -d country_intelligence --single-transaction -v ON_ERROR_STOP=1 -f sql/05_migrations/2026-11-10_sources_fehlende.sql
--
-- Nur belegte Angaben: Name, Herausgeber, URL und Version stammen aus den Kopfzeilen der Loader
-- bzw. aus load_comtrade_v2.py. Unbekanntes bleibt NULL (Quellen-Pfleger #24 füllt später).

\pset pager off

-- Abbruch, falls eine der Quellen doch schon existiert
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM sources WHERE short_code IN ('COMTRADE','MARPOR','CCP','CLINE','COLDAT','DASID','DDR')) THEN
    RAISE EXCEPTION 'Mindestens eine Quelle existiert schon – nichts eingetragen.';
  END IF;
END $$;

-- Sequenz auf den höchsten vergebenen id-Wert setzen (sonst Kollision möglich, falls ids von Hand vergeben wurden)
SELECT setval(pg_get_serial_sequence('sources', 'id'), (SELECT max(id) FROM sources));

\echo '=== Vorher ==='
SELECT count(*) AS quellen_vorher FROM sources;

INSERT INTO sources (short_code, name, url, description, publisher, documentation_url, loaded_version, access_method, update_frequency)
VALUES
 ('COMTRADE', 'UN Comtrade', 'https://comtradeapi.un.org',
  'Internationaler Warenhandel nach Melderland: Produktstruktur (HS4, Partner Welt) und Partnerstruktur (TOTAL). Tabellen trade.trade_products, trade.trade_partners.',
  'United Nations Statistics Division', NULL, NULL, 'api', NULL),
 ('MARPOR', 'Manifesto Project (MARPOR)', 'https://manifesto-project.wzb.eu/',
  'Wahlergebnisse und Kodierung der Parteiprogramme je Wahl sowie Partei-Stammdaten. Tabellen politics.marpor_elections, politics.political_parties.',
  'WZB Berlin Social Science Center', NULL, '2025a', 'download', NULL),
 ('CCP', 'Comparative Constitutions Project', NULL,
  'Verfassungsereignisse (neu, Änderung, Suspendierung, Wiedereinsetzung) seit 1789. Tabelle politics.constitutional_events.',
  'Elkins, Ginsburg, Melton', NULL, 'v6', 'download', NULL),
 ('CLINE', 'Cline Center Coup d''État Project', NULL,
  'Putsche, Putschversuche und erzwungene Rücktritte 1945–2026. Tabelle politics.coups. Loader fehlt im Repo (#69).',
  'Cline Center for Advanced Social Research', NULL, NULL, NULL, NULL),
 ('COLDAT', 'COLDAT Colonial Dates Dataset', 'https://doi.org/10.7910/DVN/T9SDEW',
  'Beginn und Ende von Kolonialherrschaft, Kolonialmacht. Tabelle international.colonial_history.',
  'Bastian Becker, Universität Bremen', NULL, NULL, 'download', NULL),
 ('DASID', 'DASID Dyadic Annual State Interactions Dataset', NULL,
  'Jährliche Beziehungen zwischen Staatenpaaren. Tabelle international.diplomatic_relations.',
  'Moyer, Turner, Meisel – University of Denver, Pardee Center', NULL, NULL, 'download', NULL),
 ('DDR', 'Diplometrics Diplomatic Representation', NULL,
  'Diplomatische Vertretungen zwischen Staaten 1960–2024. Tabelle international.diplomatic_representation.',
  'Moyer, Turner, Meisel – University of Denver, Pardee Center / Korbel School', NULL, '1960–2024 (Datei vom 25.08.2025)', 'download', NULL);

\echo '=== Nachher (erwartet: 59 Quellen, 7 neue Zeilen) ==='
SELECT count(*) AS quellen_nachher FROM sources;
SELECT id, short_code, name, publisher, loaded_version, access_method
FROM sources WHERE short_code IN ('COMTRADE','MARPOR','CCP','CLINE','COLDAT','DASID','DDR') ORDER BY id;
