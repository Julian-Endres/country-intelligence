-- Qualitätskontrolle nach den Übertragungen vom 14.11.2026 (#123). Nur lesend.
-- Aufruf (Shell, Repo-Wurzel):
--   psql -d country_intelligence -X -q -f sql/03_queries/2026-11-14_qk_sekretaer_uebertragung.sql > scripts/agent/output/2026-11-14_qk.txt 2>&1
BEGIN READ ONLY;

\echo '== Q1 Heute übertragen je Quelle (erwartet: WB 79, VDEM 54, PWT 21, UNDP 19 = 173)'
SELECT split_part(indicator_code, ':', 1) AS quelle, COUNT(*)
FROM indicator_metadata WHERE metadata_reviewed_at::date = '2026-11-14'
GROUP BY 1 ORDER BY 1;

\echo '== Q2 Fortschritt je Quelle (gesamt / beschrieben)'
SELECT split_part(indicator_code, ':', 1) AS quelle, COUNT(*) AS gesamt,
       COUNT(metadata_reviewed_at) AS beschrieben
FROM indicator_metadata
WHERE split_part(indicator_code, ':', 1) IN ('WB', 'VDEM', 'PWT', 'UNDP')
GROUP BY 1 ORDER BY 1;

\echo '== Q3 known_issues heute bzw. neueste'
SELECT id, scope, indicator_code, title FROM known_issues ORDER BY id DESC LIMIT 5;

\echo '== Q4 Regelverstöße bei allen beschriebenen Indikatoren'
SELECT indicator_code,
       CASE WHEN description IS NULL THEN 'description leer'
            WHEN length(description) > 200 THEN 'description > 200'
            WHEN scale_type IN ('index','ordinal','binary','categorical') AND unit IS NOT NULL THEN 'unit bei ' || scale_type
            WHEN scale_type IN ('ordinal','binary','categorical') AND value_labels IS NULL THEN 'value_labels fehlen'
            WHEN scale_type IS NULL THEN 'scale_type leer'
       END AS problem
FROM indicator_metadata
WHERE metadata_reviewed_at IS NOT NULL
  AND (description IS NULL OR length(description) > 200
       OR (scale_type IN ('index','ordinal','binary','categorical') AND unit IS NOT NULL)
       OR (scale_type IN ('ordinal','binary','categorical') AND value_labels IS NULL)
       OR scale_type IS NULL)
ORDER BY 1;

\echo '== Q5 JSON aller heute übertragenen Zeilen (für den Abgleich mit den Lauf-Dateien)'
\pset format unaligned
\pset tuples_only on
SELECT json_agg(row_to_json(t) ORDER BY t.indicator_code) FROM (
  SELECT indicator_code, name, description, unit, scale_type, scale_min, scale_max, direction,
         data_origin, temporal_type, key_info, producer_definition, value_labels, reference, keywords
  FROM indicator_metadata WHERE metadata_reviewed_at::date = '2026-11-14') t;
\pset tuples_only off
\pset format aligned

ROLLBACK;
