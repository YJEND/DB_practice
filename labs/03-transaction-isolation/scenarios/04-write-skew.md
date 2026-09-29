# 04. Write Skew

규칙: 쿠폰 `PROMO2026` 은 최대 2번까지만 사용할 수 있다. 현재 1번 사용됨 (`setup.sql`).
두 세션이 동시에 "아직 2번 미만이니 사용 가능" 이라고 판단하고 각자 insert 합니다.

| 순서 | 세션 A | 세션 B |
|---|---|---|
| 1 | `BEGIN ISOLATION LEVEL REPEATABLE READ;` | |
| 2 | | `BEGIN ISOLATION LEVEL REPEATABLE READ;` |
| 3 | `SELECT count(*) FROM lab03_coupon_uses WHERE coupon_code = 'PROMO2026';` | |
| 4 | | `SELECT count(*) FROM lab03_coupon_uses WHERE coupon_code = 'PROMO2026';` |
| 5 | `INSERT INTO lab03_coupon_uses (coupon_code, order_id) VALUES ('PROMO2026', 2);` | |
| 6 | | `INSERT INTO lab03_coupon_uses (coupon_code, order_id) VALUES ('PROMO2026', 3);` |
| 7 | `COMMIT;` | |
| 8 | | `COMMIT;` |
| 9 | `SELECT count(*) FROM lab03_coupon_uses WHERE coupon_code = 'PROMO2026';` | |

기록: 3, 4번의 값, 7·8번의 결과(성공/에러, SQLSTATE, 메시지 전체), 9번의 값 (규칙이 지켜졌는가).

## 변형
- 1, 2번을 `SERIALIZABLE` 로 바꿔 반복. 어느 세션이 어느 단계에서 어떤 에러를 받는가. 에러를 받은 쪽은 무엇을 해야 하는가
- `SERIALIZABLE` 에서 5번과 6번 사이에 A 가 먼저 COMMIT 하도록 순서를 바꾸면 (5 → 7 → 6 → 8)
- 격리 수준을 올리지 않고 이 규칙을 지키는 방법을 최소 두 가지 생각해서 각각 시도 (힌트 없음. 락, 제약, 카운터 컬럼 등)
- 초기화: `make sql FILE=labs/03-transaction-isolation/setup.sql`
