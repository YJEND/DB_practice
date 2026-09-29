-- 벡터 인덱스 상태.   make sql FILE=labs/06-pgvector/observe.sql
\pset footer off
SELECT count(*) AS rows, pg_size_pretty(pg_table_size('doc_chunks')) AS table_size FROM doc_chunks;

\echo ''
\echo '=== doc_chunks 인덱스 ==='
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) AS size, indexdef
FROM pg_indexes WHERE tablename = 'doc_chunks';

\echo ''
\echo '=== 빌드 진행 중인 인덱스 ==='
SELECT pid, phase, blocks_done, blocks_total, tuples_done, tuples_total
FROM pg_stat_progress_create_index;

\echo ''
\echo '=== 현재 세션 검색 파라미터 ==='
SELECT name, setting FROM pg_settings
WHERE name IN ('hnsw.ef_search', 'ivfflat.probes', 'hnsw.iterative_scan', 'ivfflat.iterative_scan', 'enable_indexscan');
