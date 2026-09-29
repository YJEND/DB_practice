-- Q2. 특정 유저의 최근 주문 20건 (마이페이지 주문 목록)
-- user_id = 1 (주문이 몰린 유저) 로도 바꿔서 측정해 보세요:
--   tools/measure.py --query "$(sed 's/4242/1/' labs/01-index-explain/queries/q2_user_orders.sql)" --label q2_whale
SELECT id, status, total_amount, created_at
FROM orders
WHERE user_id = 4242
ORDER BY created_at DESC
LIMIT 20;
