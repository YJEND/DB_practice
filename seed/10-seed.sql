-- ==================================================================
-- generate_series 기반 시드.  psql 변수 scale = small | large
--   make seed-small   -> users 10만 / products 5천 / orders 100만 / items 약 220만
--   make seed-large   -> users 100만 / products 5만 / orders 1,000만 / items 약 2,200만
-- 숫자를 직접 바꾸고 싶으면 아래 \set 값을 수정하세요.
-- ==================================================================
\set ON_ERROR_STOP on
\timing on

\if :{?scale}
\else
  \set scale small
\endif

SELECT :'scale' = 'large' AS is_large \gset
\if :is_large
  \set n_users    1000000
  \set n_products 50000
  \set n_orders   10000000
\else
  \set n_users    100000
  \set n_products 5000
  \set n_orders   1000000
\endif
\echo '>>> scale =' :scale '  users =' :n_users '  products =' :n_products '  orders =' :n_orders

-- 시드 세션에서만 적용되는 속도 옵션 (서버 설정은 그대로)
SET synchronous_commit = off;          -- 커밋마다 fsync 대기 안 함
SET maintenance_work_mem = '1GB';      -- PK 인덱스 빌드용
SET max_parallel_maintenance_workers = 4;

-- ------------------------------------------------------------------
-- users: KR 편중 country, tier 불균형, last_login_at 30% NULL
-- ------------------------------------------------------------------
\echo '>>> users'
INSERT INTO users (id, email, name, country, tier, created_at, last_login_at)
SELECT r.g,
       'user' || r.g || '@example.com',
       'user_' || r.g,
       (ARRAY['KR','KR','KR','KR','KR','KR','KR','US','US','JP','JP','DE','GB','FR','CA','BR'])[1 + floor(random() * 16)::int],
       CASE WHEN r.t < 0.85 THEN 'free' WHEN r.t < 0.97 THEN 'pro' ELSE 'enterprise' END,
       now() - random() * interval '730 days',
       CASE WHEN random() < 0.30 THEN NULL ELSE now() - random() * interval '90 days' END
FROM (SELECT g, random() AS t FROM generate_series(1, :n_users) AS g) AS r;

-- ------------------------------------------------------------------
-- products: 10개 카테고리, 재고 0~999
-- ------------------------------------------------------------------
\echo '>>> products'
INSERT INTO products (id, sku, name, category, price, stock, created_at)
SELECT g,
       'SKU-' || lpad(g::text, 8, '0'),
       'Product ' || g,
       (ARRAY['electronics','books','fashion','home','beauty','sports','toys','food','office','pet'])[1 + (g % 10)],
       round((5 + random() * 495)::numeric, 2),
       floor(random() * 1000)::int,
       now() - random() * interval '730 days'
FROM generate_series(1, :n_products) AS g;

-- ------------------------------------------------------------------
-- orders
--   user_id : 90% 는 power(random(),4) 로 작은 id 에 집중, 10% 는 균등
--             -> 상위 1% 유저가 주문의 약 28%, 상위 5% 가 약 43%, 1번 유저 혼자 2~5%
--   status  : 70 / 15 / 10 / 4.9 / 0.09 / 0.01 (%)
--   created_at : 최근 365일 균등
-- ------------------------------------------------------------------
\echo '>>> orders'
INSERT INTO orders (id, user_id, status, total_amount, coupon_code, memo, created_at, shipped_at)
SELECT y.g,
       CASE WHEN y.r_u < 0.10 THEN 1 + floor(random() * :n_users)::bigint
            ELSE 1 + floor(power(random(), 4) * :n_users)::bigint END,
       x.status,
       round((5 + random() * 495)::numeric, 2),
       CASE WHEN random() < 0.10 THEN 'CPN' || lpad(floor(random() * 10000)::int::text, 4, '0') END,
       CASE WHEN random() < 0.30
            THEN (ARRAY['please leave at door','call before delivery','gift wrap requested',
                        'fragile item inside','deliver after 6pm','no contact delivery',
                        'ring the bell twice','leave with neighbor'])[1 + floor(random() * 8)::int]
                 || ' ref:' || substr(md5(y.g::text), 1, 8)
       END,
       y.created_at,
       CASE WHEN x.status IN ('shipped','completed')
            THEN LEAST(now(), y.created_at + interval '1 day' * (1 + random() * 5)) END
FROM (
  -- random() 을 서브쿼리의 SELECT 목록에 두면 행마다 한 번씩 평가되고, 바깥에서 여러 번 참조해도 같은 값입니다.
  -- (LATERAL (SELECT random()) 처럼 바깥 행을 참조하지 않는 서브쿼리는 한 번만 평가되어 전 행이 같은 값이 됩니다)
  SELECT g,
         random() AS r_u,
         random() AS r_s,
         now() - random() * interval '365 days' AS created_at
  FROM generate_series(1, :n_orders) AS g
) AS y
CROSS JOIN LATERAL (
  SELECT CASE WHEN y.r_s < 0.70   THEN 'completed'
              WHEN y.r_s < 0.85   THEN 'shipped'
              WHEN y.r_s < 0.95   THEN 'pending'
              WHEN y.r_s < 0.999  THEN 'cancelled'
              WHEN y.r_s < 0.9999 THEN 'refunded'
              ELSE 'disputed' END AS status
) AS x;

-- ------------------------------------------------------------------
-- order_items: 주문당 1~5개 (평균 약 2.2개), 인기 상품(작은 id) 편중, 수량은 대부분 1
-- ------------------------------------------------------------------
\echo '>>> order_items'
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id,
       1 + floor(power(random(), 2) * :n_products)::bigint,
       1 + floor(power(random(), 3) * 5)::int,
       round((5 + random() * 495)::numeric, 2)
FROM (
  SELECT g AS id, 1 + floor(power(random(), 2) * 5)::int AS n_items
  FROM generate_series(1, :n_orders) AS g
) AS o
CROSS JOIN LATERAL generate_series(1, o.n_items) AS i;

-- ------------------------------------------------------------------
-- PK 는 데이터 적재 후 생성 (훨씬 빠름). identity 시퀀스도 현재 max 로 맞춤
-- ------------------------------------------------------------------
\echo '>>> primary keys'
ALTER TABLE users       ADD PRIMARY KEY (id);
ALTER TABLE products    ADD PRIMARY KEY (id);
ALTER TABLE orders      ADD PRIMARY KEY (id);
ALTER TABLE order_items ADD PRIMARY KEY (id);

SELECT setval(pg_get_serial_sequence('users',       'id'), (SELECT max(id) FROM users));
SELECT setval(pg_get_serial_sequence('products',    'id'), (SELECT max(id) FROM products));
SELECT setval(pg_get_serial_sequence('orders',      'id'), (SELECT max(id) FROM orders));
SELECT setval(pg_get_serial_sequence('order_items', 'id'), (SELECT max(id) FROM order_items));

\echo '>>> analyze'
ANALYZE users;
ANALYZE products;
ANALYZE orders;
ANALYZE order_items;

-- 시드 자체가 pg_stat_statements 를 오염시키지 않도록 초기화
SELECT pg_stat_statements_reset();
\echo '>>> done'
