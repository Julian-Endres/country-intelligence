-- =====================================================================
-- Migration 2026-11-10: Metadaten v3 (Ergebnis des Format-Piloten)
-- =====================================================================
-- Neu:      key_info, producer_definition, value_labels
-- Geändert: Wertelisten scale_type (+ measure, - latent) und data_origin (- composite_index)
-- Regeln:   als Spaltenkommentare (gelten für Sekretär, Auto-Prüfung und Handarbeit)
-- Bestehende Werte werden NICHT verändert. Alte Einheiten wie 'index 0-1' werden erst
-- beim Neuschreiben durch den Sekretär bereinigt.
--
-- Ausführen aus der Repo-Wurzel (als Ganzes oder gar nicht):
--   psql -d country_intelligence -v ON_ERROR_STOP=1 --single-transaction -f sql/05_migrations/2026-11-10_metadata_v3.sql
--
-- Nach v3 ist das Schema eingefroren, bis 5 Quellen komplett beschrieben sind.
-- Neue Ideen kommen in den Backlog, nicht in eine Migration.
-- =====================================================================


-- Sicherung: gestrichene Listenwerte dürfen nicht in Benutzung sein
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM indicator_metadata
               WHERE scale_type = 'latent' OR data_origin = 'composite_index') THEN
        RAISE EXCEPTION 'Abbruch: latent oder composite_index wird noch verwendet';
    END IF;
END $$;


-- Neue Spalten
ALTER TABLE indicator_metadata
    ADD COLUMN key_info            text[],
    ADD COLUMN producer_definition text,
    ADD COLUMN value_labels        text;

ALTER TABLE indicator_metadata
    ADD CONSTRAINT chk_im_key_info_len CHECK (key_info IS NULL OR cardinality(key_info) BETWEEN 1 AND 5);


-- Wertelisten anpassen
ALTER TABLE indicator_metadata DROP CONSTRAINT chk_im_scale_type;
ALTER TABLE indicator_metadata ADD CONSTRAINT chk_im_scale_type CHECK (scale_type IN
    ('index', 'ordinal', 'binary', 'categorical', 'percent', 'count', 'currency',
     'rate', 'ratio', 'measure', 'other'));

ALTER TABLE indicator_metadata DROP CONSTRAINT chk_im_data_origin;
ALTER TABLE indicator_metadata ADD CONSTRAINT chk_im_data_origin CHECK (data_origin IN
    ('expert_survey', 'official_statistics', 'population_survey', 'model_estimate',
     'event_count', 'administrative_record', 'other'));


-- Regeln als Spaltenkommentare
COMMENT ON COLUMN indicator_metadata.name IS
    'Offizieller Name laut Quelle (Englisch, nicht übersetzt), damit man ihn in der Dokumentation wiederfindet';
COMMENT ON COLUMN indicator_metadata.description IS
    'Genau EIN Satz in einfachen Wörtern (Englisch, höchstens 200 Zeichen): was der Indikator ist. '
    'So formuliert, dass ein hoher Wert "mehr davon" bedeutet. Keine Skalenzahlen, kein Quellenname, '
    'keine Fachbegriffe ohne Erklärung';
COMMENT ON COLUMN indicator_metadata.key_info IS
    '1 bis 5 Kernpunkte "what you should know" (Englisch): wie entsteht der Wert, wie liest man ihn, Grenzen. '
    'Jeder Punkt ist aus der Quelle belegt; eigene Hinweise beginnen mit "Note:"';
COMMENT ON COLUMN indicator_metadata.producer_definition IS
    'Wörtliche Definition des Herausgebers. Leer, wenn die Quelle keine hat';
COMMENT ON COLUMN indicator_metadata.value_labels IS
    'Bedeutung der Stufen, nur bei ordinal, categorical, binary. Format: "0 = ...; 1 = ...; 2 = ..."';
COMMENT ON COLUMN indicator_metadata.unit IS
    'Echte Maßeinheit (z. B. "current US dollars", "deaths per 1,000 live births", "years"), OHNE Wertebereich. '
    'Nur bei measure, currency, count, rate, ratio, percent; bei index, ordinal, binary, categorical leer';
COMMENT ON COLUMN indicator_metadata.scale_type IS
    'Art des Werts: index, ordinal, binary, categorical, percent, count, currency, rate, ratio, '
    'measure (Messgröße wie Jahre, Tonnen, km²), other';
COMMENT ON COLUMN indicator_metadata.scale_min IS
    'Theoretisches Minimum. Nur wenn die Quelle es nennt oder es mathematisch feststeht (z. B. Prozent 0), sonst leer';
COMMENT ON COLUMN indicator_metadata.scale_max IS
    'Theoretisches Maximum. Nur wenn die Quelle es nennt oder es mathematisch feststeht (z. B. Prozent 100), sonst leer';
COMMENT ON COLUMN indicator_metadata.data_origin IS
    'Hauptherkunft der Rohdaten (nicht die Bauweise): expert_survey, official_statistics, population_survey, '
    'model_estimate, event_count, administrative_record, other. Leer, wenn nicht belegbar';
COMMENT ON COLUMN indicator_metadata.reference IS
    'Fundstelle als Abschnitt bzw. Variableneintrag, nicht als Seite, z. B. "V-Dem Codebook v16, section 2.1.2"';
