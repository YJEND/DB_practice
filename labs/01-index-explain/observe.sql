-- 인덱스 / 통계 / 캐시 상태 관찰용.   make sql FILE=labs/01-index-explain/observe.sql
\echo '=== 인덱스 목록과 크기 ==='
SELECT tablename, indexname,
       pg_size_pretty(pg_relation_size(indexname::regclass)) AS size,
       indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN ('users','products','orders','order_items')
ORDER BY tablename, indexname;

\echo ''
\echo '=== 인덱스 사용 횟수 (idx_scan 이 0 이면 한 번도 안 쓰인 인덱스) ==='
SELECT relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname IN ('users','products','orders','order_items')
ORDER BY relname, indexrelname;

\echo ''
\echo '=== orders 컬럼 통계 (플래너가 보는 값) ==='
SELECT attname, n_distinct, null_frac,
       left(most_common_vals::text, 80)  AS most_common_vals,
       left(most_common_freqs::text, 80) AS most_common_freqs,
       correlation
FROM pg_stats
WHERE tablename = 'orders'
ORDER BY attname;

\echo ''
\echo '=== shared_buffers 안에 올라와 있는 테이블/인덱스 (pg_buffercache) ==='
SELECT c.relname,
       count(*)                         AS buffers,
       pg_size_pretty(count(*) * 8192)  AS cached,
       round(100.0 * count(*) * 8192 / nullif(pg_relation_size(c.oid), 0), 1) AS pct_of_relation
FROM pg_buffercache b
JOIN pg_class c ON b.relfilenode = pg_relation_filenode(c.oid)
WHERE c.relname IN ('users','products','orders','order_items')
   OR c.relname LIKE 'orders_%' OR c.relname LIKE 'users_%' OR c.relname LIKE 'order_items_%'
GROUP BY c.relname, c.oid
ORDER BY count(*) DESC;
