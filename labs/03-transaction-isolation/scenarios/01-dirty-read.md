# 01. Dirty Read

A 가 커밋하지 않은 변경을 B 가 볼 수 있는지 확인합니다.

| 순서 | 세션 A | 세션 B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | `UPDATE products SET stock = stock - 30 WHERE id = 1;` | |
| 3 | `SELECT stock FROM products WHERE id = 1;` | |
| 4 | | `BEGIN ISOLATION LEVEL READ UNCOMMITTED;` |
| 5 | | `SHOW transaction_isolation;` |
| 6 | | `SELECT stock FROM products WHERE id = 1;` |
| 7 | `ROLLBACK;` | |
| 8 | | `SELECT stock FROM products WHERE id = 1;` |
| 9 | | `COMMIT;` |

기록: 5번의 출력, 6번과 8번의 값, 3번과 6번이 다른가/같은가.

## 변형
- 4번을 `BEGIN ISOLATION LEVEL READ COMMITTED;` 로 바꿔 반복
- MySQL 에서 같은 순서 (`SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED; START TRANSACTION;`)
