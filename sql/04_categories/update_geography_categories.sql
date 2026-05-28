-- ============================================================
-- Geography & Environment — Category & Dimension Assignments
-- Stand: 2026-05-28
-- ============================================================
-- 5 Categories:
--   Climate & Emissions
--   Land & Ecosystems
--   Biodiversity
--   Water & Weather
--   Environmental Inequality


-- Leere Wrapper zuerst löschen
DELETE FROM indicator_metadata WHERE indicator_code IN (
    'WID:ehfcari999', 'WID:khfcari999', 'WID:khfghgi999', 'WID:lpfghgi999',
    'OWID_CO2:fossil_fuel', 'OWID_CO2:renewables_share',
    'GBIF:fish'
);


-- ============================================================
-- 1. CLIMATE & EMISSIONS
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Climate & Emissions',
    dimension = 'Emissions & Climate'
WHERE indicator_code IN (
    'OWID_CO2:co2',
    'OWID_CO2:co2_per_capita',
    'OWID_CO2:co2_per_gdp',
    'OWID_CO2:coal_co2',
    'OWID_CO2:gas_co2',
    'OWID_CO2:oil_co2',
    'OWID_CO2:methane',
    'OWID_CO2:nitrous_oxide',
    'OWID_CO2:primary_energy',
    'OWID_CO2:share_global_co2',
    'WB:EN.GHG.ALL.MT.CE.AR5',
    'WB:EN.GHG.ALL.PC.CE.AR5',
    'WB:EN.GHG.CH4.MT.CE.AR5',
    'WB:EN.GHG.CO2.MT.CE.AR5',
    'WB:EN.GHG.CO2.PC.CE.AR5',
    'WB:EN.GHG.CO2.ZG.AR5',
    'WB:EN.GHG.N2O.MT.CE.AR5',
    'WB:EN.GHG.TOT.ZG.AR5',
    'WB:NY.ADJ.DCO2.CD',
    'WID:ehfcari999:p0p100',
    'WID:khfcari999:p0p100',
    'WID:khfghgi999:p0p100'
);

UPDATE indicator_metadata SET
    category  = 'Climate & Emissions',
    dimension = 'Air Quality'
WHERE indicator_code IN (
    'WHO:SDGPM25',
    'WB:EN.ATM.PM25.MC.M3',
    'WB:EN.ATM.PM25.MC.ZS'
);


-- ============================================================
-- 2. LAND & ECOSYSTEMS
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Land & Ecosystems',
    dimension = 'Land Use'
WHERE indicator_code IN (
    'FAO_LAND:agricultural_land',
    'FAO_LAND:arable_land',
    'FAO_LAND:country_area',
    'FAO_LAND:cropland',
    'FAO_LAND:forest_land',
    'FAO_LAND:inland_waters',
    'FAO_LAND:land_area',
    'FAO_LAND:nat_regen_forest',
    'FAO_LAND:other_land',
    'FAO_LAND:pastures',
    'FAO_LAND:permanent_crops',
    'FAO_LAND:planted_forest',
    'FAO_LAND:primary_forest',
    'WB:AG.LND.AGRI.ZS',
    'WB:AG.LND.ARBL.ZS',
    'WB:AG.LND.CROP.ZS',
    'WB:AG.LND.FRST.K2',
    'WB:AG.LND.FRST.ZS',
    'WB:AG.LND.TOTL.K2'
);

UPDATE indicator_metadata SET
    category  = 'Land & Ecosystems',
    dimension = 'Biodiversity & Protection'
WHERE indicator_code IN (
    'WB:ER.LND.PTLD.ZS',
    'WB:ER.PTD.TOTL.ZS'
);


-- ============================================================
-- 3. BIODIVERSITY
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Biodiversity',
    dimension = 'Species Occurrences'
WHERE indicator_code IN (
    'GBIF:amphibians',
    'GBIF:birds',
    'GBIF:fungi',
    'GBIF:insects',
    'GBIF:mammals',
    'GBIF:plants',
    'GBIF:reptiles',
    'GBIF:total'
);

UPDATE indicator_metadata SET
    category  = 'Biodiversity',
    dimension = 'Threatened Species'
WHERE indicator_code IN (
    'GBIF:iucn_cr',
    'GBIF:iucn_en',
    'GBIF:iucn_nt',
    'GBIF:iucn_vu'
);


-- ============================================================
-- 4. WATER & WEATHER
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Water & Weather',
    dimension = 'Water Resources'
WHERE indicator_code IN (
    'WB:ER.H2O.FWST.ZS',
    'WB:ER.H2O.INTR.PC'
);

UPDATE indicator_metadata SET
    category  = 'Water & Weather',
    dimension = 'Climate & Weather'
WHERE indicator_code IN (
    'OPENMETEO:precip_sum',
    'OPENMETEO:sunshine',
    'OPENMETEO:temp_mean'
);


-- ============================================================
-- 5. ENVIRONMENTAL INEQUALITY
-- GHG Emissionen nach Einkommensgruppe (WID)
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Environmental Inequality',
    dimension = 'GHG by Income Group'
WHERE indicator_code IN (
    'WID:lpfghgi999:p0p100',
    'WID:lpfghgi999:p0p50',
    'WID:lpfghgi999:p90p100',
    'WID:lpfghgi999:p99p100'
);


-- ============================================================
-- VERIFICATION
-- ============================================================

SELECT
    category,
    dimension,
    COUNT(*) as n_indicators,
    SUM(CASE WHEN n_countries > 0 THEN 1 ELSE 0 END) as with_data
FROM (
    SELECT
        im.indicator_code,
        im.category,
        im.dimension,
        COUNT(DISTINCT i.iso_numeric) as n_countries
    FROM indicator_metadata im
    LEFT JOIN indicators i ON i.indicator_code = im.indicator_code
    WHERE im.domain = 'Geography & Environment'
    GROUP BY im.indicator_code, im.category, im.dimension
) sub
GROUP BY category, dimension
ORDER BY category, dimension;
