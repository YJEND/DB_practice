-- MySQL(InnoDB) 비교용 small 시드: users 10만 / products 5천 / orders 100만 / items 약 220만
-- generate_series 가 없으므로 digits 테이블의 cross join 으로 연번을 만듭니다.
-- (TEMPORARY 테이블은 한 쿼리에서 두 번 참조할 수 없어서 일반 테이블을 만들었다가 끝에 지웁니다)
-- 실행: make seed-mysql   (수 분 소요)
SET SESSION unique_checks = 0;
SET SESSION foreign_key_checks = 0;

TRUNCATE order_items; TRUNCATE orders; TRUNCATE products; TRUNCATE users;

DROP TABLE IF EXISTS lab_digits;
CREATE TABLE lab_digits (n TINYINT PRIMARY KEY);
INSERT INTO lab_digits VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);

-- 1..1,000,000 연번
DROP TABLE IF EXISTS lab_seq;
CREATE TABLE lab_seq (n INT PRIMARY KEY) ENGINE=InnoDB;
INSERT INTO lab_seq
SELECT 1 + a.n + b.n*10 + c.n*100 + d1.n*1000 + e.n*10000 + f.n*100000
FROM lab_digits a, lab_digits b, lab_digits c, lab_digits d1, lab_digits e, lab_digits f;

INSERT INTO users (id, email, name, country, tier, created_at, last_login_at)
SELECT n, CONCAT('user', n, '@example.com'), CONCAT('user_', n),
       ELT(1 + FLOOR(RAND()*16), 'KR','KR','KR','KR','KR','KR','KR','US','US','JP','JP','DE','GB','FR','CA','BR'),
       CASE WHEN (@t := RAND()) < 0.85 THEN 'free' WHEN @t < 0.97 THEN 'pro' ELSE 'enterprise' END,
       NOW() - INTERVAL FLOOR(RAND()*730) DAY,
       IF(RAND() < 0.30, NULL, NOW() - INTERVAL FLOOR(RAND()*90) DAY)
FROM lab_seq WHERE n <= 100000;

INSERT INTO products (id, sku, name, category, price, stock, created_at)
SELECT n, CONCAT('SKU-', LPAD(n, 8, '0')), CONCAT('Product ', n),
       ELT(1 + (n % 10), 'electronics','books','fashion','home','beauty','sports','toys','food','office','pet'),
       ROUND(5 + RAND()*495, 2), FLOOR(RAND()*1000), NOW() - INTERVAL FLOOR(RAND()*730) DAY
FROM lab_seq WHERE n <= 5000;

INSERT INTO orders (id, user_id, status, total_amount, coupon_code, memo, created_at, shipped_at)
SELECT n,
       IF(RAND() < 0.10, 1 + FLOOR(RAND()*100000), 1 + FLOOR(POW(RAND(),4)*100000)),
       @s := CASE WHEN (@r := RAND()) < 0.70 THEN 'completed' WHEN @r < 0.85 THEN 'shipped'
                  WHEN @r < 0.95 THEN 'pending' WHEN @r < 0.999 THEN 'cancelled'
                  WHEN @r < 0.9999 THEN 'refunded' ELSE 'disputed' END,
       ROUND(5 + RAND()*495, 2),
       IF(RAND() < 0.10, CONCAT('CPN', LPAD(FLOOR(RAND()*10000), 4, '0')), NULL),
       IF(RAND() < 0.30, CONCAT(ELT(1 + FLOOR(RAND()*8), 'please leave at door','call before delivery','gift wrap requested',
                                    'fragile item inside','deliver after 6pm','no contact delivery','ring the bell twice','leave with neighbor'),
                                ' ref:', LEFT(MD5(n), 8)), NULL),
       @c := NOW() - INTERVAL FLOOR(RAND()*365*24*60) MINUTE,
       IF(@s IN ('shipped','completed'), LEAST(NOW(), @c + INTERVAL FLOOR(24 + RAND()*120) HOUR), NULL)
FROM lab_seq WHERE n <= 1000000;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.n, 1 + FLOOR(POW(RAND(),2)*5000), 1 + FLOOR(POW(RAND(),3)*5), ROUND(5 + RAND()*495, 2)
FROM (SELECT n, 1 + FLOOR(POW(RAND(),2)*5) AS n_items FROM lab_seq WHERE n <= 1000000) o
JOIN lab_digits d ON d.n < o.n_items;

DROP TABLE lab_seq;
DROP TABLE lab_digits;
ANALYZE TABLE users, products, orders, order_items;
