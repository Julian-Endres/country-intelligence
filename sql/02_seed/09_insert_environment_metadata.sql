-- Environment indicators metadata
-- Run BEFORE load_environment.py

INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension) VALUES

-- Land use
('WB:AG.LND.TOTL.K2', 'Land area (sq. km)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),
('WB:AG.LND.FRST.ZS', 'Forest area (% of land area)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),
('WB:AG.LND.FRST.K2', 'Forest area (sq. km)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),
('WB:AG.LND.AGRI.ZS', 'Agricultural land (% of land area)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),
('WB:AG.LND.ARBL.ZS', 'Arable land (% of land area)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),
('WB:AG.LND.CROP.ZS', 'Permanent cropland (% of land area)', 1, 'Agriculture & Rural Development', 'Geography & Environment', 'Land use'),

-- Protected areas
('WB:ER.LND.PTLD.ZS', 'Terrestrial protected areas (% of total land area)', 1, 'Environment', 'Geography & Environment', 'Biodiversity & Protection'),
('WB:ER.PTD.TOTL.ZS', 'Terrestrial and marine protected areas (% of total territorial area)', 1, 'Environment', 'Geography & Environment', 'Biodiversity & Protection'),

-- Emissions
('WB:EN.GHG.ALL.MT.CE.AR5', 'Total greenhouse gas emissions excluding LULUCF (Mt CO2e)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.ALL.PC.CE.AR5', 'Total greenhouse gas emissions excluding LULUCF per capita (t CO2e/capita)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.TOT.ZG.AR5', 'Total greenhouse gas emissions excluding LULUCF (% change from 1990)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.CO2.MT.CE.AR5', 'Carbon dioxide (CO2) emissions (total) excluding LULUCF (Mt CO2e)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.CO2.PC.CE.AR5', 'Carbon dioxide (CO2) emissions excluding LULUCF per capita (t CO2e/capita)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.CO2.ZG.AR5', 'Carbon dioxide (CO2) emissions (total) excluding LULUCF (% change from 1990)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.CH4.MT.CE.AR5', 'Methane (CH4) emissions (total) excluding LULUCF (Mt CO2e)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),
('WB:EN.GHG.N2O.MT.CE.AR5', 'Nitrous oxide (N2O) emissions (total) excluding LULUCF (Mt CO2e)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate'),

-- Air quality
('WB:EN.ATM.PM25.MC.M3', 'PM2.5 air pollution, mean annual exposure (micrograms per cubic meter)', 1, 'Environment', 'Geography & Environment', 'Air quality'),
('WB:EN.ATM.PM25.MC.ZS', 'PM2.5 air pollution, population exposed to levels exceeding WHO guideline value (% of total)', 1, 'Environment', 'Geography & Environment', 'Air quality'),

-- Adjusted savings
('WB:NY.ADJ.DCO2.CD', 'Adjusted savings: carbon dioxide damage (current US$)', 1, 'Environment', 'Geography & Environment', 'Emissions & Climate')

ON CONFLICT (indicator_code) DO NOTHING;
