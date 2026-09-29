SELECT table_name, table_rows AS approx_rows,
       ROUND((data_length)/1024/1024, 1) AS data_mb, ROUND((index_length)/1024/1024, 1) AS index_mb
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name IN ('users','products','orders','order_items')
ORDER BY data_length DESC;
SELECT status, COUNT(*) AS rows_, ROUND(100*COUNT(*)/(SELECT COUNT(*) FROM orders), 3) AS pct FROM orders GROUP BY status ORDER BY rows_ DESC;
