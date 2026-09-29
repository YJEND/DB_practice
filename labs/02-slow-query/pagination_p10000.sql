-- 주문 목록 10,000 페이지. OFFSET 방식
SELECT id, user_id, status, total_amount, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 199980;
