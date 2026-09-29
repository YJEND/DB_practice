-- 지금 누가 무엇을 기다리는지.   make sql FILE=labs/04-locks/locks.sql
\pset footer off
\echo '=== 대기 중인 세션과 그를 막고 있는 세션 ==='
SELECT a.pid, a.application_name AS app, a.state,
       a.wait_event_type || '/' || a.wait_event AS wait,
       pg_blocking_pids(a.pid) AS blocked_by,
       now() - a.xact_start AS xact_age,
       left(a.query, 60) AS query
FROM pg_stat_activity a
WHERE a.datname = current_database()
  AND a.pid <> pg_backend_pid()
  AND a.backend_type = 'client backend'
ORDER BY a.xact_start NULLS LAST;

\echo ''
\echo '=== 잡혀 있거나 대기 중인 락 (테이블/행 단위) ==='
SELECT l.pid, a.application_name AS app, l.locktype, l.mode, l.granted,
       coalesce(c.relname, l.locktype) AS relation,
       l.transactionid
FROM pg_locks l
LEFT JOIN pg_class c ON c.oid = l.relation
LEFT JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.pid <> pg_backend_pid()
  AND (c.relname IS NULL OR c.relname NOT LIKE 'pg_%')
ORDER BY l.granted, l.pid, l.locktype;

\echo ''
\echo '=== 누적 데드락 수 (pg_stat_database) ==='
SELECT datname, deadlocks, conflicts FROM pg_stat_database WHERE datname = current_database();
