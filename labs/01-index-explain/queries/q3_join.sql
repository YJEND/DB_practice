-- Q3. 지난 7일간 KR 유저의 완료 주문을 카테고리별 매출로 집계 (4개 테이블 조인)
SELECT p.category,
       sum(oi.quantity * oi.unit_price) AS revenue,
       count(DISTINCT o.id)             AS orders
FROM orders o
JOIN users u        ON u.id = o.user_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p     ON p.id = oi.product_id
WHERE o.created_at >= date_trunc('day', now()) - interval '7 days'
  AND o.status = 'completed'
  AND u.country = 'KR'
GROUP BY p.category
ORDER BY revenue DESC
LIMIT 5;
