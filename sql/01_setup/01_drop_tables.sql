-- Drop all tables in correct order (dependencies first)
-- WARNING: This deletes all data!

DROP TABLE IF EXISTS indicators CASCADE;
DROP TABLE IF EXISTS indicator_metadata CASCADE;
DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS sources CASCADE;