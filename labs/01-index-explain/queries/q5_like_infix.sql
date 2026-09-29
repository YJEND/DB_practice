-- Q5-b. memo 에 특정 ref 코드 조각이 포함된 주문 (중간 일치)
-- 'ref:' 뒤 8자리는 md5(id) 앞부분이라 'a1b' 같은 조각은 소수 행에만 매칭됩니다.
SELECT id, user_id, memo
FROM orders
WHERE memo LIKE '%ref:a1b%';
