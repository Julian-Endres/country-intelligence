-- Comtrade nach vollem Lauf (Backlog #88), nur lesend. Vergleichswerte vorher: products 5.696.365, partners 1.200.972.
\echo '=== 1. Gesamt ==='
SELECT (SELECT count(*) FROM trade.trade_products) AS products,
       (SELECT count(*) FROM trade.trade_partners) AS partners;

\echo '=== 2. Je Jahr: Länder und Zeilen (alter Befund: ~160 Länder 2015, 50 Länder 2019) ==='
SELECT year,
       count(DISTINCT iso_numeric) AS laender_products, count(*) AS zeilen_products,
       (SELECT count(DISTINCT iso_numeric) FROM trade.trade_partners p WHERE p.year = t.year) AS laender_partners
FROM trade.trade_products t
GROUP BY year ORDER BY year;

\echo '=== 3. Früher fehlende bzw. lückenhafte Länder: Produktzeilen je Jahr ==='
SELECT year,
       count(*) FILTER (WHERE iso_numeric = '840') AS usa,
       count(*) FILTER (WHERE iso_numeric = '250') AS fra,
       count(*) FILTER (WHERE iso_numeric = '356') AS ind,
       count(*) FILTER (WHERE iso_numeric = '578') AS nor,
       count(*) FILTER (WHERE iso_numeric = '756') AS che,
       count(*) FILTER (WHERE iso_numeric = '276') AS deu,
       count(*) FILTER (WHERE iso_numeric = '076') AS bra,
       count(*) FILTER (WHERE iso_numeric = '068') AS bol
FROM trade.trade_products
GROUP BY year ORDER BY year;
