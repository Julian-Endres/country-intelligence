-- Indicators table: Stores actual data values for countries
-- Each row = one indicator value for one country, source and time period
-- obs_status: A=actual, E=estimated, P=provisional, F=forecast
-- Created: 2026-05

CREATE TABLE indicators (
    id SERIAL PRIMARY KEY,
    iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
    indicator_code VARCHAR(100) REFERENCES indicator_metadata(indicator_code),
    source_id INT REFERENCES sources(id),
    value FLOAT,
    time_period VARCHAR(10),
    obs_status CHAR(1) DEFAULT 'A',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(iso_numeric, indicator_code, source_id, time_period)
);