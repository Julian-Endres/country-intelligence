-- Health indicators metadata
-- Run BEFORE load_health.py

INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension) VALUES

-- Disease
('WB:SH.STA.DIAB.ZS', 'Diabetes prevalence (% of population ages 20 to 79)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.TBS.INCD', 'Incidence of tuberculosis (per 100,000 people)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.TBS.DTEC.ZS', 'Tuberculosis case detection rate (%, all forms)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.TBS.CURE.ZS', 'Tuberculosis treatment success rate (% of new cases)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.DYN.NCOM.ZS', 'Mortality from CVD, cancer, diabetes or CRD between exact ages 30 and 70 (%)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.DYN.NCOM.FE.ZS', 'Mortality from CVD, cancer, diabetes or CRD between exact ages 30 and 70, female (%)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.DYN.NCOM.MA.ZS', 'Mortality from CVD, cancer, diabetes or CRD between exact ages 30 and 70, male (%)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.MLR.INCD.P3', 'Incidence of malaria (per 1,000 population at risk)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),

-- HIV/AIDS
('WB:SH.DYN.AIDS.ZS', 'Prevalence of HIV, total (% of population ages 15-49)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.DYN.AIDS.FE.ZS', 'Women''s share of population ages 15+ living with HIV (%)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.HIV.1524.FE.ZS', 'Prevalence of HIV, female (% ages 15-24)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.HIV.1524.MA.ZS', 'Prevalence of HIV, male (% ages 15-24)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.HIV.INCD.ZS', 'Incidence of HIV, ages 15-49 (per 1,000 uninfected population ages 15-49)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),
('WB:SH.HIV.ARTC.ZS', 'Antiretroviral therapy coverage (% of people living with HIV)', 1, 'Health', 'Health, Body & Behavior', 'Disease'),

-- Nutrition
('WB:SH.ANM.ALLW.ZS', 'Prevalence of anemia among women of reproductive age (% of women ages 15-49)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.ANM.NPRG.ZS', 'Prevalence of anemia among non-pregnant women (% of women ages 15-49)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.ANM.CHLD.ZS', 'Prevalence of anemia among children (% of children ages 6-59 months)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.PRG.ANEM', 'Prevalence of anemia among pregnant women (%)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.STNT.ME.ZS', 'Prevalence of stunting, height for age (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.STNT.ME.FE.ZS', 'Prevalence of stunting, height for age, female (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.STNT.ME.MA.ZS', 'Prevalence of stunting, height for age, male (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.OWGH.ME.ZS', 'Prevalence of overweight, weight for height (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.OWGH.ME.FE.ZS', 'Prevalence of overweight, weight for height, female (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),
('WB:SH.STA.OWGH.ME.MA.ZS', 'Prevalence of overweight, weight for height, male (modeled estimate, % of children under 5)', 1, 'Health', 'Health, Body & Behavior', 'Nutrition'),

-- WASH
('WB:SH.H2O.BASW.ZS', 'People using at least basic drinking water services (% of population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.H2O.BASW.RU.ZS', 'People using at least basic drinking water services, rural (% of rural population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.H2O.BASW.UR.ZS', 'People using at least basic drinking water services, urban (% of urban population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.H2O.SMDW.ZS', 'People using safely managed drinking water services (% of population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.STA.BASS.ZS', 'People using at least basic sanitation services (% of population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.STA.BASS.RU.ZS', 'People using at least basic sanitation services, rural (% of rural population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.STA.BASS.UR.ZS', 'People using at least basic sanitation services, urban (% of urban population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.STA.SMSS.ZS', 'People using safely managed sanitation services (% of population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),
('WB:SH.STA.WASH.P5', 'Mortality rate attributed to unsafe water, unsafe sanitation and lack of hygiene (per 100,000 population)', 1, 'Health', 'Health, Body & Behavior', 'WASH'),

-- Immunization
('WB:SH.IMM.IDPT', 'Immunization, DPT (% of children ages 12-23 months)', 1, 'Health', 'Health, Body & Behavior', 'Immunization'),
('WB:SH.IMM.MEAS', 'Immunization, measles (% of children ages 12-23 months)', 1, 'Health', 'Health, Body & Behavior', 'Immunization'),
('WB:SH.IMM.HEPB', 'Immunization, HepB3 (% of one-year-old children)', 1, 'Health', 'Health, Body & Behavior', 'Immunization'),

-- Healthcare system
('WB:SH.MED.BEDS.ZS', 'Hospital beds (per 1,000 people)', 1, 'Health', 'Health, Body & Behavior', 'Healthcare system'),
('WB:SH.MED.PHYS.ZS', 'Physicians (per 1,000 people)', 1, 'Health', 'Health, Body & Behavior', 'Healthcare system'),
('WB:SH.MED.NUMW.P3', 'Nurses and midwives (per 1,000 people)', 1, 'Health', 'Health, Body & Behavior', 'Healthcare system'),
('WB:SH.XPD.CHEX.GD.ZS', 'Current health expenditure (% of GDP)', 1, 'Health', 'Health, Body & Behavior', 'Healthcare system'),
('WB:SH.XPD.CHEX.PC.CD', 'Current health expenditure per capita (current US$)', 1, 'Health', 'Health, Body & Behavior', 'Healthcare system')

ON CONFLICT (indicator_code) DO NOTHING;
