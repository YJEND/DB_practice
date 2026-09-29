# 03. Phantom Read

같은 조건으로 두 번 조회하는 사이에 다른 세션이 조건에 맞는 행을 **추가** 합니다.

| 순서 | 세션 A | 세션 B |
|---|---|---|
| 1 | | `BEGIN ISOLATION LEVEL READ COMMITTED;` |
| 2 | | `SELECT count(*) FROM orders WHERE user_id = 4242 AND status = 'pending';` |
| 3 | `BEGIN;` | |
| 4 | `INSERT INTO orders (user_id, status, total_amount, created_at) VALUES (4242, 'pending', 10, now()) RETURNING id;` | |
| 5 | `COMMIT;` | |
| 6 | | `SELECT count(*) FROM orders WHERE user_id = 4242 AND status = 'pending';` |
| 7 | | `UPDATE orders SET memo = 'lab03' WHERE user_id = 4242 AND status = 'pending';` |
| 8 | | (7번이 갱신한 행 수를 기록) |
| 9 | | `SELECT count(*) FROM orders WHERE user_id = 4242 AND status = 'pending' AND memo = 'lab03';` |
| 10 | | `COMMIT;` |

기록: 2, 6, 8, 9번의 값.

## 변형
- 1번을 `REPEATABLE READ` 로 바꿔 반복. 6번과 8번이 같은가?
- REPEATABLE READ 상태에서, 4번 대신 A 가 `UPDATE orders SET status = 'cancelled' WHERE id = <B 가 2번에서 센 행 중 하나>` 를 커밋한 뒤 B 가 7번을 실행하면 어떤 메시지가 나오는가 (SQLSTATE 기록)
- `SERIALIZABLE` 로도 반복
- 정리: `DELETE FROM orders WHERE user_id = 4242 AND total_amount = 10 AND status = 'pending'; UPDATE orders SET memo = NULL WHERE memo = 'lab03';`
