-- Nach der Migration v3 ausführen (nur lesen). Erwartete Werte in den Kommentaren.

-- 1. Bestehende Daten unverändert: gleiche Zahlen wie in _vorher.sql, Abfrage 1
SELECT COUNT(*) AS gesamt,
       COUNT(*) FILTER (WHERE description IS NULL OR TRIM(description) = '') AS ohne_beschreibung,
       COUNT(scale_type) AS scale_type_gesetzt,
       COUNT(data_origin) AS data_origin_gesetzt
FROM indicator_metadata;

-- 2. Neue Spalten da und leer: 3 Zeilen; key_info 0 | producer_definition 0 | value_labels 0
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'indicator_metadata'
  AND column_name IN ('key_info', 'producer_definition', 'value_labels')
ORDER BY column_name;

SELECT COUNT(key_info) AS key_info, COUNT(producer_definition) AS producer_definition,
       COUNT(value_labels) AS value_labels
FROM indicator_metadata;

-- 3. Neue Wertelisten aktiv: 3 Zeilen, scale_type mit 'measure' ohne 'latent', data_origin ohne 'composite_index'
SELECT conname, pg_get_constraintdef(oid) AS regel
FROM pg_constraint
WHERE conrelid = 'indicator_metadata'::regclass
  AND conname IN ('chk_im_scale_type', 'chk_im_data_origin', 'chk_im_key_info_len')
ORDER BY conname;

-- 4. Agent darf die neuen Spalten lesen: true
SELECT has_column_privilege('ci_agent_readonly', 'indicator_metadata', 'key_info', 'SELECT') AS agent_liest;
