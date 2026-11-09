-- =====================================================================
-- Migration 2026-11-09: Metadaten v2
-- =====================================================================
-- Fügt NUR hinzu: Spalten, eine Tabelle (known_issues) und eine
-- Übersicht (indicator_coverage). Bestehende Werte werden nicht verändert.
--
-- Ausführen aus der Repo-Wurzel (als Ganzes oder gar nicht):
--   psql -d country_intelligence -v ON_ERROR_STOP=1 --single-transaction -f sql/05_migrations/2026-11-09_metadata_v2.sql
--
-- Neue Spalten mit festen Wertelisten haben CHECK-Bedingungen, damit
-- weder Agent noch Tippfehler ungültige Werte eintragen können.
-- =====================================================================


-- ---------------------------------------------------------------------
-- A-D) indicator_metadata
-- ---------------------------------------------------------------------
ALTER TABLE indicator_metadata
    -- Verstehen und richtig benutzen
    ADD COLUMN direction          varchar(20),
    ADD COLUMN scale_type         varchar(20),
    ADD COLUMN scale_min          double precision,
    ADD COLUMN scale_max          double precision,
    ADD COLUMN data_origin        varchar(30),
    ADD COLUMN temporal_type      varchar(20),
    ADD COLUMN is_lead_indicator  boolean NOT NULL DEFAULT false,
    ADD COLUMN keywords           text[],
    -- Herkunft
    ADD COLUMN reference          text,
    ADD COLUMN loader_script      varchar(200),
    -- Pflege und Organisation
    ADD COLUMN status             varchar(20) NOT NULL DEFAULT 'active',
    ADD COLUMN metadata_reviewed_at timestamptz,
    ADD COLUMN added_at           timestamptz;   -- bestehende Zeilen bleiben leer (= vor dem 09.11.2026)

ALTER TABLE indicator_metadata ALTER COLUMN added_at SET DEFAULT now();

ALTER TABLE indicator_metadata
    ADD CONSTRAINT chk_im_direction CHECK (direction IN
        ('higher_is_better', 'higher_is_worse', 'neutral', 'not_applicable')),
    ADD CONSTRAINT chk_im_scale_type CHECK (scale_type IN
        ('index', 'ordinal', 'binary', 'latent', 'percent', 'count', 'currency',
         'rate', 'ratio', 'categorical', 'other')),
    ADD CONSTRAINT chk_im_scale_range CHECK (scale_min IS NULL OR scale_max IS NULL OR scale_min < scale_max),
    ADD CONSTRAINT chk_im_data_origin CHECK (data_origin IN
        ('expert_survey', 'official_statistics', 'population_survey', 'model_estimate',
         'event_count', 'composite_index', 'administrative_record', 'other')),
    ADD CONSTRAINT chk_im_temporal_type CHECK (temporal_type IN
        ('annual', 'survey_wave', 'snapshot', 'irregular', 'other')),
    ADD CONSTRAINT chk_im_status CHECK (status IN ('active', 'deprecated', 'experimental'));

COMMENT ON COLUMN indicator_metadata.direction IS 'Ist ein hoher Wert gut oder schlecht? higher_is_better / higher_is_worse / neutral / not_applicable';
COMMENT ON COLUMN indicator_metadata.scale_type IS 'Art der Skala: index, ordinal, binary, latent, percent, count, currency, rate, ratio, categorical, other';
COMMENT ON COLUMN indicator_metadata.scale_min IS 'Theoretisches Minimum laut Quelle (leer bei unbegrenzten Skalen)';
COMMENT ON COLUMN indicator_metadata.scale_max IS 'Theoretisches Maximum laut Quelle (leer bei unbegrenzten Skalen)';
COMMENT ON COLUMN indicator_metadata.data_origin IS 'Wie entsteht die Zahl: expert_survey, official_statistics, population_survey, model_estimate, event_count, composite_index, administrative_record, other';
COMMENT ON COLUMN indicator_metadata.temporal_type IS 'Zeitstruktur: annual, survey_wave, snapshot, irregular, other';
COMMENT ON COLUMN indicator_metadata.is_lead_indicator IS 'Leitindikator der Quelle bzw. Dimension (Encyclopedia-Konzept)';
COMMENT ON COLUMN indicator_metadata.keywords IS 'Suchbegriffe Deutsch und Englisch';
COMMENT ON COLUMN indicator_metadata.reference IS 'Fundstelle in der Quellendokumentation, z. B. "V-Dem Codebook v16, S. 47"';
COMMENT ON COLUMN indicator_metadata.loader_script IS 'Skript, das den Indikator lädt (Pfad im Repo)';
COMMENT ON COLUMN indicator_metadata.status IS 'active / deprecated (ersetzt, nicht mehr nutzen) / experimental';
COMMENT ON COLUMN indicator_metadata.metadata_reviewed_at IS 'Zeitpunkt der Freigabe der Metadaten durch Julian (setzt apply.py)';
COMMENT ON COLUMN indicator_metadata.added_at IS 'Wann der Indikator angelegt wurde (leer = vor 09.11.2026)';


-- ---------------------------------------------------------------------
-- B-D) sources  (= Quellenregister)
-- ---------------------------------------------------------------------
ALTER TABLE sources
    ADD COLUMN summary           text,
    ADD COLUMN publisher         varchar(200),
    ADD COLUMN license           text,
    ADD COLUMN citation          text,
    ADD COLUMN documentation_url varchar(500),
    ADD COLUMN loaded_version    varchar(50),
    ADD COLUMN loaded_at         date,
    ADD COLUMN update_frequency  varchar(20),
    ADD COLUMN access_method     varchar(20),
    ADD COLUMN update_check      text,
    ADD COLUMN notion_url        varchar(500);

ALTER TABLE sources
    ADD CONSTRAINT chk_src_update_frequency CHECK (update_frequency IN
        ('annual', 'biannual', 'quarterly', 'monthly', 'continuous', 'irregular', 'one_off', 'unknown')),
    ADD CONSTRAINT chk_src_access_method CHECK (access_method IN
        ('api', 'download', 'scraping', 'manual', 'other'));

COMMENT ON COLUMN sources.summary IS 'Kurztext (1-2 Sätze) aus dem Abschnitt "Auf einen Blick" des Quellen-Leitfadens';
COMMENT ON COLUMN sources.publisher IS 'Herausgebende Institution';
COMMENT ON COLUMN sources.license IS 'Lizenz / Weitergabe-Bedingungen';
COMMENT ON COLUMN sources.citation IS 'Vorgeschriebene bzw. empfohlene Zitierweise';
COMMENT ON COLUMN sources.documentation_url IS 'Codebook / Methodik';
COMMENT ON COLUMN sources.loaded_version IS 'In der DB geladene Version, z. B. v16';
COMMENT ON COLUMN sources.loaded_at IS 'Datum des letzten Ladens';
COMMENT ON COLUMN sources.update_frequency IS 'annual, biannual, quarterly, monthly, continuous, irregular, one_off, unknown';
COMMENT ON COLUMN sources.access_method IS 'api, download, scraping, manual, other';
COMMENT ON COLUMN sources.update_check IS 'Wie man prüft, ob es eine neue Version gibt (für den Quellen-Pfleger)';
COMMENT ON COLUMN sources.notion_url IS 'Link zur Quellen-Seite / zum Leitfaden in Notion';


-- ---------------------------------------------------------------------
-- E) relational_table_metadata
-- ---------------------------------------------------------------------
ALTER TABLE relational_table_metadata
    ADD COLUMN grain                varchar(200),
    ADD COLUMN join_keys            varchar(200),
    ADD COLUMN loader_script        varchar(200),
    ADD COLUMN status               varchar(20) NOT NULL DEFAULT 'active',
    ADD COLUMN metadata_reviewed_at timestamptz;

ALTER TABLE relational_table_metadata
    ADD CONSTRAINT chk_rtm_status CHECK (status IN ('active', 'deprecated', 'experimental'));

COMMENT ON COLUMN relational_table_metadata.grain IS 'Was ist eine Zeile? z. B. "Konflikt-Jahr", "Länderpaar-Jahr", "Land-Produkt-Jahr"';
COMMENT ON COLUMN relational_table_metadata.join_keys IS 'Spalten für die Verbindung zu Ländern und Jahren, z. B. "iso_numeric, year"';
COMMENT ON COLUMN relational_table_metadata.loader_script IS 'Skript, das die Tabelle lädt (Pfad im Repo)';
COMMENT ON COLUMN relational_table_metadata.status IS 'active / deprecated / experimental';
COMMENT ON COLUMN relational_table_metadata.metadata_reviewed_at IS 'Zeitpunkt der Freigabe der Metadaten durch Julian';


-- ---------------------------------------------------------------------
-- Neue Tabelle: known_issues
-- ---------------------------------------------------------------------
CREATE TABLE known_issues (
    id             serial PRIMARY KEY,
    scope          varchar(20)  NOT NULL CHECK (scope IN ('database', 'source', 'indicator', 'table')),
    source_id      integer      REFERENCES sources(id),
    indicator_code varchar(100) REFERENCES indicator_metadata(indicator_code),
    table_name     varchar(200),                 -- schema.tabelle bei scope = 'table'
    title          varchar(200) NOT NULL,
    description    text         NOT NULL,
    decision       varchar(20)  NOT NULL DEFAULT 'accepted'
                   CHECK (decision IN ('accepted', 'to_fix', 'fixed', 'wont_fix')),
    decided_by     varchar(50)  NOT NULL DEFAULT 'julian',
    created_at     timestamptz  NOT NULL DEFAULT now(),
    resolved_at    timestamptz,
    CHECK (scope <> 'source'    OR source_id      IS NOT NULL),
    CHECK (scope <> 'indicator' OR indicator_code IS NOT NULL),
    CHECK (scope <> 'table'     OR table_name     IS NOT NULL)
);

COMMENT ON TABLE known_issues IS 'Bekannte Auffälligkeiten mit Entscheidung. Agenten melden diese nicht erneut als neu.';

INSERT INTO known_issues (scope, source_id, title, description, decision)
SELECT 'source', id, 'V-Dem erst ab 1900 geladen',
       'V-Dem reicht laut Codebook bis 1789 zurück. Der Import ab 1900 ist eine bewusste Entscheidung (Julian, 09.11.2026).',
       'accepted'
FROM sources WHERE short_code = 'VDEM';

INSERT INTO known_issues (scope, indicator_code, title, description, decision)
SELECT 'indicator', indicator_code, 'Gini (WB) sehr dünn besetzt',
       'WB:SI.POV.GINI hat nur wenige Länder. Früher geprüft: Der Datensatz ist echt dünn, kein Ladefehler (Kommunikationsprotokoll, Fall 5).',
       'accepted'
FROM indicator_metadata WHERE indicator_code = 'WB:SI.POV.GINI';


-- ---------------------------------------------------------------------
-- Neue Übersicht: indicator_coverage (nach jedem Laden auffrischen:
--   REFRESH MATERIALIZED VIEW indicator_coverage;)
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW indicator_coverage AS
SELECT indicator_code,
       source_id,
       COUNT(*)                    AS n_values,
       COUNT(DISTINCT iso_numeric) AS n_countries,
       COUNT(DISTINCT time_period) AS n_periods,
       MIN(time_period)            AS first_period,
       MAX(time_period)            AS last_period,
       MIN(value)                  AS min_value,
       MAX(value)                  AS max_value,
       now()                       AS refreshed_at
FROM indicators
GROUP BY indicator_code, source_id;

CREATE UNIQUE INDEX idx_indicator_coverage ON indicator_coverage (indicator_code, source_id);

COMMENT ON MATERIALIZED VIEW indicator_coverage IS 'Abdeckung pro Indikator. Nach jedem Laden auffrischen: REFRESH MATERIALIZED VIEW indicator_coverage;';


-- ---------------------------------------------------------------------
-- Leserechte für den Agenten-Zugang
-- ---------------------------------------------------------------------
GRANT SELECT ON known_issues, indicator_coverage TO ci_agent_readonly;
