-- Q1-b. 같은 쿼리, 범위만 30일로. Q1 에 만든 인덱스가 여기서도 쓰이는지 비교
SELECT count(*) AS orders, sum(total_amount) AS revenue
FROM orders
WHERE created_at >= date_trunc('day', now()) - interval '30 days'
  AND created_at <  date_trunc('day', now());
