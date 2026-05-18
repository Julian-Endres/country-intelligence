CREATE TABLE indicator_metadata (
    indicator_code VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    unit VARCHAR(50),
    source_id INT REFERENCES sources(id),
    category VARCHAR(100),
    domain VARCHAR(100),
    dimension VARCHAR(100)
);