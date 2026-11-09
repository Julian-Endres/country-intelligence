-- Vor der Migration ausführen. Erwartet: 0 Zeilen (keine der neuen Spalten/Objekte existiert schon).
SELECT table_name, column_name FROM information_schema.columns
WHERE (table_name = 'indicator_metadata' AND column_name IN ('direction','scale_type','scale_min','scale_max','data_origin','temporal_type','is_lead_indicator','keywords','reference','loader_script','status','metadata_reviewed_at','added_at'))
   OR (table_name = 'sources' AND column_name IN ('summary','publisher','license','citation','documentation_url','loaded_version','loaded_at','update_frequency','access_method','update_check','notion_url'))
   OR (table_name = 'relational_table_metadata' AND column_name IN ('grain','join_keys','loader_script','status','metadata_reviewed_at'))
UNION ALL
SELECT 'objekt', relname FROM pg_class WHERE relname IN ('known_issues','indicator_coverage');
