-- 컨테이너 최초 기동(볼륨이 비어 있을 때) 한 번만 실행됩니다.
-- 볼륨을 지우고(make reset) 다시 올리면 다시 실행됩니다.
CREATE EXTENSION IF NOT EXISTS vector;              -- 06-pgvector
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- 02-slow-query
CREATE EXTENSION IF NOT EXISTS pgstattuple;         -- 05-ops: dead tuple / bloat 정밀 측정
CREATE EXTENSION IF NOT EXISTS pg_buffercache;      -- 01: 어떤 테이블이 shared_buffers 에 올라와 있는지
