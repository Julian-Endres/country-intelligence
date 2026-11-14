-- indicator_catalog als reines Suchverzeichnis kennzeichnen (Entscheidung 14.11.2026).
-- Grund: Für geladene Indikatoren gilt indicator_metadata (geprüft, mit Belegen); der Katalog
-- ist eine Momentaufnahme vom Mai 2026 (WB 11.05., WHO 21.–25.05.) und weicht bei 23 Namen ab.
-- Ändert nur den Tabellenkommentar, keine Daten. Vorher/nachher wird angezeigt.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-14_kommentar_indicator_catalog.sql

\echo '== vorher'
SELECT obj_description('indicator_catalog'::regclass, 'pg_class') AS kommentar,
       (SELECT COUNT(*) FROM indicator_catalog) AS zeilen;

BEGIN;

COMMENT ON TABLE indicator_catalog IS
    'Suchverzeichnis NICHT geladener Indikatoren (WB 1486, WHO 3058), Stand Mai 2026 (last_checked). '
    'Nur zum Finden neuer Kandidaten (Name, Abdeckung bei der Quelle). WHO ohne Beschreibungen. '
    'Für geladene Indikatoren gilt ausschließlich indicator_metadata, Abdeckung in der DB: indicator_coverage. '
    'Nicht für Namen, Einheiten oder Beschreibungen verwenden';

COMMIT;

\echo '== nachher'
SELECT obj_description('indicator_catalog'::regclass, 'pg_class') AS kommentar,
       (SELECT COUNT(*) FROM indicator_catalog) AS zeilen;
