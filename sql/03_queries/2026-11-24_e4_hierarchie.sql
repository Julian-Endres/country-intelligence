-- CI-171 E4 (#83): alle aktiven Codes der Dimensions "Human Development" und
-- "Science & Achievement" mit Domain/Category, dazu Nachbar-Dimensions je Category.
-- Nur lesen.
\echo '--- Codes der beiden Dimensions'
SELECT dimension, domain, category, indicator_code
FROM indicator_metadata
WHERE status = 'active' AND dimension IN ('Human Development', 'Science & Achievement')
ORDER BY dimension, domain, category, indicator_code;

\echo ''
\echo '--- Andere Dimensions in denselben Categories (Zielkandidaten)'
SELECT domain, category, dimension, count(*) AS codes
FROM indicator_metadata
WHERE status = 'active'
  AND category IN (SELECT DISTINCT category FROM indicator_metadata
                   WHERE status = 'active' AND dimension IN ('Human Development', 'Science & Achievement'))
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
