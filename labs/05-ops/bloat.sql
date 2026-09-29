-- orders 테이블의 bloat 상태.   make sql FILE=labs/05-ops/bloat.sql
\pset footer off
\echo '=== 크기 / 튜플 통계 (pg_stat_user_tables) ==='
SELECT relname,
       pg_size_pretty(pg_table_size(relid))   AS table_size,
       pg_size_pretty(pg_indexes_size(relid)) AS index_size,
       n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
       n_tup_upd, n_tup_hot_upd,
       round(100.0 * n_tup_hot_upd / nullif(n_tup_upd, 0), 1) AS hot_pct,
       last_vacuum, last_autovacuum, vacuum_count, autovacuum_count
FROM pg_stat_user_tables
WHERE relname = 'orders';

\echo ''
\echo '=== pgstattuple (실제 페이지를 읽어 계산, 큰 테이블이면 수 초) ==='
SELECT pg_size_pretty(table_len) AS table_len,
       tuple_count, pg_size_pretty(tuple_len) AS live_len, tuple_percent,
       dead_tuple_count, pg_size_pretty(dead_tuple_len) AS dead_len, dead_tuple_percent,
       pg_size_pretty(free_space) AS free_space, free_percent
FROM pgstattuple('orders');

\echo ''
\echo '=== PK 인덱스 상태 (pgstatindex) ==='
SELECT pg_size_pretty(pg_relation_size('orders_pkey')) AS index_size,
       tree_level, leaf_pages, empty_pages, deleted_pages,
       avg_leaf_density, leaf_fragmentation
FROM pgstatindex('orders_pkey');

\echo ''
\echo '=== 테이블 저장 옵션 / autovacuum 설정 ==='
SELECT relname, reloptions FROM pg_class WHERE relname = 'orders';
SELECT name, setting FROM pg_settings
WHERE name IN ('autovacuum', 'autovacuum_vacuum_scale_factor', 'autovacuum_vacuum_threshold',
               'autovacuum_naptime', 'autovacuum_vacuum_cost_delay', 'autovacuum_vacuum_cost_limit');

\echo ''
\echo '=== 지금 돌고 있는 (auto)vacuum ==='
SELECT p.pid, a.application_name, p.relid::regclass, p.phase,
       p.heap_blks_scanned, p.heap_blks_total,
       round(100.0 * p.heap_blks_scanned / nullif(p.heap_blks_total, 0), 1) AS pct
FROM pg_stat_progress_vacuum p JOIN pg_stat_activity a USING (pid);
