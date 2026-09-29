-- 문서 청크 + 384차원 임베딩.  make sql FILE=labs/06-pgvector/setup.sql VARS="-v n=100000"
\set ON_ERROR_STOP on
\timing on
\if :{?n}
\else
  \set n 100000
\endif
\echo '>>> doc_chunks rows =' :n

-- 행마다 다른 랜덤 벡터를 만들기 위한 VOLATILE 함수 (SELECT 안에 서브쿼리로 쓰면 한 번만 평가돼 전부 같은 벡터가 됨)
CREATE OR REPLACE FUNCTION random_vector(dim int, scale float8 DEFAULT 1.0)
RETURNS vector LANGUAGE sql VOLATILE AS $$
  SELECT array_agg((random() * 2 - 1) * scale)::vector FROM generate_series(1, dim)
$$;

DROP TABLE IF EXISTS doc_chunks;
CREATE TABLE doc_chunks (
  id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doc_id    int  NOT NULL,
  chunk_no  int  NOT NULL,
  content   text NOT NULL,
  embedding vector(384) NOT NULL
);

-- 100개의 중심점. 문서 doc_id 는 (doc_id % 100) 번 중심점 주변에 모임
DROP TABLE IF EXISTS lab06_centroids;
CREATE TABLE lab06_centroids AS
SELECT c, random_vector(384, 1.0) AS vec FROM generate_series(0, 99) AS c;

INSERT INTO doc_chunks (doc_id, chunk_no, content, embedding)
SELECT g / 20,
       g % 20,
       'doc ' || g / 20 || ' chunk ' || g % 20 || ' (cluster ' || (g / 20) % 100 || ')',
       c.vec + random_vector(384, 0.35)
FROM generate_series(1, :n) AS g
JOIN lab06_centroids c ON c.c = (g / 20) % 100;

ANALYZE doc_chunks;

SELECT count(*) AS rows, pg_size_pretty(pg_table_size('doc_chunks')) AS table_size,
       count(DISTINCT embedding) AS distinct_embeddings  -- rows 와 같아야 정상
FROM doc_chunks;
