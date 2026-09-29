-- Q6. 지난달 주문을 상태별로 집계 (컬럼에 함수를 적용한 조건)
-- 같은 유형: WHERE lower(email) = 'user777@example.com',  WHERE user_id::text = '42'
SELECT status, count(*)
FROM orders
WHERE date_trunc('month', created_at) = date_trunc('month', now() - interval '1 month')
GROUP BY status
ORDER BY count(*) DESC;
