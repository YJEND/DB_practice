# Lab 03 — 트랜잭션 격리 수준

세션 두 개를 번갈아 실행하면서 dirty read, non-repeatable read, phantom read, write skew, lost update 를 재현합니다.
각 시나리오 파일에는 **실행 순서만** 있습니다. 결과는 직접 관찰해서 `record.md` 에 적으세요.

## 준비

터미널 두 개를 열어 각각:

```bash
make psql-a      # 프롬프트 [A]
make psql-b      # 프롬프트 [B]
```

세션 이름이 `application_name` 에 들어가므로 세 번째 터미널에서 누가 누구를 기다리는지 볼 수 있습니다:

```bash
make sql FILE=labs/04-locks/locks.sql
```

시나리오용 테이블/데이터 준비 (반복 실행 가능):

```bash
make sql FILE=labs/03-transaction-isolation/setup.sql
```

## 알아둘 명령

```sql
SHOW transaction_isolation;                          -- 현재 세션의 기본 격리 수준
BEGIN ISOLATION LEVEL READ UNCOMMITTED;              -- 트랜잭션 단위로 지정
BEGIN ISOLATION LEVEL READ COMMITTED;
BEGIN ISOLATION LEVEL REPEATABLE READ;
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT txid_current();                               -- 지금 트랜잭션 ID (스냅샷 비교용)
SELECT xmin, xmax, * FROM products WHERE id = 1;     -- 행 버전(MVCC) 관찰
```

## 시나리오

| 파일 | 현상 | 핵심 질문 |
|---|---|---|
| `scenarios/01-dirty-read.md` | 커밋 안 된 값을 다른 세션이 읽는가 | PostgreSQL 에서 READ UNCOMMITTED 를 지정하면 실제로 무엇이 되는가. MySQL 은? |
| `scenarios/02-non-repeatable-read.md` | 같은 트랜잭션 안에서 같은 행을 두 번 읽었을 때 값이 바뀌는가 | READ COMMITTED 와 REPEATABLE READ 에서 스냅샷은 언제 잡히는가 |
| `scenarios/03-phantom-read.md` | 같은 조건으로 두 번 조회했을 때 행 수가 바뀌는가 | REPEATABLE READ 에서 UPDATE 가 다른 세션의 커밋과 충돌하면 |
| `scenarios/04-write-skew.md` | 두 세션이 각자 확인한 조건이 커밋 후 깨지는가 | REPEATABLE READ 로 막을 수 없는 이상 현상과 SERIALIZABLE 의 동작. 재시도는 누가 하는가 |
| `scenarios/05-lost-update.md` | 두 세션의 갱신 중 하나가 사라지는가 | 격리 수준, `UPDATE ... SET x = x - 1`, `FOR UPDATE` 각각이 무엇을 막는가 |

각 시나리오 끝에 "변형" 이 있습니다. 격리 수준을 바꿔 같은 순서를 반복하세요.

## 기록할 것

- 각 단계에서 SELECT 가 돌려준 값 (세션·단계별로)
- 어떤 문장이 **대기(block)** 했는지, 어떤 문장이 **에러** 를 냈는지 (SQLSTATE 와 메시지 전체)
- 격리 수준별 결과 비교표
- PostgreSQL 공식 문서의 표와 관찰 결과가 일치하는지: https://www.postgresql.org/docs/current/transaction-iso.html

## MySQL(InnoDB) 과 비교하기 (선택)

```bash
make up-mysql && make seed-mysql
make mysql            # 터미널 2개
```

```sql
SELECT @@transaction_isolation;
SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;   -- 이후 START TRANSACTION;
```

같은 순서를 InnoDB 기본값(REPEATABLE READ)과 READ UNCOMMITTED 에서 반복하고, PostgreSQL 과 결과가 다른 시나리오를 기록하세요. 특히 01, 03, 05 번.
