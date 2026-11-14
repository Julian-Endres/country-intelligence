-- Entscheidungen Julian 14.11.2026 (Backlog #87, #6). Ändert KEINE Werte in indicators.
--   1. Regel für time_period als Spaltenkommentar (der Sekretär liest Kommentare als Regeln).
--   2. Drei known_issues zu V-Dem (Agenten melden sie danach nicht erneut).
--   3. VDEM:v2x_corr bekommt direction = higher_is_worse (Codebook v16, Z. 17404).
-- Doppelt ausführen ist harmlos (NOT EXISTS / WHERE-Bedingung).
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-14_static_regel_vdem_befunde.sql

\echo '== vorher: Kommentar time_period'
SELECT col_description('indicators'::regclass, a.attnum)
FROM pg_attribute a WHERE a.attrelid = 'indicators'::regclass AND a.attname = 'time_period';

\echo '== vorher: known_issues gesamt / VDEM'
SELECT count(*) AS gesamt,
       count(*) FILTER (WHERE source_id = (SELECT id FROM sources WHERE short_code = 'VDEM')) AS vdem
FROM known_issues;

\echo '== vorher: direction der VDEM-Korruptionsindizes (erwartet: v2x_corr leer)'
SELECT indicator_code, direction FROM indicator_metadata
WHERE indicator_code IN ('VDEM:v2x_corr', 'VDEM:v2x_execorr', 'VDEM:v2x_pubcorr') ORDER BY 1;

BEGIN;

COMMENT ON COLUMN indicators.time_period IS
    'Jahr als Text (JJJJ). Sonderwert static NUR für Eigenschaften ohne Zeitbezug (z. B. Binnenland, Küstenlänge, '
    'Unabhängigkeitsjahr). Werte, die den Stand einer bestimmten Ausgabe zeigen (Index-Ausgabe, Datensatz-Version, '
    'Studie), bekommen das Jahr dieser Ausgabe, nicht static. Entscheidung Julian 14.11.2026 (#87)';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id, 'V-Dem: Deutschland 1945–1948 ohne Werte, 1949–1990 = BRD',
       'In der Originaldatei V-Dem-CY-Full+Others-v16.csv hat DEU keine Zeilen für 1945–1948 (1944: 0,072, 1949: 0,793 bei '
       'v2x_polyarchy). Kein Ladefehler. V-Dem führt Deutschland als durchgehende Einheit; 1949–1990 sind die Werte unter 276 '
       'die der Bundesrepublik, die DDR ist eine eigene Einheit (siehe Eintrag DDR/Kosovo). Geprüft 14.11.2026.',
       'accepted'
FROM sources s WHERE s.short_code = 'VDEM'
  AND NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.title LIKE 'V-Dem: Deutschland 1945%');

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id, 'V-Dem: nur Punktschätzer geladen (keine _codelow/_codehigh/_sd/_osp/_ord)',
       'load_vdem.py schließt die Varianten _codelow, _codehigh, _sd, _osp, _ord, _mean, _nr bewusst aus. Konfidenzintervalle '
       'und 0–1-Varianten (_osp) fehlen deshalb in der DB. Die Accountability-Indizes (v2x_accountability, _veracc, _diagacc, '
       '_horacc) liegen in der unbegrenzten Version vor. Wer Unsicherheit braucht: Original-CSV in data/raw. Entscheidung Julian 14.11.2026.',
       'accepted'
FROM sources s WHERE s.short_code = 'VDEM'
  AND NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.title LIKE 'V-Dem: nur Punktschätzer%');

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id, 'V-Dem: 8 Einheiten ohne Ländercode verworfen (DDR, Kosovo, Gaza, Somaliland, Südjemen, Sansibar …)',
       'load_vdem.py lädt nur Einheiten, deren country_text_id in countries vorkommt. Ab 1900 hat die Quelle 183 Einheiten, die DB 175. '
       'Es fehlen u. a. DDR (1949–1990), Kosovo (XKX), Palestine/Gaza (PSG; 275 enthält nur Palestine/West Bank), Somaliland, '
       'South Yemen, Zanzibar. Lösung gehört zum Ländercode-Standard (Backlog #105).',
       'to_fix'
FROM sources s WHERE s.short_code = 'VDEM'
  AND NOT EXISTS (SELECT 1 FROM known_issues k WHERE k.title LIKE 'V-Dem: 8 Einheiten%');

UPDATE indicator_metadata SET direction = 'higher_is_worse'
WHERE indicator_code = 'VDEM:v2x_corr' AND direction IS DISTINCT FROM 'higher_is_worse';

COMMIT;

\echo '== nachher: Kommentar time_period'
SELECT col_description('indicators'::regclass, a.attnum)
FROM pg_attribute a WHERE a.attrelid = 'indicators'::regclass AND a.attname = 'time_period';

\echo '== nachher: known_issues gesamt / VDEM (erwartet: +3)'
SELECT count(*) AS gesamt,
       count(*) FILTER (WHERE source_id = (SELECT id FROM sources WHERE short_code = 'VDEM')) AS vdem
FROM known_issues;
SELECT id, title, decision FROM known_issues ORDER BY id DESC LIMIT 3;

\echo '== nachher: direction'
SELECT indicator_code, direction FROM indicator_metadata
WHERE indicator_code IN ('VDEM:v2x_corr', 'VDEM:v2x_execorr', 'VDEM:v2x_pubcorr') ORDER BY 1;
