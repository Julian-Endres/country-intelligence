-- Comtrade v2 Trockenlauf 11.11.2026 gegen WB:TX.VAL.MRCH.CD.WT (Backlog #88), nur lesend.
-- Comtrade-Exporte (Mrd USD) aus logs/comtrade_v2_2026-11-11.log, Pipeline p1.
WITH ct(iso_numeric, jahr, export_mrd) AS (
  SELECT '068','2008',7.1    UNION ALL SELECT '068','2009',5.5    UNION ALL SELECT '068','2010',7.1
  UNION ALL SELECT '068','2011',9.2    UNION ALL SELECT '068','2012',12.0
  UNION ALL SELECT '276','2008',1457.5 UNION ALL SELECT '276','2009',1125.8 UNION ALL SELECT '276','2010',1267.7
  UNION ALL SELECT '276','2011',1483.8 UNION ALL SELECT '276','2012',1410.1
  UNION ALL SELECT '840','2008',1299.9 UNION ALL SELECT '840','2009',1056.7 UNION ALL SELECT '840','2010',1278.1
  UNION ALL SELECT '840','2011',1481.7 UNION ALL SELECT '840','2012',1544.9
)
SELECT ct.iso_numeric, ct.jahr, ct.export_mrd AS comtrade_mrd,
       round((i.value / 1e9)::numeric, 1) AS wb_mrd,
       round((ct.export_mrd / (i.value / 1e9))::numeric, 2) AS quote
FROM ct
LEFT JOIN indicators i
  ON i.iso_numeric = ct.iso_numeric AND i.time_period = ct.jahr
 AND i.indicator_code = 'WB:TX.VAL.MRCH.CD.WT'
ORDER BY ct.iso_numeric, ct.jahr;
