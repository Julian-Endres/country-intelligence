-- =============================================================================
-- indicators.source_id NOT NULL (15.11.2026, Abschluss Backlog #1)
--
-- Warum: UNIQUE(iso_numeric, indicator_code, source_id, time_period) greift nicht, wenn source_id NULL ist
-- (NULL ist nie gleich NULL). Jeder Loader ohne source_id hat deshalb mit ON CONFLICT DO NOTHING bei jedem
-- Lauf alle Werte erneut eingefügt (GHI 7-mal am 28.05., 684.365 Werte ohne Quelle). Seit Migration 3 hat
-- jeder Wert eine source_id. Die Sperre verhindert, dass es wieder passiert: Ein Loader ohne source_id
-- bricht jetzt mit Fehler ab, statt still zu verdoppeln.
--
-- FOLGE (gewollt, laut statt still): Diese Loader schreiben noch ohne source_id und brechen beim nächsten Lauf ab,
-- bis sie beim Anfassen nach docs/PIPELINE_STANDARD.md umgestellt sind (Backlog-Eintrag 15.11.):
--   scripts/pipeline/culture/load_pew_religion.py, demographics/load_unhcr.py, economy/load_pwt.py,
--   economy/load_wid.py, social/load_caf_wgi.py; dazu governance/load_fsi_gitoc_owid.py für SIPRI
--   (übergibt source_id, die für SIPRI NULL war).
--
-- Aufruf (Shell, Repo-Wurzel). Sperrt indicators kurz (prüft 4,1 Mio. Zeilen einmal):
--   psql -d country_intelligence -X -q -P pager=off -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/2026-11-15_indicators_source_id_not_null.sql > logs/migrations/2026-11-15_source_id_not_null.txt 2>&1
--
-- Erwartet vorher: 0 Werte ohne source_id, Spalte noch nullable. Nachher: Spalte NOT NULL, Zeilen unverändert.
-- =============================================================================

BEGIN;

CREATE TEMP TABLE kontrolle ON COMMIT DROP AS SELECT count(*) AS zeilen FROM indicators;

DO $$
DECLARE n_null bigint; nn boolean;
BEGIN
    SELECT count(*) INTO n_null FROM indicators WHERE source_id IS NULL;
    SELECT attnotnull INTO nn FROM pg_attribute
     WHERE attrelid = 'indicators'::regclass AND attname = 'source_id';
    IF n_null <> 0 OR nn THEN
        RAISE EXCEPTION 'Vorher-Kontrolle falsch: Werte ohne source_id=% (0), schon NOT NULL=% (false)', n_null, nn;
    END IF;
    RAISE NOTICE 'Vorher-Kontrolle OK: % Zeilen, 0 ohne source_id', (SELECT zeilen FROM kontrolle);
END $$;

ALTER TABLE indicators ALTER COLUMN source_id SET NOT NULL;

COMMENT ON COLUMN indicators.source_id IS
    'Pflicht (NOT NULL seit 15.11.2026, Backlog #1). Ohne source_id greift UNIQUE nicht und jeder Ladelauf '
    'verdoppelt die Werte. Loader holen die ID aus sources.short_code und brechen ab, wenn sie fehlt (PIPELINE_STANDARD P15).';

DO $$
DECLARE nn boolean; n bigint;
BEGIN
    SELECT attnotnull INTO nn FROM pg_attribute
     WHERE attrelid = 'indicators'::regclass AND attname = 'source_id';
    SELECT count(*) INTO n FROM indicators;
    IF NOT nn OR n <> (SELECT zeilen FROM kontrolle) THEN
        RAISE EXCEPTION 'Nachher-Kontrolle falsch: NOT NULL=% (true) Zeilen=% (%)', nn, n, (SELECT zeilen FROM kontrolle);
    END IF;
    RAISE NOTICE 'Nachher-Kontrolle OK: source_id NOT NULL, % Zeilen unverändert', n;
END $$;

COMMIT;
