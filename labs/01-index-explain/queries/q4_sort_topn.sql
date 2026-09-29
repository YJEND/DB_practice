-- Q4. 처리 대기(pending) 주문 중 최신 100건 (운영 대시보드)
SELECT id, user_id, total_amount, created_at
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 100;
