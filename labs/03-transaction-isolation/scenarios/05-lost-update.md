# 05. Lost Update (보너스)

두 세션이 같은 값을 읽고, 각자 계산해서 쓰면 한쪽 갱신이 사라집니다. 재고 차감의 가장 흔한 버그입니다.

| 순서 | 세션 A | 세션 B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | `SELECT stock FROM products WHERE id = 2;` | |
| 3 | | `BEGIN;` |
| 4 | | `SELECT stock FROM products WHERE id = 2;` |
| 5 | `UPDATE products SET stock = <2번에서 읽은 값> - 1 WHERE id = 2;` | |
| 6 | `COMMIT;` | |
| 7 | | `UPDATE products SET stock = <4번에서 읽은 값> - 1 WHERE id = 2;` |
| 8 | | `COMMIT;` |
| 9 | `SELECT stock FROM products WHERE id = 2;` | |

기록: 9번의 값과 "기대한 값". 7번이 대기했는지.

## 변형 (각각 stock 을 100 으로 되돌리고 시작)
1. 1, 3번을 `BEGIN ISOLATION LEVEL REPEATABLE READ;` 로 — 7·8번에서 무슨 일이 생기는가
2. 5, 7번을 `UPDATE products SET stock = stock - 1 WHERE id = 2;` 로 (READ COMMITTED) — 9번의 값은
3. 2, 4번을 `SELECT stock FROM products WHERE id = 2 FOR UPDATE;` 로 — 4번이 언제 돌아오는가, 4번이 돌려주는 값은
4. 위 세 방식이 각각 "무엇을 막고 무엇을 못 막는지" 표로 정리 (04-write-skew 와 연결해서)
