-- Nach der Migration ausführen. Erwartete Werte in den Kommentaren.

-- Bestehende Daten unverändert:  gesamt 725 | ohne_beschreibung 321 | aktiv 725 | richtung_gesetzt 0
SELECT COUNT(*) AS gesamt,
       COUNT(*) FILTER (WHERE description IS NULL OR TRIM(description) = '') AS ohne_beschreibung,
       COUNT(*) FILTER (WHERE status = 'active') AS aktiv,
       COUNT(direction) AS richtung_gesetzt
FROM indicator_metadata;

-- Quellen unverändert: 52
SELECT COUNT(*) AS quellen FROM sources;

-- Bekannte Fälle: 2 (V-Dem ab 1900, Gini)
SELECT id, scope, title, decision FROM known_issues ORDER BY id;

-- Abdeckungs-Übersicht: eine Zeile pro Indikator mit Werten (höchstens 725)
SELECT COUNT(*) AS indikatoren_mit_werten, SUM(n_values) AS werte_gesamt FROM indicator_coverage;
