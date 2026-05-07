-- Indicators table: Stores actual data values for countries
-- Each row = one indicator value for one country in one year
-- Created: 2026-05

CREATE TABLE indicators (
    id SERIAL PRIMARY KEY,
    iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
    indicator_code VARCHAR(100) REFERENCES indicator_metadata(indicator_code),
    value FLOAT,
    year INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(iso_numeric, indicator_code, year)
);