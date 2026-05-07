-- Indicator Metadata: Describes what each indicator means
-- Primary Key: indicator_code (e.g. NY.GDP.PCAP.CD)
-- Created: 2026-05

CREATE TABLE indicator_metadata (
    indicator_code VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    unit VARCHAR(50),
    source_id INT REFERENCES sources(id),
    category VARCHAR(100)
);