-- Initial seed data for sources table
-- Run after 02_create_sources.sql

INSERT INTO sources (name, short_code, url, description) VALUES
('World Bank', 'WB', 'https://data.worldbank.org', 'Global economic and development indicators'),
('World Health Organization', 'WHO', 'https://www.who.int/data', 'Health and disease statistics worldwide'),
('UN Development Programme', 'UNDP', 'https://hdr.undp.org', 'Human Development Index and related metrics'),
('RestCountries', 'REST', 'https://restcountries.com', 'Country base data including geography and codes'),
('V-Dem Institute', 'VDEM', 'https://v-dem.net', 'Varieties of Democracy political indicators');