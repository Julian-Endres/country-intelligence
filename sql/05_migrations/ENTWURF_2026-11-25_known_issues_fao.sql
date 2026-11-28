-- =====================================================================
-- ENTWURF (Claude, Nacht 24./25.11.2026) – CI-182: FAO-Lücken als known_issue
-- NICHT ausgeführt. Aufruf (Shell, Repo-Wurzel):
--   psql -U postgres -d country_intelligence -v ON_ERROR_STOP=1 \
--        -f sql/05_migrations/ENTWURF_2026-11-25_known_issues_fao.sql > logs/migrations/2026-11-25_ki_fao.txt 2>&1
--
-- Befund: Keine Zuordnungsfrage. Die Rohdatei data/raw/health/fao_food.zip (FAOSTAT Food Balances,
-- Bulk-Download, Dateien vom 14.10.2025, 2010–2023) enthält diese Länder gar nicht – weder in den Daten
-- noch in FoodBalanceSheets_E_AreaCodes.csv: Benin, Burundi, Dominica, Japan, Mali, Singapur, Somalia,
-- Südsudan, Sudan, Togo, Tschad, Zentralafrikanische Republik (M49 204 108 212 392 466 702 706 728 729 768 148 140).
-- Our World in Data vermerkt zur FAOSTAT-Ausgabe vom 28.10.2025, dass Daten für 11 dieser Länder
-- (alle außer Singapur) wegen einer laufenden Überprüfung fehlen.
-- =====================================================================

BEGIN;

DO $$
BEGIN
    IF (SELECT count(*) FROM known_issues WHERE title LIKE 'FAO Food Balances: 12 Länder%') <> 0 THEN
        RAISE EXCEPTION 'known_issue existiert schon';
    END IF;
    IF (SELECT count(*) FROM sources WHERE short_code IN ('FAO_FOOD', 'FAO_FOOD_GRP')) <> 2 THEN
        RAISE EXCEPTION 'Quellen FAO_FOOD / FAO_FOOD_GRP nicht gefunden';
    END IF;
    -- Kontrolle: keine Werte für diese Länder in beiden Quellen (sonst stimmt der Befund nicht)
    IF (SELECT count(*) FROM indicators i JOIN sources s ON s.id = i.source_id
        WHERE s.short_code IN ('FAO_FOOD', 'FAO_FOOD_GRP')
          AND i.iso_numeric IN ('204','108','212','392','466','702','706','728','729','768','148','140')) <> 0 THEN
        RAISE EXCEPTION 'Es gibt doch Werte für eines der 12 Länder – Befund prüfen';
    END IF;
END $$;

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', s.id,
       'FAO Food Balances: 12 Länder fehlen in der Quelle (u. a. Japan, Sudan)',
       'Die FAOSTAT Food Balances (Bulk-Download, Dateien vom 14.10.2025, Jahre 2010–2023) enthalten Benin, Burundi, Dominica, Japan, Mali, Singapur, Somalia, Südsudan, Sudan, Togo, Tschad und die Zentralafrikanische Republik nicht (auch nicht in der Gebietsliste der Datei). Kein Ladefehler: der Loader übernimmt M49 direkt. Laut Our World in Data fehlen 11 davon in der Ausgabe vom 28.10.2025 wegen einer laufenden Überprüfung durch die FAO. Beim nächsten FAOSTAT-Release erneut prüfen (CI-182).',
       'accepted'
FROM sources s WHERE s.short_code IN ('FAO_FOOD', 'FAO_FOOD_GRP');

DO $$
BEGIN
    IF (SELECT count(*) FROM known_issues WHERE title LIKE 'FAO Food Balances: 12 Länder%') <> 2 THEN
        RAISE EXCEPTION 'Kontrolle nachher: erwartet 2 Einträge (je Quelle einer)';
    END IF;
    RAISE NOTICE 'Kontrolle nachher ok';
END $$;

COMMIT;
