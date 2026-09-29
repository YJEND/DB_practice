-- pg_stat_statements 를 다섯 가지 기준으로 정렬.   make sql FILE=labs/02-slow-query/pgss_top.sql
-- 초기화: SELECT pg_stat_statements_reset();
\pset footer off
\echo '=== 1) 총 실행 시간 기준 (서비스 전체 부하 기여도) ==='
SELECT queryid, calls, round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms, rows,
       shared_blks_hit, shared_blks_read,
       left(regexp_replace(query, '\s+', ' ', 'g'), 70) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query NOT ILIKE '%pg_stat_statements%' AND query NOT ILIKE 'EXPLAIN%'
ORDER BY total_exec_time DESC LIMIT 10;

\echo ''
\echo '=== 2) 평균 실행 시간 기준 (한 번이 오래 걸리는 쿼리) ==='
SELECT queryid, calls, round(mean_exec_time::numeric, 2) AS mean_ms,
       round(max_exec_time::numeric, 2) AS max_ms, round(stddev_exec_time::numeric, 2) AS stddev_ms,
       left(regexp_replace(query, '\s+', ' ', 'g'), 70) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query NOT ILIKE '%pg_stat_statements%' AND query NOT ILIKE 'EXPLAIN%'
ORDER BY mean_exec_time DESC LIMIT 10;

\echo ''
\echo '=== 3) 호출 수 기준 (N+1 의심) ==='
SELECT queryid, calls, round(mean_exec_time::numeric, 3) AS mean_ms,
       round(total_exec_time::numeric, 1) AS total_ms,
       left(regexp_replace(query, '\s+', ' ', 'g'), 70) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query NOT ILIKE '%pg_stat_statements%' AND query NOT ILIKE 'EXPLAIN%'
ORDER BY calls DESC LIMIT 10;

\echo ''
\echo '=== 4) 디스크 읽기 기준 (캐시 미스, I/O 부하) ==='
SELECT queryid, calls, shared_blks_read, shared_blks_hit,
       round(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct,
       temp_blks_written,
       left(regexp_replace(query, '\s+', ' ', 'g'), 60) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query NOT ILIKE '%pg_stat_statements%' AND query NOT ILIKE 'EXPLAIN%'
ORDER BY shared_blks_read DESC LIMIT 10;

\echo ''
\echo '=== 5) 반환 행 수 기준 (너무 많이 가져오는 쿼리) ==='
SELECT queryid, calls, rows, round(rows::numeric / nullif(calls, 0), 1) AS rows_per_call,
       left(regexp_replace(query, '\s+', ' ', 'g'), 70) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query NOT ILIKE '%pg_stat_statements%' AND query NOT ILIKE 'EXPLAIN%'
ORDER BY rows DESC LIMIT 10;

\echo ''
SELECT 'total statements tracked = ' || count(*) || ',  total calls = ' || sum(calls) FROM pg_stat_statements;
