-- Q5-a. memo 가 'gift wrap' 으로 시작하는 주문 (전방 일치)
SELECT id, user_id, memo
FROM orders
WHERE memo LIKE 'gift wrap%'
ORDER BY id
LIMIT 50;
