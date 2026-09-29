# Lab 04 — 락과 동시성

세 파트: (A) 재고 차감 동시성, (B) 작업 큐와 `FOR UPDATE SKIP LOCKED`, (C) 데드락 유도와 관찰.
A, B 는 Python 하네스가 여러 워커를 동시에 돌리고 결과를 검증합니다. **SQL 은 여러분이 씁니다.**

## 준비

```bash
make seed-small && make venv
make sql FILE=labs/04-locks/setup.sql
```

락 관찰 (세 번째 터미널에서 반복 실행):

```bash
make sql FILE=labs/04-locks/locks.sql
make logs          # log_lock_waits=on 이라 1초 이상 대기하면 로그에 찍힘. 데드락도 여기 나옴
```

---

## Part A. 재고 차감 동시성

`stock_worker.py` 는 N 개 워커가 각각 M 번 "재고 1개 차감" 을 시도합니다. 시작 재고는 `--stock` (기본 50), 시도 횟수는 워커 × 반복 (기본 10 × 10 = 100). 즉 **50개만 팔려야 하고 50번은 품절로 거절돼야** 정상입니다.

```bash
.venv/bin/python labs/04-locks/stock_worker.py --sql labs/04-locks/decrement_naive.sql
.venv/bin/python labs/04-locks/stock_worker.py --sql labs/04-locks/decrement_naive.sql --think-ms 5   # 경합을 더 잘 재현
```

하네스가 출력하는 것: 판매 성공 수, 품절 거절 수, 최종 재고, **불일치(초과 판매 / 사라진 차감)**, 에러 종류별 수(SQLSTATE), 소요 시간, 초당 처리량.

### SQL 파일 규칙
- 세미콜론으로 구분된 문장을 한 트랜잭션 안에서 순서대로 실행하고 COMMIT 합니다.
- 파라미터: `%(product_id)s`, `%(worker)s`. 직전 문장이 행을 돌려주면 첫 컬럼이 `%(last)s` 로 다음 문장에 들어갑니다.
- **마지막 문장이 1행 이상 돌려주면 "판매 성공", 0행이면 "품절"** 로 셉니다. (`UPDATE ... RETURNING` 활용)
- 에러가 나면 그 시도는 ROLLBACK 되고 SQLSTATE 별로 집계됩니다. `--retry` 를 주면 40001/40P01 은 재시도합니다.

### 과제
1. `decrement_naive.sql` (읽고 → 애플리케이션에서 판단 → 쓰기) 로 불일치를 재현하고 수치 기록
2. 같은 규칙(재고 0 미만 금지, 품절이면 거절)을 지키는 SQL 을 **최소 세 가지 방식** 으로 작성해 각각 측정
   - 예를 들어 행 잠금, 원자적 갱신 + 조건, 격리 수준 + 재시도(`--isolation serializable --retry`), 제약 조건 ... 조합은 자유
3. 방식별로: 정확성(불일치 0인가), 처리량, 에러/재시도 수, 대기 시간을 표로 비교
4. `--workers 50` 으로 올렸을 때 어떤 방식이 가장 처리량이 떨어지는가. `locks.sql` 로 대기 중인 세션의 `wait_event` 관찰

---

## Part B. 작업 큐: FOR UPDATE / SKIP LOCKED

`lab04_jobs` 에 pending 작업 2,000 개가 있습니다. `queue_worker.py` 는 N 개 워커가 각자 "작업 하나 집기 → 처리(`--work-ms`) → done 표시" 를 반복합니다. 집기 SQL 은 여러분이 씁니다.

```bash
make sql FILE=labs/04-locks/setup.sql        # 큐 초기화
.venv/bin/python labs/04-locks/queue_worker.py --sql labs/04-locks/pick_naive.sql --workers 8
```

하네스가 출력하는 것: 워커별 처리 수, **같은 작업을 두 워커가 처리한 수(중복)**, 처리 안 된 작업 수, 총 소요 시간, 초당 처리량, 워커별 대기 시간 분포.

### SQL 파일 규칙
- Part A 와 같은 규칙. 마지막 문장이 돌려주는 첫 컬럼을 "집은 작업 id" 로 봅니다. 0행이면 "큐 비었음" 으로 워커가 종료합니다.
- 하네스는 집은 뒤 `--work-ms` 만큼 기다렸다가 **같은 트랜잭션 안에서** `UPDATE lab04_jobs SET status = 'done', done_at = now(), locked_by = %(worker)s WHERE id = %(job)s` 를 실행하고 COMMIT 합니다. (이 부분은 고정)

### 과제
1. `pick_naive.sql` 로 중복 처리를 재현
2. `FOR UPDATE` 만 붙인 버전과 `FOR UPDATE SKIP LOCKED` 버전을 각각 작성해 중복 수·처리량·대기 시간 비교
3. `--work-ms 50` 처럼 처리 시간을 늘리면 두 방식의 차이가 어떻게 달라지는가
4. `ORDER BY` 를 빼면/바꾸면 어떤 일이 생기는지, `LIMIT` 없이 여러 개를 집으면 어떤지

---

## Part C. 데드락

### C-1. 두 세션으로 직접 만들기

| 순서 | 세션 A (`make psql-a`) | 세션 B (`make psql-b`) |
|---|---|---|
| 1 | `BEGIN;` | `BEGIN;` |
| 2 | `UPDATE products SET stock = stock - 1 WHERE id = 1;` | |
| 3 | | `UPDATE products SET stock = stock - 1 WHERE id = 2;` |
| 4 | `UPDATE products SET stock = stock - 1 WHERE id = 2;` | |
| 5 | | `UPDATE products SET stock = stock - 1 WHERE id = 1;` |
| 6 | (결과 관찰) | (결과 관찰) |
| 7 | `ROLLBACK;` 또는 `COMMIT;` | `ROLLBACK;` 또는 `COMMIT;` |

4번 직후(5번 전에) 세 번째 터미널에서 `locks.sql` 을 실행해 대기 상태를 캡처하세요. 5번 이후 `make logs` 의 메시지도 기록.

기록: 어느 세션이 어떤 에러(SQLSTATE 40P01)를 받았는가, 몇 초 만에(`deadlock_timeout`), 남은 세션은 어떻게 됐는가, 로그의 "Process X waits for ... blocked by process Y" 메시지 전문.

### C-2. 워커로 재현

```bash
.venv/bin/python labs/04-locks/stock_worker.py --sql labs/04-locks/pair_a.sql --sql-alt labs/04-locks/pair_b.sql --workers 10 --stock 100000
```

짝수 워커는 `pair_a.sql`(1번 → 2번 순서), 홀수 워커는 `pair_b.sql`(2번 → 1번 순서) 로 두 상품을 함께 차감합니다.

과제
1. 데드락 발생 수(40P01)와 처리량 기록
2. 데드락이 나지 않게 SQL 을 고치고(파일을 새로 만들어) 다시 측정. 방법은 하나가 아닙니다
3. `--retry` 를 켜면 결과가 어떻게 달라지는지. 재시도가 "해결" 인지 아닌지 의견

---

## 참고 문서
- 명시적 잠금: https://www.postgresql.org/docs/current/explicit-locking.html
- pg_locks: https://www.postgresql.org/docs/current/view-pg-locks.html
