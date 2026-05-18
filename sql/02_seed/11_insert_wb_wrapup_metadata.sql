-- WB Wrap-up indicators metadata
-- Final batch from World Bank WDI
-- Run BEFORE load_wb_wrapup.py

INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension) VALUES

-- Labor: Youth employment
('WB:SL.EMP.1524.SP.ZS', 'Employment to population ratio, ages 15-24, total (%) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),
('WB:SL.EMP.1524.SP.FE.ZS', 'Employment to population ratio, ages 15-24, female (%) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),
('WB:SL.EMP.1524.SP.MA.ZS', 'Employment to population ratio, ages 15-24, male (%) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),

-- Labor: Youth unemployment
('WB:SL.UEM.1524.ZS', 'Unemployment, youth total (% of total labor force ages 15-24) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),
('WB:SL.UEM.1524.FE.ZS', 'Unemployment, youth female (% of female labor force ages 15-24) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),
('WB:SL.UEM.1524.MA.ZS', 'Unemployment, youth male (% of male labor force ages 15-24) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Labour market'),

-- Labor: Employment by sector
('WB:SL.AGR.EMPL.ZS', 'Employment in agriculture (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.AGR.EMPL.FE.ZS', 'Employment in agriculture, female (% of female employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.AGR.EMPL.MA.ZS', 'Employment in agriculture, male (% of male employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.IND.EMPL.ZS', 'Employment in industry (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.IND.EMPL.FE.ZS', 'Employment in industry, female (% of female employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.IND.EMPL.MA.ZS', 'Employment in industry, male (% of male employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.SRV.EMPL.ZS', 'Employment in services (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.SRV.EMPL.FE.ZS', 'Employment in services, female (% of female employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),
('WB:SL.SRV.EMPL.MA.ZS', 'Employment in services, male (% of male employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment by sector'),

-- Labor: Employment type
('WB:SL.EMP.SELF.ZS', 'Self-employed, total (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment type'),
('WB:SL.EMP.MPYR.ZS', 'Employers, total (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Economy & Infrastructure', 'Employment type'),
('WB:SL.EMP.WORK.ZS', 'Wage and salaried workers, total (% of total employment) (modeled ILO estimate)', 1, 'Social Protection & Labor', 'Employment type', 'Employment type'),

-- Gender & Political representation
('WB:SG.GEN.PARL.ZS', 'Proportion of seats held by women in national parliaments (%)', 1, 'Gender', 'Politics & Governance', 'Political representation'),

-- Economic structure
('WB:NV.AGR.TOTL.ZS', 'Agriculture, forestry, and fishing, value added (% of GDP)', 1, 'Economy & Growth', 'Economy & Infrastructure', 'Economic structure'),
('WB:NV.IND.TOTL.ZS', 'Industry (including construction), value added (% of GDP)', 1, 'Economy & Growth', 'Economy & Infrastructure', 'Economic structure'),
('WB:NV.IND.MANF.ZS', 'Manufacturing, value added (% of GDP)', 1, 'Economy & Growth', 'Economy & Infrastructure', 'Economic structure'),
('WB:NV.SRV.TOTL.ZS', 'Services, value added (% of GDP)', 1, 'Economy & Growth', 'Economy & Infrastructure', 'Economic structure'),

-- High-tech
('WB:TX.MNF.TECH.ZS.UN', 'Medium and high-tech exports (% manufactured exports)', 1, 'Economy & Growth', 'Economy & Infrastructure', 'Economic structure'),

-- Tourism
('WB:ST.INT.ARVL', 'International tourism, number of arrivals', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),
('WB:ST.INT.DPRT', 'International tourism, number of departures', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),
('WB:ST.INT.RCPT.CD', 'International tourism, receipts (current US$)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),
('WB:ST.INT.XPND.CD', 'International tourism, expenditures (current US$)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),
('WB:BX.GSR.TRVL.ZS', 'Travel services (% of service exports, BoP)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),
('WB:BM.GSR.TRVL.ZS', 'Travel services (% of service imports, BoP)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Tourism'),

-- Remittances
('WB:BX.TRF.PWKR.CD.DT', 'Personal remittances, received (current US$)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Remittances & Diaspora'),
('WB:BX.TRF.PWKR.DT.GD.ZS', 'Personal remittances, received (% of GDP)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Remittances & Diaspora'),
('WB:BM.TRF.PWKR.CD.DT', 'Personal remittances, paid (current US$)', 1, 'Economy & Growth', 'International Relations & Global Integration', 'Remittances & Diaspora'),

-- Water resources
('WB:ER.H2O.INTR.PC', 'Renewable internal freshwater resources per capita (cubic meters)', 1, 'Environment', 'Geography & Environment', 'Water resources'),
('WB:ER.H2O.FWST.ZS', 'Level of water stress: freshwater withdrawal as a proportion of available freshwater resources', 1, 'Environment', 'Geography & Environment', 'Water resources'),

-- Urban
('WB:EN.POP.SLUM.UR.ZS', 'Population living in slums (% of urban population)', 1, 'Urban Development', 'Population & Demographics', 'Urbanization'),

-- ICT
('WB:IT.NET.SECR.P6', 'Secure Internet servers (per 1 million people)', 1, 'Infrastructure', 'Communication & Media', 'Internet & ICT'),
('WB:IT.NET.USER.ZS', 'Individuals using the Internet (% of population)', 1, 'Infrastructure', 'Communication & Media', 'Internet & ICT')

ON CONFLICT (indicator_code) DO NOTHING;
