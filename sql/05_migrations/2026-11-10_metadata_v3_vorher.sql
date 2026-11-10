-- Vor der Migration v3 ausführen (nur lesen). Erwartete Werte in den Kommentaren.

-- 1. Stand der Tabelle: gesamt 725 | ohne_beschreibung (Zahl notieren) | scale_type_gesetzt 0 | data_origin_gesetzt 0
SELECT COUNT(*) AS gesamt,
       COUNT(*) FILTER (WHERE description IS NULL OR TRIM(description) = '') AS ohne_beschreibung,
       COUNT(scale_type) AS scale_type_gesetzt,
       COUNT(data_origin) AS data_origin_gesetzt
FROM indicator_metadata;

-- 2. Werte, die v3 aus den Listen streicht: muss 0 sein, sonst bricht die Migration ab
SELECT COUNT(*) AS gestrichene_werte_in_benutzung
FROM indicator_metadata
WHERE scale_type = 'latent' OR data_origin = 'composite_index';

-- 3. Die neuen Spalten gibt es noch nicht: 0 Zeilen
SELECT column_name FROM information_schema.columns
WHERE table_name = 'indicator_metadata'
  AND column_name IN ('key_info', 'producer_definition', 'value_labels');
