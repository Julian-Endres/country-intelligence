-- =========================================
-- ROLLBACK: WB Categories zurück auf Original
-- =========================================

UPDATE indicator_metadata SET category = 'Climate Change'
WHERE indicator_code IN (
    'WB:SP.URB.TOTL',
    'WB:SP.URB.TOTL.IN.ZS',
    'WB:SP.URB.GROW',
    'WB:SP.POP.GROW'
);

UPDATE indicator_metadata SET category = 'Financial Sector'
WHERE indicator_code IN (
    'WB:SM.POP.TOTL',
    'WB:SM.POP.TOTL.ZS',
    'WB:SM.POP.NETM'
);

UPDATE indicator_metadata SET category = 'Education'
WHERE indicator_code IN (
    'WB:SL.UEM.TOTL.MA.ZS',
    'WB:SL.UEM.TOTL.FE.ZS',
    'WB:SL.TLF.CACT.ZS',
    'WB:SP.POP.1564.TO.ZS',
    'WB:SP.POP.0014.TO.ZS'
);

-- Verification
SELECT indicator_code, name, category, domain, dimension
FROM indicator_metadata
ORDER BY category, indicator_code;
