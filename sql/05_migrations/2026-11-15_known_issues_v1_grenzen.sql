-- =============================================================================
-- known_issues: Historische Einheiten für DB v1.0 als dokumentierte Grenze akzeptieren (15.11.2026)
-- Entscheidung Julian 15.11.2026: Readiness R5.1 verlangt 0 offene to_fix. Die beiden offenen Einträge betreffen
-- dasselbe Thema (Vorgängerstaaten/Einheiten ohne Ländercode). Für v1.0 sind sie dokumentierte Grenzen, die
-- Nacharbeit steht als Aufgabe im Backlog #105 (historische Einheiten mit ISO-Zahlencode und Gültigkeitszeitraum).
--   1. 'V-Dem: 8 Einheiten ohne Ländercode verworfen …'          (14.11.2026)
--   2. 'POLITY5: Vorgängerstaaten und historische Einheiten …'    (15.11.2026, Migration 3)
-- Beide: decision to_fix → accepted, Beschreibung um einen Satz ergänzt. Sonst ändert sich nichts.
--
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_known_issues_v1_grenzen.sql > logs/migrations/2026-11-15_known_issues_v1_grenzen.txt 2>&1
--
-- Erwartet vorher:  to_fix gesamt 2, genau diese beiden Titel. Nachher: to_fix 0, accepted +2.
-- =============================================================================

BEGIN;

CREATE TEMP TABLE ziel ON COMMIT DROP AS
SELECT id, title FROM known_issues
WHERE decision = 'to_fix'
  AND (title LIKE 'V-Dem: 8 Einheiten ohne Ländercode%' OR title LIKE 'POLITY5: Vorgängerstaaten%');

DO $$
DECLARE n_tofix bigint; n_ziel bigint; n_acc bigint;
BEGIN
    SELECT count(*) INTO n_tofix FROM known_issues WHERE decision = 'to_fix';
    SELECT count(*) INTO n_ziel FROM ziel;
    SELECT count(*) INTO n_acc FROM known_issues WHERE decision = 'accepted';
    IF n_tofix <> 2 OR n_ziel <> 2 THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: to_fix gesamt=% (2), davon Zielzeilen=% (2)', n_tofix, n_ziel;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK: to_fix 2 (beide Zielzeilen), accepted %', n_acc;
END $$;

\echo '== Vorher'
SELECT k.id, k.title, k.decision FROM known_issues k JOIN ziel USING (id) ORDER BY k.id;

UPDATE known_issues k
SET decision = 'accepted',
    description = k.description || ' Für DB v1.0 als dokumentierte Grenze akzeptiert (Julian 15.11.2026); '
                  || 'Nacharbeit: Backlog #105 (historische Einheiten mit eigenem ISO-Zahlencode).'
FROM ziel z WHERE k.id = z.id;

DO $$
DECLARE n_tofix bigint; n_ziel_acc bigint;
BEGIN
    SELECT count(*) INTO n_tofix FROM known_issues WHERE decision = 'to_fix';
    SELECT count(*) INTO n_ziel_acc FROM known_issues k JOIN ziel USING (id)
     WHERE k.decision = 'accepted' AND k.description LIKE '%Backlog #105 (historische Einheiten%';
    IF n_tofix <> 0 OR n_ziel_acc <> 2 THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: to_fix=% (0) Zielzeilen accepted=% (2)', n_tofix, n_ziel_acc;
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: to_fix 0';
END $$;

\echo '== Nachher'
SELECT k.id, k.title, k.decision FROM known_issues k JOIN ziel USING (id) ORDER BY k.id;

COMMIT;
