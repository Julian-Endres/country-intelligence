-- Nachträge zum Review der Sekretär-Läufe vom 19.11.2026 (Entscheidungen Julian 23.11.2026, Backlog CI-158, CI-162).
-- Ändert KEINE Werte in indicators, nur indicator_metadata (5 Zeilen).
--   1. WEF: domain/category/dimension von gggi_pes und gggi_pos tauschen (Loader hatte die Beschriftung vertauscht;
--      Beleg QoG-Codebuch Jan25 Z. 31636/31656, Gegenprobe Jan26: USA pes 0,248 / pos 0,780). CI-158.
--   2. PEW_REL:rdi: scale_min 0, scale_max 10 (Pew-Methodikseite 12.02.2026: 1 - Summe p², x 11,6, Skala 0-10).
--   3. UNVOTE:n_votes: Name korrigiert (zählt auch Nichtteilnahme X, Loader Z. 196/259).
--   4. UNVOTE:yes_environment: key_info-Note um die Lücken ergänzt (Werte nur 2018-2020, 2023, 2025; Rohdatei nachgezählt).
-- Jede Änderung ist an den alten Wert gebunden: doppelt ausführen ist harmlos, ein unerwarteter Altwert ändert nichts.
-- Unabhängig davon, ob der WEF-Lauf 2026-11-19_1915 schon übertragen ist (der Lauf ändert domain/category/dimension nicht).
-- Aufruf (Shell, Repo-Wurzel; schreibt die Ausgabe ins Log):
--   psql -d country_intelligence -X -f sql/05_migrations/2026-11-23_nachtraege_review_19_11.sql 2>&1 | tee logs/migrations/2026-11-23_nachtraege_review.txt

\echo '== vorher (erwartet: pes = Labour & Employment / Economy, Wealth & Labor / Gender & Labour; pos = Rule of Law & Rights / Politics, Governance & Law / Gender & Political Equality)'
SELECT indicator_code, name, category, domain, dimension, scale_min, scale_max
FROM indicator_metadata
WHERE indicator_code IN ('WEF:gggi_pes', 'WEF:gggi_pos', 'PEW_REL:rdi', 'UNVOTE:n_votes', 'UNVOTE:yes_environment')
ORDER BY 1;
SELECT indicator_code, key_info[5] AS note_5 FROM indicator_metadata WHERE indicator_code = 'UNVOTE:yes_environment';
\echo '== vorher: Wertebereich PEW_REL:rdi (erwartet 0,03 bis 9,25)'
SELECT min(value), max(value), count(*) FROM indicators WHERE indicator_code = 'PEW_REL:rdi';

BEGIN;

-- 1. WEF tauschen (beide Zeilen in einem Schritt, nur wenn beide noch den alten Stand haben)
UPDATE indicator_metadata m SET
    category  = CASE m.indicator_code WHEN 'WEF:gggi_pes' THEN 'Rule of Law & Rights'          ELSE 'Labour & Employment' END,
    domain    = CASE m.indicator_code WHEN 'WEF:gggi_pes' THEN 'Politics, Governance & Law'    ELSE 'Economy, Wealth & Labor' END,
    dimension = CASE m.indicator_code WHEN 'WEF:gggi_pes' THEN 'Gender & Political Equality'   ELSE 'Gender & Labour' END
WHERE m.indicator_code IN ('WEF:gggi_pes', 'WEF:gggi_pos')
  AND (SELECT count(*) FROM indicator_metadata x
       WHERE (x.indicator_code = 'WEF:gggi_pes' AND x.category = 'Labour & Employment' AND x.domain = 'Economy, Wealth & Labor' AND x.dimension = 'Gender & Labour')
          OR (x.indicator_code = 'WEF:gggi_pos' AND x.category = 'Rule of Law & Rights' AND x.domain = 'Politics, Governance & Law' AND x.dimension = 'Gender & Political Equality')) = 2;

-- 2. PEW rdi Skala
UPDATE indicator_metadata SET scale_min = 0, scale_max = 10,
    reference = concat_ws('; ', reference, 'scale 0-10: Pew Research Center, Methodology: Religious Diversity Around the World (12 Feb 2026)')
WHERE indicator_code = 'PEW_REL:rdi' AND scale_min IS NULL AND scale_max IS NULL;

-- 3. UNVOTE n_votes Name
UPDATE indicator_metadata SET name = 'UN GA: Recorded votes (incl. non-voting)'
WHERE indicator_code = 'UNVOTE:n_votes' AND name = 'UN GA: Total votes cast';

-- 4. UNVOTE yes_environment Note
UPDATE indicator_metadata SET key_info = array_replace(key_info,
    'Note: The series starts only in 2018 because earlier country-years have fewer than 3 matching votes.',
    'Note: Values exist only for 2018-2020, 2023 and 2025; all other years have fewer than 3 matching resolutions (57 of 5,694 resolutions in the raw file match the theme).')
WHERE indicator_code = 'UNVOTE:yes_environment'
  AND key_info @> ARRAY['Note: The series starts only in 2018 because earlier country-years have fewer than 3 matching votes.'];

COMMIT;

\echo '== nachher (erwartet: pes = Rule of Law & Rights / Politics, Governance & Law / Gender & Political Equality; pos umgekehrt; rdi 0/10; n_votes neuer Name)'
SELECT indicator_code, name, category, domain, dimension, scale_min, scale_max
FROM indicator_metadata
WHERE indicator_code IN ('WEF:gggi_pes', 'WEF:gggi_pos', 'PEW_REL:rdi', 'UNVOTE:n_votes', 'UNVOTE:yes_environment')
ORDER BY 1;
SELECT indicator_code, key_info[5] AS note_5, cardinality(key_info) AS n FROM indicator_metadata WHERE indicator_code = 'UNVOTE:yes_environment';
\echo '== nachher: Werte in indicators unverändert (erwartet wie vorher)'
SELECT min(value), max(value), count(*) FROM indicators WHERE indicator_code = 'PEW_REL:rdi';
