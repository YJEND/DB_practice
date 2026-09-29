# 02. Non-repeatable Read

한 트랜잭션 안에서 같은 행을 두 번 읽는 사이에 다른 세션이 커밋합니다.

| 순서 | 세션 A | 세션 B |
|---|---|---|
| 1 | | `BEGIN ISOLATION LEVEL READ COMMITTED;` |
| 2 | | `SELECT stock FROM products WHERE id = 1;` |
| 3 | `BEGIN;` | |
| 4 | `UPDATE products SET stock = stock - 10 WHERE id = 1;` | |
| 5 | | `SELECT stock FROM products WHERE id = 1;` |
| 6 | `COMMIT;` | |
| 7 | | `SELECT stock FROM products WHERE id = 1;` |
| 8 | | `COMMIT;` |

기록: 2, 5, 7번의 값. 5번이 대기했는지.

## 변형
- 1번을 `BEGIN ISOLATION LEVEL REPEATABLE READ;` 로 바꿔 반복. 7번 이후 B 가 `COMMIT` 하고 다시 `SELECT` 하면?
- REPEATABLE READ 에서 2번 대신 `SELECT txid_current();` 를 먼저 실행한 뒤 진행하면 결과가 달라지는가 (스냅샷이 잡히는 시점)
- 원상복구: `UPDATE products SET stock = 100 WHERE id = 1;`
