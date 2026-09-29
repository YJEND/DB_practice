-- id=777 청크의 임베딩과 가장 가까운 청크 10개 (자기 자신 제외), 코사인 거리
SELECT d.id, d.doc_id, d.chunk_no,
       d.embedding <=> q.embedding AS cosine_distance
FROM doc_chunks d,
     (SELECT embedding FROM doc_chunks WHERE id = 777) AS q
WHERE d.id <> 777
ORDER BY d.embedding <=> q.embedding
LIMIT 10;
