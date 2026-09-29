-- ==================================================================
-- 시드 확인: 행 수 / 크기 / 분포.   make verify
-- ==================================================================
\pset footer off
\echo ''
\echo '=== 테이블 크기 (PK 인덱스 포함) ==='
SELECT c.relname                                   AS "table",
       to_char(s.n_live_tup, 'FM999,999,999,999')   AS approx_rows,
       pg_size_pretty(pg_table_size(c.oid))         AS table_size,
       pg_size_pretty(pg_indexes_size(c.oid))       AS index_size,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c
JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE c.relname IN ('users','products','orders','order_items')
ORDER BY pg_total_relation_size(c.oid) DESC;

\echo ''
\echo '=== 정확한 행 수 ==='
SELECT 'users' AS "table", to_char(count(*), 'FM999,999,999,999') AS rows FROM users
UNION ALL SELECT 'products',    to_char(count(*), 'FM999,999,999,999') FROM products
UNION ALL SELECT 'orders',      to_char(count(*), 'FM999,999,999,999') FROM orders
UNION ALL SELECT 'order_items', to_char(count(*), 'FM999,999,999,999') FROM order_items;

\echo ''
\echo '=== orders.status 분포 (불균형 확인) ==='
SELECT status, to_char(count(*), 'FM999,999,999') AS rows,
       round(100.0 * count(*) / sum(count(*)) OVER (), 3) AS pct
FROM orders GROUP BY status ORDER BY count(*) DESC;

\echo ''
\echo '=== 주문 상위 10 유저 (편향 확인) ==='
SELECT user_id, count(*) AS orders,
       round(100.0 * count(*) / (SELECT count(*) FROM orders), 2) AS pct_of_all
FROM orders GROUP BY user_id ORDER BY count(*) DESC LIMIT 10;

\echo ''
\echo '=== NULL 비율 ==='
SELECT round(100.0 * count(*) FILTER (WHERE coupon_code IS NULL) / count(*), 1) AS coupon_null_pct,
       round(100.0 * count(*) FILTER (WHERE memo IS NULL) / count(*), 1)        AS memo_null_pct,
       round(100.0 * count(*) FILTER (WHERE shipped_at IS NULL) / count(*), 1)  AS shipped_null_pct,
       min(created_at)::date AS oldest_order, max(created_at)::date AS newest_order
FROM orders;

\echo ''
\echo '=== 인덱스 목록 (PK 만 있어야 정상) ==='
SELECT tablename, indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes WHERE schemaname = 'public'
  AND tablename IN ('users','products','orders','order_items')
ORDER BY tablename, indexname;

\echo ''
SELECT 'database total = ' || pg_size_pretty(pg_database_size(current_database())) AS summary;
