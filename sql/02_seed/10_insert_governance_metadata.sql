-- Governance indicators metadata (World Governance Indicators, WB source=3)
-- Run BEFORE load_governance.py

INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension) VALUES

-- World Governance Indicators (WGI)
('WB:RL.EST', 'Rule of Law: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Rule of law'),
('WB:RL.PER.RNK', 'Rule of Law: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Rule of law'),
('WB:GE.EST', 'Government Effectiveness: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Government effectiveness'),
('WB:GE.PER.RNK', 'Government Effectiveness: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Government effectiveness'),
('WB:RQ.EST', 'Regulatory Quality: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Regulatory quality'),
('WB:RQ.PER.RNK', 'Regulatory Quality: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Regulatory quality'),
('WB:CC.EST', 'Control of Corruption: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Corruption'),
('WB:CC.PER.RNK', 'Control of Corruption: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Corruption'),
('WB:VA.EST', 'Voice and Accountability: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Voice & accountability'),
('WB:VA.PER.RNK', 'Voice and Accountability: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Voice & accountability'),
('WB:PV.EST', 'Political Stability and Absence of Violence: Estimate', 1, 'Public Sector', 'Politics & Governance', 'Political stability'),
('WB:PV.PER.RNK', 'Political Stability and Absence of Violence: Percentile Rank', 1, 'Public Sector', 'Politics & Governance', 'Political stability'),

-- ODA
('WB:DT.ODA.ALLD.CD', 'Net official development assistance and official aid received (current US$)', 1, 'Aid Effectiveness', 'Politics & Governance', 'Aid & ODA'),
('WB:DT.ODA.ODAT.GN.ZS', 'Net ODA received (% of GNI)', 1, 'Aid Effectiveness', 'Politics & Governance', 'Aid & ODA'),
('WB:DT.ODA.ODAT.PC.ZS', 'Net ODA received per capita (current US$)', 1, 'Aid Effectiveness', 'Politics & Governance', 'Aid & ODA')

ON CONFLICT (indicator_code) DO NOTHING;
