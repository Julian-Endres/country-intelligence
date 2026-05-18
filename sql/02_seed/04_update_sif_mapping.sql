-- =========================================
-- SIF Domain & Dimension Mapping
-- + WB Category Corrections
-- Run: 2026-05
-- =========================================

-- =========================================
-- PART 1: SIF DOMAIN + DIMENSION MAPPING
-- =========================================

-- Domain 1: Population & Demographics
UPDATE indicator_metadata SET
    domain = 'Population & Demographics',
    dimension = 'Population structure'
WHERE indicator_code IN (
    'WB:SP.POP.TOTL',
    'WB:SP.POP.TOTL.FE.ZS',
    'WB:SP.POP.GROW',
    'WB:EN.POP.DNST',
    'WB:SP.POP.0014.TO.ZS',
    'WB:SP.POP.1564.TO.ZS',
    'WB:SP.POP.65UP.TO',
    'WB:SP.POP.65UP.TO.ZS',
    'WB:SP.POP.DPND'
);

UPDATE indicator_metadata SET
    domain = 'Population & Demographics',
    dimension = 'Fertility & natural change'
WHERE indicator_code IN (
    'WB:SP.DYN.TFRT.IN',
    'WB:SP.DYN.CBRT.IN',
    'WB:SP.DYN.CDRT.IN'
);

UPDATE indicator_metadata SET
    domain = 'Population & Demographics',
    dimension = 'Urbanization'
WHERE indicator_code IN (
    'WB:SP.URB.TOTL',
    'WB:SP.URB.TOTL.IN.ZS',
    'WB:SP.URB.GROW',
    'WB:SP.RUR.TOTL',
    'WB:SP.RUR.TOTL.ZS',
    'WB:SP.RUR.TOTL.ZG'
);

UPDATE indicator_metadata SET
    domain = 'Population & Demographics',
    dimension = 'Migration'
WHERE indicator_code IN (
    'WB:SM.POP.TOTL',
    'WB:SM.POP.TOTL.ZS',
    'WB:SM.POP.NETM'
);

-- Domain 3: Economy & Infrastructure
UPDATE indicator_metadata SET
    domain = 'Economy & Infrastructure',
    dimension = 'Wealth & inequality'
WHERE indicator_code IN (
    'WB:NY.GDP.PCAP.CD',
    'WB:SI.POV.GINI'
);

UPDATE indicator_metadata SET
    domain = 'Economy & Infrastructure',
    dimension = 'Labour market'
WHERE indicator_code IN (
    'WB:SL.UEM.TOTL.MA.ZS',
    'WB:SL.UEM.TOTL.FE.ZS',
    'WB:SL.TLF.CACT.ZS'
);

-- Domain 7: Communication & Media
UPDATE indicator_metadata SET
    domain = 'Communication & Media',
    dimension = 'Literacy & education access'
WHERE indicator_code IN (
    'WB:SE.ADT.LITR.ZS'
);

-- Domain 8: Health, Body & Behavior
UPDATE indicator_metadata SET
    domain = 'Health, Body & Behavior',
    dimension = 'Mortality'
WHERE indicator_code IN (
    'WB:SP.DYN.LE00.IN',
    'WB:SP.DYN.LE00.FE.IN',
    'WB:SP.DYN.LE00.MA.IN',
    'WB:SP.DYN.IMRT.IN',
    'WB:SH.DYN.MORT',
    'WB:SH.STA.MMRT'
);

UPDATE indicator_metadata SET
    domain = 'Health, Body & Behavior',
    dimension = 'Mental health & suicide'
WHERE indicator_code IN (
    'WB:SH.STA.SUIC.P5'
);

UPDATE indicator_metadata SET
    domain = 'Health, Body & Behavior',
    dimension = 'Substance use'
WHERE indicator_code IN (
    'WB:SH.ALC.PCAP.MA.LI',
    'WB:SH.ALC.PCAP.FE.LI'
);

-- =========================================
-- PART 2: WB CATEGORY CORRECTIONS
-- =========================================

-- Urbanization wrongly labeled as "Climate Change"
UPDATE indicator_metadata SET category = 'Demographics'
WHERE indicator_code IN (
    'WB:SP.URB.TOTL',
    'WB:SP.URB.TOTL.IN.ZS',
    'WB:SP.URB.GROW',
    'WB:SP.POP.GROW'
);

-- Migration wrongly labeled as "Financial Sector"
UPDATE indicator_metadata SET category = 'Demographics'
WHERE indicator_code IN (
    'WB:SM.POP.TOTL',
    'WB:SM.POP.TOTL.ZS',
    'WB:SM.POP.NETM'
);

-- Unemployment wrongly labeled as "Education"
UPDATE indicator_metadata SET category = 'Labour'
WHERE indicator_code IN (
    'WB:SL.UEM.TOTL.MA.ZS',
    'WB:SL.UEM.TOTL.FE.ZS',
    'WB:SL.TLF.CACT.ZS'
);

-- Age structure wrongly labeled as "Education"
UPDATE indicator_metadata SET category = 'Demographics'
WHERE indicator_code IN (
    'WB:SP.POP.1564.TO.ZS',
    'WB:SP.POP.0014.TO.ZS'
);

-- =========================================
-- VERIFICATION
-- =========================================

SELECT
    domain,
    dimension,
    category,
    indicator_code,
    name
FROM indicator_metadata
ORDER BY domain NULLS LAST, dimension, indicator_code;
