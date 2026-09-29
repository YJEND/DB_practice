-- 같은 kNN 에 doc_id 필터를 붙인 버전. 인덱스가 있어도 결과가 10개 미만으로 줄어드는지 확인
SELECT d.id, d.doc_id, d.chunk_no,
       d.embedding <=> q.embedding AS cosine_distance
FROM doc_chunks d,
     (SELECT embedding FROM doc_chunks WHERE id = 777) AS q
WHERE d.id <> 777
  AND d.doc_id < 1000
ORDER BY d.embedding <=> q.embedding
LIMIT 10;
