-- Sources table: All data sources used in this project
-- Created: 2026-05

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_code VARCHAR(20) UNIQUE NOT NULL,
    url VARCHAR(255),
    description TEXT
);