-- Q7. 분쟁(disputed) 상태 주문 전체 조회 — 전체의 약 0.01%
-- 비교: status = 'completed' (약 70%) 로 바꿔서도 측정해 보세요.
SELECT id, user_id, total_amount, created_at
FROM orders
WHERE status = 'disputed'
ORDER BY created_at DESC;
