-- =====================================================================
-- CI-172 Bestand: Verwechslungspaare über ALLE Quellen (nur lesend)
-- Ausführen (Shell):
--   psql -U postgres -d country_intelligence -f sql/03_queries/ci172_verwechslungspaare.sql \
--        > "Claude outputs/fuzzy_audit/verwechslungspaare.txt"
--
-- Idee: Das Fuzzy-Audit prüft nur 11 Loader. Fehlzuordnungen hinterlassen aber in JEDER Quelle
-- dieselben Spuren, egal wie der Loader zuordnet:
--   A  Eine Quelle mit vielen Ländern hat nur EINEN Partner eines Verwechslungspaars
--      (TI und FH: NGA da, NER fehlt).
--   B  Beide Partner da, aber fast identische Werte (dieselbe Rohzeile zweimal).
--   C  Namibia fehlt in großen Quellen (ISO2 "NA" wird von pandas als leer gelesen).
-- Ergebnis = Verdachtsliste, kein Beweis. Jeder Treffer wird an der Rohdatei geprüft.
-- =====================================================================

CREATE TEMP TABLE paare (a char(3), b char(3), hinweis text);
INSERT INTO paare VALUES
 ('NER','NGA','Niger / Nigeria'),
 ('COG','COD','Kongo / DR Kongo'),
 ('PRK','KOR','Nordkorea / Südkorea'),
 ('SDN','SSD','Sudan / Südsudan (SSD erst ab 2011)'),
 ('GIN','GNB','Guinea / Guinea-Bissau'),
 ('GIN','GNQ','Guinea / Äquatorialguinea'),
 ('DMA','DOM','Dominica / Dominikanische Republik'),
 ('AUT','AUS','Österreich / Australien'),
 ('SVK','SVN','Slowakei / Slowenien'),
 ('COL','CAN','Kolumbien / Kanada („Columbia“)'),
 ('MNG','MNE','Mongolei / Montenegro'),
 ('MAC','MKD','Macau / Nordmazedonien'),
 ('WSM','ASM','Samoa / Amerikanisch-Samoa'),
 ('VGB','VIR','Brit. / Amerik. Jungferninseln'),
 ('IRN','IRQ','Iran / Irak'),
 ('CHN','TWN','China / Taiwan'),
 ('GEO','SGS','Georgien / Südgeorgien');

CREATE TEMP TABLE quelle_land AS
SELECT DISTINCT i.source_id, c.iso_code_3
FROM indicators i JOIN countries c USING (iso_numeric);

CREATE TEMP TABLE umfang AS
SELECT source_id, COUNT(*) AS n_laender FROM quelle_land GROUP BY 1;

-- A. Nur ein Partner vorhanden (Quellen mit mindestens 100 Ländern)
SELECT s.short_code, u.n_laender, p.hinweis,
       CASE WHEN qa.source_id IS NULL THEN p.a ELSE p.b END AS fehlt,
       CASE WHEN qa.source_id IS NULL THEN p.b ELSE p.a END AS vorhanden
FROM umfang u
JOIN sources s ON s.id = u.source_id
CROSS JOIN paare p
LEFT JOIN quelle_land qa ON qa.source_id = u.source_id AND qa.iso_code_3 = p.a
LEFT JOIN quelle_land qb ON qb.source_id = u.source_id AND qb.iso_code_3 = p.b
WHERE u.n_laender >= 100
  AND (qa.source_id IS NULL) <> (qb.source_id IS NULL)
ORDER BY s.short_code, p.hinweis;

-- B. Beide Partner vorhanden, Werte im selben Indikator-Jahr zu mindestens 90 % gleich (mind. 10 Paare)
SELECT s.short_code, p.hinweis,
       COUNT(*) AS paare_gesamt,
       SUM(CASE WHEN ia.value = ib.value THEN 1 ELSE 0 END) AS gleich,
       ROUND(100.0 * SUM(CASE WHEN ia.value = ib.value THEN 1 ELSE 0 END) / COUNT(*), 1) AS proz_gleich
FROM paare p
JOIN countries ca ON ca.iso_code_3 = p.a
JOIN countries cb ON cb.iso_code_3 = p.b
JOIN indicators ia ON ia.iso_numeric = ca.iso_numeric
JOIN indicators ib ON ib.iso_numeric = cb.iso_numeric
                  AND ib.source_id = ia.source_id
                  AND ib.indicator_code = ia.indicator_code
                  AND ib.time_period = ia.time_period
JOIN sources s ON s.id = ia.source_id
GROUP BY s.short_code, p.hinweis
HAVING COUNT(*) >= 10
   AND SUM(CASE WHEN ia.value = ib.value THEN 1 ELSE 0 END) >= 0.9 * COUNT(*)
ORDER BY proz_gleich DESC, s.short_code;

-- C. Namibia fehlt in Quellen mit mindestens 150 Ländern
SELECT s.short_code, u.n_laender
FROM umfang u JOIN sources s ON s.id = u.source_id
WHERE u.n_laender >= 150
  AND NOT EXISTS (SELECT 1 FROM quelle_land q WHERE q.source_id = u.source_id AND q.iso_code_3 = 'NAM')
ORDER BY 1;
