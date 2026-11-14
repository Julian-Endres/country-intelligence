-- Spaltenkommentare an die Regeln vom 12.11. (description, #129) und 14.11. (data_origin, #124) angleichen.
-- Der Sekretär liest diese Kommentare als Regeln; die alte description-Regel widersprach dem Prompt.
-- Ändert nur Kommentare, keine Daten. Vorher/nachher wird angezeigt.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-14_kommentare_description_data_origin.sql

\echo '== vorher'
SELECT a.attname, col_description('indicator_metadata'::regclass, a.attnum)
FROM pg_attribute a WHERE a.attrelid = 'indicator_metadata'::regclass AND a.attname IN ('description', 'data_origin');

BEGIN;

COMMENT ON COLUMN indicator_metadata.description IS
    'Genau EIN Satz (Englisch, höchstens 200 Zeichen): sachlich, was gemessen wird. Gängige Fachwörter erwünscht '
    '(prevalence, mortality rate, share, per capita), statistischer Jargon und wertende Alltagssprache nicht. '
    'Schwellen, Referenzstandards und Methode gehören in key_info. So formuliert, dass ein hoher Wert "mehr davon" '
    'bedeutet. Keine Skalenzahlen, kein Quellenname';

COMMENT ON COLUMN indicator_metadata.data_origin IS
    'expert_survey, official_statistics, population_survey, model_estimate, event_count, administrative_record, other. '
    'Prüffrage: Beruht der Wert auf einer eigenen Beobachtung genau dieses Land-Jahres? Ja: Art der Beobachtung '
    '(auch wenn danach zu einem Index verrechnet). Nein (interpoliert, fortgeschrieben, modelliert): model_estimate. '
    'Nur wenn eindeutig, sonst leer';

COMMIT;

\echo '== nachher'
SELECT a.attname, col_description('indicator_metadata'::regclass, a.attnum)
FROM pg_attribute a WHERE a.attrelid = 'indicator_metadata'::regclass AND a.attname IN ('description', 'data_origin');
