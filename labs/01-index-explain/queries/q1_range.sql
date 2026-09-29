-- Q1. 범위 조회: 어제 하루 동안 들어온 주문 건수와 매출
-- (시드의 created_at 은 실행 시점 기준 최근 365일에 균등 분포)
SELECT count(*) AS orders, sum(total_amount) AS revenue
FROM orders
WHERE created_at >= date_trunc('day', now()) - interval '1 day'
  AND created_at <  date_trunc('day', now());
