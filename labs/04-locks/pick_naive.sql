-- 작업 큐에서 하나 집기 (락 없음). 마지막 문장의 첫 컬럼이 집은 작업 id 입니다.
SELECT id FROM lab04_jobs WHERE status = 'pending' ORDER BY id LIMIT 1;
UPDATE lab04_jobs SET status = 'processing', locked_by = %(worker)s WHERE id = %(last)s RETURNING id;
