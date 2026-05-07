-- Updates the region column based on subregion values
-- Run after countries are populated via load_countries.py

UPDATE countries SET region = 'Europe' 
WHERE subregion IN ('Northern Europe', 'Western Europe', 'Southern Europe', 'Eastern Europe', 'Central Europe', 'Southeast Europe');

UPDATE countries SET region = 'Asia' 
WHERE subregion IN ('Eastern Asia', 'Western Asia', 'South-Eastern Asia', 'Southern Asia', 'Central Asia');

UPDATE countries SET region = 'Africa' 
WHERE subregion IN ('Northern Africa', 'Western Africa', 'Eastern Africa', 'Middle Africa', 'Southern Africa');

UPDATE countries SET region = 'Americas' 
WHERE subregion IN ('North America', 'South America', 'Central America', 'Caribbean');

UPDATE countries SET region = 'Oceania' 
WHERE subregion IN ('Australia and New Zealand', 'Melanesia', 'Polynesia', 'Micronesia');

UPDATE countries SET region = 'Antarctic' 
WHERE subregion IS NULL;

COMMIT;