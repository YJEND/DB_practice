-- orders 의 약 20% 행(id 가 5의 배수)의 memo 에 표식을 덧붙입니다.
-- 실행할 때마다 표식 번호가 올라가므로 몇 번 실행했는지 memo 에 남습니다.
\timing on
SELECT coalesce(max((regexp_match(memo, '\[upd(\d+)\]'))[1]::int), 0) + 1 AS n
FROM orders WHERE id % 5 = 0 AND memo LIKE '%[upd%' \gset
\echo '>>> update round' :n
UPDATE orders
   SET memo = coalesce(memo, '') || ' [upd' || :n || ']'
 WHERE id % 5 = 0;
