# Lab 01 — 인덱스와 실행 계획

## 이 랩에서 하는 일

지금 DB 에는 PK 외 인덱스가 하나도 없습니다. 그래서 `queries/` 폴더의 쿼리 7개는 모두 느립니다.
각 쿼리마다 아래 네 단계를 반복하고, 결과를 `record.md` 에 남기면 됩니다.

```
① before 측정        ② 실행 계획 읽기          ③ 인덱스 만들기       ④ after 측정 + 비교
measure.py 로 저장 → EXPLAIN 에서 왜 느린지 → CREATE INDEX ...  → measure.py + compare.py
                      찾기 (어디서 시간을 씀?)                       → record.md 에 표 붙이기
```

아래 "예시: 한 사이클 따라하기" 를 먼저 한 번 따라 해보고, 그다음 Q1 부터 같은 방식으로 풀면 됩니다.

## 실습 테이블은 어디에 있나

| 항목 | 값 |
|---|---|
| 접속 | `localhost:5432`, 사용자 `lab`, 비밀번호 `lab` |
| 데이터베이스 | **`lab`** (`postgres` 데이터베이스에는 테이블이 없습니다) |
| 스키마 | `public` |
| 이 랩에서 쓰는 테이블 | `orders`, `users`, `order_items`, `products` |

`lab01_` 같은 전용 테이블은 없습니다. Lab 01 은 시드로 만든 위 네 테이블을 그대로 씁니다.
(`lab03_coupon_uses`, `lab04_jobs` 는 Lab 03, 04 의 setup.sql 이 만드는 테이블입니다.)

VS Code 에서 보는 방법은 맨 아래 "VS Code 에서 테이블 보기" 를 참고하세요.

## 준비

모든 명령은 **저장소 루트**(`~/Desktop/postgre`)에서 실행합니다.

```bash
make up                  # 컨테이너가 꺼져 있으면
make verify              # 행 수 확인 + "인덱스 목록" 에 *_pkey 만 있는지 확인
make venv                # 처음 한 번 (측정 도구 설치)
```

---

## 예시: 한 사이클 따라하기

7개 문제와 상관없는 쿼리로 전체 흐름을 보여줍니다. **"이름으로 유저 한 명 찾기"** 입니다.

```sql
SELECT id, email, tier FROM users WHERE name = 'user_777';
```

### ① before 측정

```bash
.venv/bin/python tools/measure.py \
  --query "SELECT id, email, tier FROM users WHERE name = 'user_777'" \
  --label demo_before
```

- `--query` 대신 `--sql 파일경로` 를 쓰면 파일에 적힌 쿼리를 측정합니다. 7개 문제는 이 방식으로 합니다.
- `--label` 은 결과 파일 이름입니다. 나중에 비교할 때 이 이름으로 찾습니다.
- 결과는 `results/오늘날짜/시각_demo_before.txt` 와 `.json` 으로 저장됩니다.

### ② 실행 계획 읽기

`make psql` 로 접속해서 같은 쿼리 앞에 `EXPLAIN (ANALYZE, BUFFERS)` 를 붙입니다. (measure.py 가 저장한 .txt 파일 아래쪽에도 같은 내용이 있습니다.)

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT id, email, tier FROM users WHERE name = 'user_777';
```

실제 출력:

```
 Seq Scan on users  (cost=0.00..2432.00 rows=1 width=34) (actual time=0.064..5.245 rows=1.00 loops=1)
   Filter: (name = 'user_777'::text)
   Rows Removed by Filter: 99999
   Buffers: shared hit=1182
 Planning Time: 0.352 ms
 Execution Time: 5.316 ms
```

한 줄씩 읽으면 이렇습니다.

| 출력 | 뜻 | 이 예시에서 |
|---|---|---|
| `Seq Scan on users` | 테이블을 처음부터 끝까지 전부 읽음 | 1명을 찾으려고 10만 행을 다 봄 |
| `rows=1` (cost 괄호 안) | 플래너가 **예상한** 결과 행 수 | 1행 예상 |
| `rows=1.00` (actual 괄호 안) | **실제** 결과 행 수 | 실제로도 1행 |
| `Filter:` | 읽은 행마다 검사한 조건 | name 비교를 10만 번 |
| `Rows Removed by Filter: 99999` | 읽었지만 버린 행 수 | 99,999행을 읽고 버림. **낭비의 크기** |
| `Buffers: shared hit=1182` | 읽은 8KB 페이지 수. hit 는 메모리, read 는 디스크 | 1,182페이지 ≈ 9MB 를 훑음 |
| `Execution Time` | 실제 실행 시간 | 5.3ms |

결론: "1행을 얻으려고 테이블 전체(1,182페이지)를 읽는다" 가 느린 원인입니다.

### ③ 인덱스 만들기

```sql
\timing on
CREATE INDEX idx_users_name ON users (name);     -- Time: 95.734 ms
\di+ idx_users_name                              -- Size: 3104 kB
```

생성 시간과 크기도 기록합니다. 인덱스는 공짜가 아니기 때문입니다 (디스크 + INSERT/UPDATE 때마다 갱신 비용).

다시 실행 계획을 봅니다.

```
 Index Scan using idx_users_name on users  (cost=0.42..8.44 rows=1 width=34) (actual time=0.053..0.054 rows=1.00 loops=1)
   Index Cond: (name = 'user_777'::text)
   Buffers: shared hit=1 read=3
 Execution Time: 0.079 ms
```

| 바뀐 점 | before | after |
|---|---|---|
| 스캔 방식 | `Seq Scan` (전체 읽기) | `Index Scan` (인덱스로 위치를 찾아 그 행만 읽기) |
| 조건 처리 | `Filter` + 99,999행 버림 | `Index Cond` (버리는 행 없음) |
| 읽은 페이지 | 1,182 | 4 |

`read=3` 은 방금 만든 인덱스가 아직 메모리에 없어서 디스크에서 읽었다는 뜻입니다. 한 번 더 실행하면 hit 로 바뀝니다.

### ④ after 측정 + 비교

```bash
.venv/bin/python tools/measure.py \
  --query "SELECT id, email, tier FROM users WHERE name = 'user_777'" \
  --label demo_after
.venv/bin/python tools/compare.py demo_before demo_after
```

출력 (일부):

```
| 항목 | Before (demo_before) | After (demo_after) | 변화 |
|---|---:|---:|---:|
| wall clock median (ms) | 11.05 | 0.18 | -98.3% |
| execution median (ms) | 3.58 | 0.01 | -99.9% |
| shared hit blocks | 1,182 | 4 | -99.7% |
| rows returned | 1 | 1 | +0.0% |
```

이 표를 그대로 `record.md` 의 "수치" 칸에 붙여넣습니다.

- **wall clock**: 파이썬에서 쿼리를 보내고 결과를 받을 때까지 걸린 시간. 네트워크와 결과 전송이 포함됩니다.
- **execution**: DB 안에서 실행만 한 시간 (EXPLAIN ANALYZE 의 Execution Time).
- 두 값이 크게 다르면 DB 밖(전송, 결과 크기)에서 시간이 쓰이고 있다는 뜻입니다.
- `rows returned` 가 before/after 에서 같은지 꼭 확인하세요. 다르면 결과가 바뀐 것이니 비교가 무의미합니다.

### 예시 정리 (중요)

예시 인덱스는 문제 풀이에 영향을 주지 않도록 지워주세요.

```sql
DROP INDEX idx_users_name;
```

### 예시를 record.md 에 쓰면

```markdown
## 예시. 이름으로 유저 찾기

### 재현
- 실행한 명령: measure.py --query "... WHERE name = 'user_777'" --label demo_before
- before 계획 요약: Seq Scan on users, rows 예상 1 / 실제 1, Rows Removed by Filter 99,999, shared hit 1,182

### 원인
- name 컬럼에 인덱스가 없어서 1행을 찾으려고 10만 행(1,182페이지)을 모두 읽고 99,999행을 버림

### 해결
- CREATE INDEX idx_users_name ON users (name);
- 크기 3,104 kB (테이블 9.5MB 의 약 1/3), 생성 96ms

### 수치
| 항목 | Before | After | 변화 |
|---|---:|---:|---:|
| execution median (ms) | 3.58 | 0.01 | -99.9% |
| shared hit blocks | 1,182 | 4 | -99.7% |
| 스캔 노드 | Seq Scan | Index Scan | |
```

---

## 문제

예시와 같은 방식으로 풀면 됩니다. 단, 7개 문제는 예시처럼 "컬럼 하나에 인덱스" 로 끝나지 않는 것이 많습니다. 표의 "관찰/기록할 것" 이 힌트 역할을 합니다.

```bash
# 문제 측정 명령 형태 (q1 예)
.venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_before
.venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_after
.venv/bin/python tools/compare.py q1_before q1_after
```

| # | 파일 | 시나리오 | 관찰/기록할 것 |
|---|---|---|---|
| Q1 | `queries/q1_range.sql` | 어제 하루 주문 건수·매출 (created_at 범위) | 스캔 방식, rows 추정치 vs 실제, shared read/hit, 범위를 30일로 넓히면(`q1_range_30d.sql`) 계획이 바뀌는가 |
| Q2 | `queries/q2_user_orders.sql` | 특정 유저의 최근 주문 20건 (등치 + 정렬 + LIMIT) | `user_id = 4242` 와 `user_id = 1`(주문이 몰린 유저) 에서 계획·시간이 같은가. 인덱스 컬럼 순서/방향에 따른 차이 |
| Q3 | `queries/q3_join.sql` | 지난 7일 KR 유저의 카테고리별 매출 (4개 테이블 조인) | 조인 방식(Nested Loop / Hash / Merge), 어느 테이블부터 읽는지, Hash 의 Batches, 어떤 조건이 가장 먼저 걸러지는지 |
| Q4 | `queries/q4_sort_topn.sql` | pending 주문 최신 100건 (정렬 + LIMIT) | Sort Method (top-N heapsort / external merge), 정렬에 쓰인 메모리·temp 블록, `work_mem` 을 바꾸면 |
| Q5 | `queries/q5_like_prefix.sql`, `queries/q5_like_infix.sql` | memo `LIKE 'gift wrap%'` vs `LIKE '%ref:a1b%'` | 같은 인덱스로 둘 다 빨라지는가. B-tree 연산자 클래스(`text_pattern_ops`)와 확장(`pg_trgm`)의 차이 |
| Q6 | `queries/q6_function.sql` | 지난달 주문 상태별 건수 (`date_trunc` 를 컬럼에 적용) | 인덱스를 만들었는데도 쓰이지 않는다면 이유. 조건을 바꿔 쓰는 방법과 표현식 인덱스의 차이. `lower(email)` 도 같은 유형 |
| Q7 | `queries/q7_rare_status.sql` | `status = 'disputed'` (전체의 0.01%) | 같은 인덱스로 `status = 'completed'` 를 조회하면 계획이 어떻게 달라지는가. `pg_stats` 의 most_common_vals. 부분 인덱스(partial index) 크기 |

Q2 의 `user_id = 1` 버전처럼 파일을 조금 바꿔 측정하고 싶으면 파일을 복사해서 고치거나 `--query` 에 직접 넣으면 됩니다.

## 실행 계획 용어 모음

예시에 나오지 않은 용어도 문제를 풀다 보면 나옵니다. 의미만 정리합니다.

| 용어 | 뜻 |
|---|---|
| `Seq Scan` | 테이블 전체를 순서대로 읽음 |
| `Index Scan` | 인덱스로 행 위치를 찾고, 테이블에서 그 행을 하나씩 읽음 |
| `Index Only Scan` | 인덱스만 읽고 테이블은 읽지 않음 (필요한 컬럼이 전부 인덱스에 있을 때) |
| `Bitmap Index Scan` + `Bitmap Heap Scan` | 인덱스로 해당 페이지 목록을 먼저 모은 뒤, 페이지 순서대로 테이블을 읽음. 결과 행이 "적지도 많지도 않을 때" 자주 나옴 |
| `Parallel Seq Scan`, `Workers Launched` | 여러 프로세스가 나눠서 읽음 |
| `Nested Loop` / `Hash Join` / `Merge Join` | 조인 방식. 바깥 행마다 안쪽을 찾기 / 한쪽으로 해시 테이블 만들기 / 양쪽을 정렬해서 맞추기 |
| `Sort Method: quicksort Memory: 25kB` | 메모리 안에서 정렬 |
| `Sort Method: external merge Disk: 12000kB` | `work_mem` 이 모자라 디스크(temp)를 써서 정렬 |
| `top-N heapsort` | LIMIT 이 있어서 상위 N개만 유지하며 정렬 |
| `cost=A..B` | 플래너가 계산한 비용 추정치 (단위 없음). A 는 첫 행까지, B 는 전체 |
| `loops=N` | 이 노드가 N번 실행됨. actual time 과 rows 는 **1회 평균** 이라 전체는 × N |
| `Buffers: shared hit / read` | 메모리에서 찾은 페이지 / 디스크에서 읽은 페이지 (1페이지 = 8KB) |
| `temp read / written` | 정렬·해시가 메모리를 넘쳐 임시 파일을 쓴 양 |
| `Rows Removed by Filter` | 읽었지만 조건에 안 맞아 버린 행 수 |
| `rows` 예상 vs 실제가 크게 다름 | 플래너가 잘못 추정함. 잘못된 계획의 흔한 원인 (통계 확인: `observe.sql`) |

## 자주 막히는 점

- **같은 쿼리를 두 번 실행하면 두 번째가 훨씬 빠르다** — 처음엔 디스크(read)에서, 다음엔 메모리(hit)에서 읽기 때문입니다. measure.py 는 기본으로 1회 예열 후 측정합니다. 첫 실행까지 보고 싶으면 `--cold`.
- **인덱스를 만들었는데 계획이 그대로 Seq Scan** — 실수가 아닐 수 있습니다. 플래너가 "인덱스를 안 쓰는 게 더 싸다" 고 판단한 것일 수 있습니다. 왜 그런지가 곧 기록할 거리입니다. 확인용으로 `--set enable_seqscan=off` 를 주면 강제로 인덱스를 쓰게 해서 비교할 수 있습니다.
- **compare.py 가 "결과를 찾을 수 없음"** — label 철자 확인. 같은 label 로 여러 번 측정했다면 가장 최근 파일을 씁니다.
- **measure.py 가 접속 실패** — 저장소 루트에서 실행했는지, `make up` 상태인지 확인.
- **처음 상태로 돌리고 싶다** — `make sql FILE=labs/01-index-explain/reset_indexes.sql` (PK 빼고 인덱스 전부 삭제).

## 더 해볼 것

- 인덱스 생성 시간, 크기(`\di+`), 테이블 크기 대비 비율
- 인덱스를 만든 뒤 `INSERT`/`UPDATE` 가 얼마나 느려지는지 (`measure.py --rollback` 으로 DML 측정)
- `random_page_cost` 를 1.1 로 낮췄을 때 플래너 선택이 바뀌는 쿼리가 있는지 (`--set random_page_cost=1.1`)
- 인덱스·통계·캐시 상태 한눈에 보기: `make sql FILE=labs/01-index-explain/observe.sql`

## VS Code 에서 테이블 보기

"Database Client" 확장(cweijan) 기준입니다.

1. 접속 설정을 열어 아래처럼 입력합니다.
   - Host `127.0.0.1`, Port `5432`, Username `lab`, Password `lab`
   - **Database `lab`** ← `postgres` 로 두면 빈 데이터베이스가 보입니다
2. 저장 후 트리에서 `lab` → `public` → `Tables` 를 펼치면 `orders`, `users`, `order_items`, `products` 가 보입니다.
3. 그래도 안 보이면 연결 이름에서 우클릭 → Refresh. 시드를 실행하기 전에 연결했다면 새로고침이 필요합니다.

확장에서 쿼리를 실행해도 되지만, 측정 기록은 measure.py 로 남기세요. 확장이 표시하는 시간은 화면 표시까지 포함돼서 비교 기준으로 쓰기 어렵습니다.

## 참고 문서

- EXPLAIN 읽는 법: https://www.postgresql.org/docs/current/using-explain.html
- 인덱스 종류: https://www.postgresql.org/docs/current/indexes-types.html
- 플래너 통계(pg_stats): https://www.postgresql.org/docs/current/planner-stats.html
