-- ============================================================
-- Politics & Governance — Category & Dimension Assignments
-- Basiert auf echten indicator_codes aus der DB
-- Stand: 2026-05-28
-- ============================================================
-- 5 Categories:
--   Democracy & Elections
--   Rule of Law & Rights
--   State Capacity & Institutions
--   Security & Conflict
--   Political Economy


-- ============================================================
-- 1. DEMOCRACY & ELECTIONS
-- Was ist das Regime? Wie frei sind Wahlen? Wie stark die Teilhabe?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Democracy & Elections',
    dimension = 'Democracy & Regime'
WHERE indicator_code IN (
    'POLITY5:polity2',
    'POLITY5:democ',
    'POLITY5:autoc',
    'POLITY5:durable',
    'POLITY5:polcomp',
    'POLITY5:xconst',
    'VDEM:v2x_polyarchy',
    'VDEM:v2x_polyarchy_stock',
    'VDEM:v2x_libdem',
    'VDEM:v2x_libdem_stock',
    'VDEM:v2x_egaldem',
    'VDEM:v2x_egaldem_stock',
    'VDEM:v2x_partipdem',
    'VDEM:v2x_partipdem_stock',
    'VDEM:v2x_delibdem',
    'VDEM:v2x_delibdem_stock',
    'VDEM:v2x_regime',
    'VDEM:v2x_regime_amb'
);

UPDATE indicator_metadata SET
    category  = 'Democracy & Elections',
    dimension = 'Electoral Integrity'
WHERE indicator_code IN (
    'VDEM:v2x_elecreg',
    'VDEM:v2x_elecoff',
    'VDEM:v2x_electoral_integrity',
    'VDEM:v2x_EDcomp_thick',
    'VDEM:v2x_suffr',
    'WB:SG.GEN.PARL.ZS'
);

UPDATE indicator_metadata SET
    category  = 'Democracy & Elections',
    dimension = 'Political Participation'
WHERE indicator_code IN (
    'VDEM:v2x_partip',
    'VDEM:v2x_api',
    'VDEM:v2x_mpi',
    'VDEM:v2x_cspart',
    'VDEM:v2x_frassoc_thick'
);

UPDATE indicator_metadata SET
    category  = 'Democracy & Elections',
    dimension = 'Civil & Political Rights'
WHERE indicator_code IN (
    'FH:PR',
    'FH:CL',
    'FH:STATUS'
);


-- ============================================================
-- 2. RULE OF LAW & RIGHTS
-- Funktioniert der Rechtsstaat? Korruption? Bürgerrechte?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Rule of Law & Rights',
    dimension = 'Rule of Law'
WHERE indicator_code IN (
    'WB:RL.EST',
    'WB:RL.PER.RNK',
    'VDEM:v2x_rule',
    'VDEM:v2x_jucon',
    'VDEM:v2x_liberal',
    'VDEM:v2x_accountability',
    'VDEM:v2x_diagacc',
    'VDEM:v2x_veracc',
    'VDEM:v2x_horacc',
    'VDEM:v2x_hosabort',
    'VDEM:v2x_hosinter',
    'VDEM:v2x_legabort'
);

UPDATE indicator_metadata SET
    category  = 'Rule of Law & Rights',
    dimension = 'Corruption'
WHERE indicator_code IN (
    'TI:CPI',
    'WB:CC.EST',
    'WB:CC.PER.RNK',
    'VDEM:v2x_corr',
    'VDEM:v2x_execorr',
    'VDEM:v2x_pubcorr',
    'VDEM:v2x_neopat'
);

UPDATE indicator_metadata SET
    category  = 'Rule of Law & Rights',
    dimension = 'Civil Liberties'
WHERE indicator_code IN (
    'VDEM:v2x_civlib',
    'VDEM:v2x_clphy',
    'VDEM:v2x_clpol',
    'VDEM:v2x_clpriv',
    'VDEM:v2x_freexp',
    'VDEM:v2x_freexp_altinf'
);

UPDATE indicator_metadata SET
    category  = 'Rule of Law & Rights',
    dimension = 'Gender & Political Equality'
WHERE indicator_code IN (
    'VDEM:v2x_gender',
    'VDEM:v2x_gencs',
    'VDEM:v2x_genpp',
    'VDEM:v2x_gencl',
    'VDEM:v2x_egal'
);


-- ============================================================
-- 3. STATE CAPACITY & INSTITUTIONS
-- Kann der Staat liefern? Ist er stabil? Medienfreiheit?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'State Capacity & Institutions',
    dimension = 'State Fragility'
WHERE indicator_code LIKE 'FSI:%';

UPDATE indicator_metadata SET
    category  = 'State Capacity & Institutions',
    dimension = 'Press Freedom'
WHERE indicator_code LIKE 'RSF:%';

UPDATE indicator_metadata SET
    category  = 'State Capacity & Institutions',
    dimension = 'Military & Defence'
WHERE indicator_code = 'SIPRI:milex_gdp';

UPDATE indicator_metadata SET
    category  = 'State Capacity & Institutions',
    dimension = 'Government Effectiveness'
WHERE indicator_code IN (
    'WB:GE.EST',
    'WB:GE.PER.RNK',
    'WB:RQ.EST',
    'WB:RQ.PER.RNK',
    'WB:PV.EST',
    'WB:PV.PER.RNK',
    'WB:VA.EST',
    'WB:VA.PER.RNK',
    'VDEM:v2x_ex_confidence',
    'VDEM:v2x_ex_direlect',
    'VDEM:v2x_ex_hereditary',
    'VDEM:v2x_ex_military',
    'VDEM:v2x_ex_party',
    'VDEM:v2x_divparctrl',
    'VDEM:v2x_feduni'
);


-- ============================================================
-- 4. SECURITY & CONFLICT
-- Wie gefährlich ist das Land? Kriminalität, organisiertes Verbrechen?
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Security & Conflict',
    dimension = 'Homicide & Crime'
WHERE indicator_code LIKE 'UNODC:%';

UPDATE indicator_metadata SET
    category  = 'Security & Conflict',
    dimension = 'Organized Crime'
WHERE indicator_code LIKE 'GITOC:%';


-- ============================================================
-- 5. POLITICAL ECONOMY
-- Entwicklungshilfe, internationale Abhängigkeiten
-- ============================================================

UPDATE indicator_metadata SET
    category  = 'Political Economy',
    dimension = 'Aid & Development Finance'
WHERE indicator_code LIKE 'WB:DT.ODA%';


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
    WHERE im.domain = 'Politics & Governance'
    GROUP BY im.indicator_code, im.category, im.dimension
) sub
GROUP BY category, dimension
ORDER BY category, dimension;
