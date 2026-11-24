-- CI-171 E1 / Grundsatzfrage OWID: Was kam über OWID in die DB, und unter welchem Präfix?
-- Nur lesen. Aufruf (Shell):
--   psql -d country_intelligence -X -f sql/03_queries/2026-11-24_owid_bezugswege.sql > logs/2026-11-24_owid_bezugswege.txt

-- 1) Welche Quellen erwähnen OWID selbst?
--    ILIKE = LIKE ohne Groß/Klein; coalesce macht aus NULL einen leeren Text, damit || nicht NULL ergibt.
\echo '--- 1) Quellen, die OWID in Name, URL, Beschreibung, Herausgeber oder Zitat nennen'
SELECT s.id, s.short_code, s.name, s.publisher
FROM sources s
WHERE coalesce(s.name,'') || ' ' || coalesce(s.url,'') || ' ' || coalesce(s.description,'') || ' '
   || coalesce(s.publisher,'') || ' ' || coalesce(s.citation,'') || ' ' || coalesce(s.documentation_url,'')
      ILIKE ANY (ARRAY['%owid%', '%our world in data%', '%ourworldindata%'])
ORDER BY s.id;

-- 2) Welche Codes deuten auf OWID hin? Zwei Spuren:
--    a) der Loader (loader_script) ist einer der Loader, die laut Code bei OWID laden
--    b) Beschreibung oder Fundstelle (reference) nennen OWID
--    split_part(code, ':', 1) = Präfix vor dem Doppelpunkt.
\echo ''
\echo '--- 2) Codes mit OWID-Spur, je Präfix und Quelle der Metadaten'
SELECT split_part(m.indicator_code, ':', 1)            AS praefix,
       s.short_code                                    AS quelle_metadaten,
       m.loader_script,
       count(*)                                        AS codes,
       count(*) FILTER (WHERE m.status = 'active')     AS aktiv,
       min(m.indicator_code)                           AS beispiel
FROM indicator_metadata m
LEFT JOIN sources s ON s.id = m.source_id
WHERE m.loader_script ILIKE ANY (ARRAY['%owid%', '%load_cpi%', '%load_rsf%', '%load_olympics%'])
   OR coalesce(m.description,'') || ' ' || coalesce(m.reference,'')
      ILIKE ANY (ARRAY['%owid%', '%our world in data%', '%ourworldindata%'])
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- 3) Wo widersprechen sich Werte und Metadaten bei der Quelle?
--    Das ist das Muster der 9 Codes aus #2 – die Abfrage zeigt, ob es noch mehr gibt.
--    Läuft über alle ~4,1 Mio. Werte, kann einige Sekunden dauern.
\echo ''
\echo '--- 3) Werte, deren source_id nicht zur Quelle in den Metadaten passt'
SELECT split_part(i.indicator_code, ':', 1) AS praefix,
       sw.short_code                        AS quelle_werte,
       sm.short_code                        AS quelle_metadaten,
       count(DISTINCT i.indicator_code)     AS codes,
       count(*)                             AS werte
FROM indicators i
JOIN indicator_metadata m ON m.indicator_code = i.indicator_code
LEFT JOIN sources sw ON sw.id = i.source_id
LEFT JOIN sources sm ON sm.id = m.source_id
WHERE i.source_id IS DISTINCT FROM m.source_id   -- IS DISTINCT FROM: wie <>, aber NULL zählt mit
GROUP BY 1, 2, 3
ORDER BY 5 DESC;

-- 4) Gibt es dieselben Themen schon aus anderer Quelle (z. B. WHO direkt über die API)?
--    Und wo sind migration_stock, urban_share, youth_unemployment aus dem OWID-Loader gelandet?
\echo ''
\echo '--- 4) Mögliche Doppelungen: gleiche Themen, alle Quellen'
SELECT m.indicator_code, m.name, s.short_code AS quelle, m.status,
       (SELECT count(*) FROM indicators i WHERE i.indicator_code = m.indicator_code) AS werte
FROM indicator_metadata m
LEFT JOIN sources s ON s.id = m.source_id
WHERE m.name ~* '(alcohol|tobacco|smok|binge|substance|drug|homicide|prison|poverty|migrant|urban|youth.*unemploy|unemploy.*15)'
ORDER BY m.name, m.indicator_code;
