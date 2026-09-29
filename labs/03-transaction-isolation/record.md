# Lab 03 기록 — 트랜잭션 격리 수준

- 날짜:
- PostgreSQL 기본 격리 수준 (`SHOW default_transaction_isolation`):
- MySQL 비교 여부:

## 01. Dirty Read
### 재현 (단계별 관찰값)
| 단계 | 세션 | 실행 | 결과 |
|---|---|---|---|
| | | | |
### 원인 (왜 그런 결과가 나오는가)
### 해결 / 결론
### 격리 수준별 비교
| 격리 수준 | PostgreSQL 결과 | MySQL 결과 |
|---|---|---|
| READ UNCOMMITTED | | |
| READ COMMITTED | | |

## 02. Non-repeatable Read
(같은 형식)

## 03. Phantom Read

## 04. Write Skew
- REPEATABLE READ 에서:
- SERIALIZABLE 에서 (에러 메시지 전문):
- 격리 수준 없이 막는 방법 2가지와 각각의 비용:

## 05. Lost Update
| 방식 | 막는 것 | 못 막는 것 | 대기/에러 |
|---|---|---|---|
| READ COMMITTED + 읽고-계산-쓰기 | | | |
| REPEATABLE READ | | | |
| `SET stock = stock - 1` | | | |
| `FOR UPDATE` | | | |

## 배운 것 3줄
1.
2.
3.
