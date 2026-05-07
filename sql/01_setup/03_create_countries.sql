-- Countries table: Base table with stable country information
-- Primary Key: iso_numeric (ISO 3166-1 numeric standard)
-- Created: 2026-05

CREATE TABLE countries (
    iso_numeric CHAR(3) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    iso_code_3 CHAR(3) UNIQUE NOT NULL,
    iso_code_2 CHAR(2) UNIQUE NOT NULL,
    region VARCHAR(100),
    subregion VARCHAR(100),
    capital VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    area_km2 FLOAT,
    is_landlocked BOOLEAN,
    is_island BOOLEAN,
    flag_url VARCHAR(255)
);