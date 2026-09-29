-- 두 상품을 함께 차감: 1번 → 2번 순서 (짝수 워커)
UPDATE products SET stock = stock - 1 WHERE id = 1 RETURNING stock;
UPDATE products SET stock = stock - 1 WHERE id = 2 RETURNING stock;
