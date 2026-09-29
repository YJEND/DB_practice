-- MySQL(InnoDB) 비교용 스키마. PostgreSQL 쪽 seed/00-schema.sql 과 같은 구조입니다.
-- 컨테이너 최초 기동 시 한 번 실행됩니다. 데이터는 `make seed-mysql` 로 넣습니다.
CREATE TABLE IF NOT EXISTS users (
  id            BIGINT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL,
  name          VARCHAR(100) NOT NULL,
  country       CHAR(2) NOT NULL,
  tier          VARCHAR(20) NOT NULL,
  created_at    DATETIME NOT NULL,
  last_login_at DATETIME NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id         BIGINT PRIMARY KEY,
  sku        VARCHAR(32) NOT NULL,
  name       VARCHAR(100) NOT NULL,
  category   VARCHAR(32) NOT NULL,
  price      DECIMAL(10,2) NOT NULL,
  stock      INT NOT NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS orders (
  id           BIGINT PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  status       VARCHAR(20) NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL,
  coupon_code  VARCHAR(16) NULL,
  memo         VARCHAR(255) NULL,
  created_at   DATETIME NOT NULL,
  shipped_at   DATETIME NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_items (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_id   BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  quantity   INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL
) ENGINE=InnoDB;
