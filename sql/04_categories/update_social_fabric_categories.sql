-- ============================================================
-- Social Fabric & Daily Life — Category & Dimension Assignments
-- Stand: 2026-05-28
-- ============================================================

UPDATE indicator_metadata SET category = 'Trust & Institutions', dimension = 'Institutional Trust'
WHERE indicator_code LIKE 'EDELMAN:%';

UPDATE indicator_metadata SET category = 'Civic Life', dimension = 'Civic Engagement & Giving'
WHERE indicator_code LIKE 'CAF_WGI:%';

UPDATE indicator_metadata SET category = 'Wellbeing', dimension = 'Wellbeing & Happiness'
WHERE indicator_code LIKE 'WHR:%';

UPDATE indicator_metadata SET category = 'Basic Services', dimension = 'WASH'
WHERE indicator_code IN ('WHO:WSH_WATER_BASIC', 'WHO:WSH_SANITATION_BASIC');
