-- ============================================================
-- Economy & Infrastructure — Category & Dimension Assignments
-- Stand: 2026-05-28
-- ============================================================
-- 6 Categories:
--   Output & Growth
--   Wealth & Inequality
--   Labour & Employment
--   Economic Structure
--   Public Finance & Energy
--   Human Development


-- ============================================================
-- 1. OUTPUT & GROWTH
-- Wie groß und wie reich ist die Wirtschaft?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Output & Growth',
    dimension = 'GDP & Growth'
WHERE indicator_code IN (
    'WB:NY.GDP.MKTP.CD',
    'WB:NY.GDP.MKTP.KD',
    'WB:NY.GDP.MKTP.KD.ZG',
    'WB:NY.GDP.PCAP.CD',
    'WB:NY.GDP.PCAP.KD',
    'WB:NY.GDP.PCAP.KD.ZG',
    'PWT:rgdpe',
    'PWT:rgdpo',
    'PWT:rgdpna',
    'PWT:pl_gdpo'
);

UPDATE indicator_metadata SET
    category  = 'Output & Growth',
    dimension = 'National Accounts'
WHERE indicator_code IN (
    'PWT:ccon',
    'PWT:csh_c',
    'PWT:csh_g',
    'PWT:csh_i',
    'PWT:csh_m',
    'PWT:csh_x',
    'PWT:cn',
    'PWT:delta',
    'PWT:labsh',
    'PWT:irr',
    'PWT:ctfp',
    'PWT:cwtfp',
    'PWT:hc',
    'PWT:xr',
    'PWT:emp',
    'PWT:avh'
);

UPDATE indicator_metadata SET
    category  = 'Output & Growth',
    dimension = 'Inflation & Prices'
WHERE indicator_code IN (
    'WB:FP.CPI.TOTL',
    'WB:FP.CPI.TOTL.ZG',
    'WB:NY.GDP.DEFL.KD.ZG'
);


-- ============================================================
-- 2. WEALTH & INEQUALITY
-- Wie ist Wohlstand verteilt?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Wealth & Inequality',
    dimension = 'Income Distribution'
WHERE indicator_code IN (
    'WB:SI.POV.GINI',
    'WID:gdiincj992:p0p100',
    'WID:gptincj992:p0p100',
    'WID:gcaincj992:p0p100',
    'WID:sdiincj992:p0p50',
    'WID:sdiincj992:p90p100',
    'WID:sdiincj992:p99p100',
    'WID:sptincj992:p0p50',
    'WID:sptincj992:p90p100',
    'WID:sptincj992:p99p100',
    'WID:scaincj992:p0p50',
    'WID:scaincj992:p90p100',
    'WID:scaincj992:p99p100',
    'WID:rdiincj992:p0p100',
    'WID:rptincj992:p0p100',
    'WID:tdiincj992:p90p100',
    'WID:tdiincj992:p99p100',
    'WID:tptincj992:p90p100',
    'WID:tptincj992:p99p100',
    'WID:sfiinct992:p0p50',
    'WID:sfiinct992:p90p100',
    'WID:sfiinct992:p99p100',
    'WID:spllinf992:p0p50',
    'WID:spllinf992:p90p100',
    'WID:spllinf992:p99p100'
);

UPDATE indicator_metadata SET
    category  = 'Wealth & Inequality',
    dimension = 'Wealth Distribution'
WHERE indicator_code IN (
    'WID:ghwealj992:p0p100',
    'WID:rhwealj992:p0p100',
    'WID:shwealj992:p0p50',
    'WID:shwealj992:p90p100',
    'WID:shwealj992:p99p100',
    'WID:thwealj992:p90p100',
    'WID:thwealj992:p99p100'
);

UPDATE indicator_metadata SET
    category  = 'Wealth & Inequality',
    dimension = 'Poverty'
WHERE indicator_code IN (
    'WB:SI.POV.DDAY',
    'WB:SI.POV.GAPS',
    'WB:SI.POV.NAHC',
    'WB:poverty_3_day'
);


-- ============================================================
-- 3. LABOUR & EMPLOYMENT
-- Wie arbeiten die Menschen?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Labour & Employment',
    dimension = 'Labour Market'
WHERE indicator_code IN (
    'WB:SL.TLF.CACT.ZS',
    'WB:SL.UEM.TOTL.FE.ZS',
    'WB:SL.UEM.TOTL.MA.ZS',
    'WB:SL.UEM.1524.ZS',
    'WB:SL.UEM.1524.FE.ZS',
    'WB:SL.UEM.1524.MA.ZS',
    'WB:SL.EMP.1524.SP.ZS',
    'WB:SL.EMP.1524.SP.FE.ZS',
    'WB:SL.EMP.1524.SP.MA.ZS',
    'ILO:EAP_DWAP_SEX_AGE_RT',
    'ILO:SDG_0852_SEX_AGE_RT',
    'ILO:SDG_0831_SEX_ECO_RT',
    'ILO:ILR_TUMT_NOC_RT'
);

UPDATE indicator_metadata SET
    category  = 'Labour & Employment',
    dimension = 'Employment Structure'
WHERE indicator_code IN (
    'WB:SL.AGR.EMPL.ZS',
    'WB:SL.AGR.EMPL.FE.ZS',
    'WB:SL.AGR.EMPL.MA.ZS',
    'WB:SL.IND.EMPL.ZS',
    'WB:SL.IND.EMPL.FE.ZS',
    'WB:SL.IND.EMPL.MA.ZS',
    'WB:SL.SRV.EMPL.ZS',
    'WB:SL.SRV.EMPL.FE.ZS',
    'WB:SL.SRV.EMPL.MA.ZS',
    'WB:SL.EMP.SELF.ZS',
    'WB:SL.EMP.MPYR.ZS',
    'WB:SL.EMP.WORK.ZS',
    'ILO:EMP_2EMP_SEX_STE_NB',
    'ILO:EMP_TEMP_SEX_ECO_NB'
);

UPDATE indicator_metadata SET
    category  = 'Labour & Employment',
    dimension = 'Wages & Hours'
WHERE indicator_code IN (
    'ILO:EAR_EHRA_SEX_NB',
    'ILO:HOW_2TOT_SEX_NB',
    'ILO:HOW_TEMP_SEX_ECO_NB',
    'PWT:avh'
);


-- ============================================================
-- 4. ECONOMIC STRUCTURE
-- Wie ist die Wirtschaft aufgebaut?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Economic Structure',
    dimension = 'Sectoral Composition'
WHERE indicator_code IN (
    'WB:NV.AGR.TOTL.ZS',
    'WB:NV.IND.TOTL.ZS',
    'WB:NV.IND.MANF.ZS',
    'WB:NV.SRV.TOTL.ZS',
    'WB:TX.MNF.TECH.ZS.UN'
);

UPDATE indicator_metadata SET
    category  = 'Economic Structure',
    dimension = 'Trade'
WHERE indicator_code IN (
    'WB:TG.VAL.TOTL.GD.ZS',
    'WB:TM.VAL.MRCH.CD.WT',
    'WB:TX.VAL.MRCH.CD.WT',
    'WB:TM.QTY.MRCH.XD.WD',
    'WB:TX.QTY.MRCH.XD.WD',
    'WB:BN.CAB.XOKA.GD.ZS'
);

UPDATE indicator_metadata SET
    category  = 'Economic Structure',
    dimension = 'Investment & Capital'
WHERE indicator_code IN (
    'WB:NE.GDI.TOTL.CD',
    'WB:NE.GDI.TOTL.ZS',
    'WB:BX.KLT.DINV.CD.WD'
);

UPDATE indicator_metadata SET
    category  = 'Economic Structure',
    dimension = 'Tourism & Remittances'
WHERE indicator_code IN (
    'WB:ST.INT.ARVL',
    'WB:ST.INT.DPRT',
    'WB:ST.INT.RCPT.CD',
    'WB:ST.INT.XPND.CD',
    'WB:BX.TRF.PWKR.CD.DT',
    'WB:BX.TRF.PWKR.DT.GD.ZS',
    'WB:BM.TRF.PWKR.CD.DT'
);


-- ============================================================
-- 5. PUBLIC FINANCE & ENERGY
-- Wie investiert der Staat? Wie ist die Infrastruktur?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Public Finance & Energy',
    dimension = 'Government Finance'
WHERE indicator_code IN (
    'WB:GC.TAX.TOTL.GD.ZS',
    'WB:GC.XPN.TOTL.GD.ZS',
    'WB:GC.DOD.TOTL.GD.ZS',
    'WB:NY.ADJ.AEDU.GN.ZS',
    'WB:DT.ODA.ALLD.CD',
    'WB:DT.ODA.ODAT.GN.ZS',
    'WB:DT.ODA.ODAT.PC.ZS'
);

UPDATE indicator_metadata SET
    category  = 'Public Finance & Energy',
    dimension = 'Energy & Electricity'
WHERE indicator_code IN (
    'WB:EG.ELC.ACCS.ZS',
    'WB:EG.ELC.ACCS.RU.ZS',
    'WB:EG.ELC.ACCS.UR.ZS',
    'WB:EG.ELC.RNEW.ZS',
    'WB:EG.ELC.RNWX.ZS'
);

UPDATE indicator_metadata SET
    category  = 'Public Finance & Energy',
    dimension = 'Infrastructure'
WHERE indicator_code IN (
    'WB:LP.LPI.OVRL.XQ',
    'WB:LP.LPI.INFR.XQ',
    'WB:IS.AIR.PSGR',
    'WB:IS.AIR.GOOD.MT.K1',
    'WB:IS.RRS.TOTL.KM',
    'WB:IS.SHP.GCNW.XQ'
);


-- ============================================================
-- 6. HUMAN DEVELOPMENT
-- Wohlstand jenseits von GDP
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Human Development',
    dimension = 'Human Development'
WHERE indicator_code IN (
    'UNDP:hdi',
    'UNDP:gii',
    'UNDP:gnipc',
    'UNDP:mpi',
    'UNDP:mpi_headcount',
    'UNDP:mpi_intensity',
    'UNDP:mpi_assets',
    'UNDP:mpi_attendance',
    'UNDP:mpi_child_mortality',
    'UNDP:mpi_cooking_fuel',
    'UNDP:mpi_drinking_water',
    'UNDP:mpi_electricity',
    'UNDP:mpi_housing',
    'UNDP:mpi_nutrition',
    'UNDP:mpi_sanitation',
    'UNDP:mpi_schooling'
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
    WHERE im.domain = 'Economy & Infrastructure'
    GROUP BY im.indicator_code, im.category, im.dimension
) sub
GROUP BY category, dimension
ORDER BY category, dimension;
