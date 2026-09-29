-- 흔한 버그 패턴: 재고를 읽고, 애플리케이션이 판단한 뒤, 읽은 값 기준으로 씁니다.
-- %(last)s 에는 직전 SELECT 의 첫 컬럼(stock) 이 들어갑니다.
SELECT stock FROM products WHERE id = %(product_id)s;
UPDATE products
   SET stock = %(last)s - 1
 WHERE id = %(product_id)s
   AND %(last)s > 0
RETURNING stock;
