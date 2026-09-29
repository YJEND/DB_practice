-- 두 상품을 함께 차감: 2번 → 1번 순서 (홀수 워커)
UPDATE products SET stock = stock - 1 WHERE id = 2 RETURNING stock;
UPDATE products SET stock = stock - 1 WHERE id = 1 RETURNING stock;
