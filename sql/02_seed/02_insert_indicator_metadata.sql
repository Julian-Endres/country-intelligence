-- Initial seed data for indicator_metadata table
-- Run after 04_create_indicator_metadata.sql and 01_insert_sources.sql
-- source_id = 1 refers to World Bank

INSERT INTO indicator_metadata (indicator_code, name, description, unit, source_id, category) VALUES
('NY.GDP.PCAP.CD', 'GDP per capita', 'Gross domestic product per capita in current US dollars', 'USD', 1, 'Economy'),
('SP.DYN.LE00.IN', 'Life expectancy at birth', 'Life expectancy at birth in years, total population', 'years', 1, 'Health'),
('SP.POP.TOTL', 'Total population', 'Total population of the country', 'people', 1, 'Demographics'),
('SE.ADT.LITR.ZS', 'Literacy rate', 'Adult literacy rate, population 15+ years', '%', 1, 'Education'),
('SI.POV.GINI', 'Gini coefficient', 'Income inequality measure, 0 = perfect equality, 100 = perfect inequality', 'index', 1, 'Economy');