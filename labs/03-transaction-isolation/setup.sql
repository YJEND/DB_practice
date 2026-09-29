-- Lab 03 시나리오용 준비. 여러 번 실행해도 됩니다.
-- products 1, 2번 재고를 100 으로 맞추고, write skew 용 쿠폰 사용 테이블을 만듭니다.
UPDATE products SET stock = 100 WHERE id IN (1, 2);

DROP TABLE IF EXISTS lab03_coupon_uses;
CREATE TABLE lab03_coupon_uses (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  coupon_code text   NOT NULL,
  order_id    bigint NOT NULL,
  used_at     timestamptz NOT NULL DEFAULT now()
);
-- 규칙(애플리케이션 레벨): 쿠폰 'PROMO2026' 은 최대 2번까지만 사용 가능. 이미 1번 사용됨.
INSERT INTO lab03_coupon_uses (coupon_code, order_id) VALUES ('PROMO2026', 1);

-- phantom read 용: user 4242 의 pending 주문 수를 미리 확인해 두세요
SELECT count(*) AS pending_orders_of_4242 FROM orders WHERE user_id = 4242 AND status = 'pending';
SELECT id, stock FROM products WHERE id IN (1, 2) ORDER BY id;
