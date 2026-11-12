-- Kontrollzahlen trade-Schema vor/nach Comtrade-v2-Testlauf (Backlog #88), nur lesend.
SELECT 'products' AS tabelle, iso_numeric, count(*) AS zeilen, round(sum(fob_value) FILTER (WHERE flow_code='X')::numeric/1e9,1) AS export_mrd
FROM trade.trade_products WHERE iso_numeric IN ('068','276','840') AND year BETWEEN 2008 AND 2012 GROUP BY iso_numeric
UNION ALL
SELECT 'partners', iso_numeric, count(*), round(sum(fob_value) FILTER (WHERE flow_code='X')::numeric/1e9,1)
FROM trade.trade_partners WHERE iso_numeric IN ('068','276','840') AND year BETWEEN 2008 AND 2012 GROUP BY iso_numeric
UNION ALL
SELECT 'products gesamt', NULL, count(*), NULL FROM trade.trade_products
UNION ALL
SELECT 'partners gesamt', NULL, count(*), NULL FROM trade.trade_partners
ORDER BY 1, 2;
