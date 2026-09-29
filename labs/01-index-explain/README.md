# Lab 01 — 인덱스와 실행 계획

인덱스가 PK 밖에 없는 상태에서 느린 쿼리 7개를 측정하고, 직접 인덱스를 설계해 before/after 를 수치로 남깁니다.

## 준비

```bash
make seed-small          # 또는 seed-large
make venv                # 측정 도구
make verify              # "인덱스 목록" 에 *_pkey 만 있는지 확인
```

## 측정 절차 (모든 문제 공통)

```bash
# 1. before
.venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_before

# 2. psql 에서 인덱스 설계/생성 (생성 시간도 기록: \timing on)
make psql

# 3. after
.venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_after

# 4. 비교표 → record.md 에 붙여넣기
.venv/bin/python tools/compare.py q1_before q1_after
```

- 실행 계획만 보고 싶으면 psql 에서 `EXPLAIN (ANALYZE, BUFFERS) <쿼리>`.
- 세션 설정을 바꿔서 비교하려면 `--set work_mem=64MB`, `--set random_page_cost=1.1`, `--set enable_seqscan=off` 처럼 붙입니다.
- 인덱스/통계/캐시 상태 확인 쿼리: `make sql FILE=labs/01-index-explain/observe.sql`
- PK 만 남기고 초기화: `make sql FILE=labs/01-index-explain/reset_indexes.sql`

## 문제

| # | 파일 | 시나리오 | 관찰/기록할 것 |
|---|---|---|---|
| Q1 | `queries/q1_range.sql` | 어제 하루 주문 건수·매출 (created_at 범위) | 스캔 방식, rows 추정치 vs 실제, shared read/hit, 범위를 30일로 넓히면 계획이 바뀌는가 |
| Q2 | `queries/q2_user_orders.sql` | 특정 유저의 최근 주문 20건 (등치 + 정렬 + LIMIT) | `user_id = 4242` 와 `user_id = 1`(주문이 몰린 유저) 에서 계획·시간이 같은가. 인덱스 컬럼 순서/방향에 따른 차이 |
| Q3 | `queries/q3_join.sql` | 지난 7일 KR 유저의 카테고리별 매출 (4개 테이블 조인) | 조인 방식(Nested Loop / Hash / Merge), 어느 테이블부터 읽는지, Hash 의 Batches, 어떤 조건이 가장 먼저 걸러지는지 |
| Q4 | `queries/q4_sort_topn.sql` | pending 주문 최신 100건 (정렬 + LIMIT) | Sort Method (top-N heapsort / external merge), 정렬에 쓰인 메모리·temp 블록, `work_mem` 을 바꾸면 |
| Q5 | `queries/q5_like_prefix.sql`, `queries/q5_like_infix.sql` | memo `LIKE 'gift wrap%'` vs `LIKE '%ref:a1b2%'` | 같은 인덱스로 둘 다 빨라지는가. B-tree 연산자 클래스(`text_pattern_ops`)와 확장(`pg_trgm`)의 차이 |
| Q6 | `queries/q6_function.sql` | 지난달 주문 상태별 건수 (`date_trunc` 를 컬럼에 적용) | 인덱스를 만들었는데도 쓰이지 않는다면 이유. 조건을 바꿔 쓰는 방법과 표현식 인덱스의 차이. `lower(email)` 도 같은 유형 |
| Q7 | `queries/q7_rare_status.sql` | `status = 'disputed'` (전체의 0.01%) | 같은 인덱스로 `status = 'completed'` 를 조회하면 계획이 어떻게 달라지는가. `pg_stats` 의 most_common_vals. 부분 인덱스(partial index) 크기 |

## 추가로 기록하면 좋은 것

- 인덱스 생성 시간, 인덱스 크기(`\di+`), 테이블 크기 대비 비율
- 인덱스를 만든 뒤 `INSERT`/`UPDATE` 가 얼마나 느려지는지 (`tools/measure.py --rollback` 로 DML 측정)
- 첫 실행(디스크 읽기) vs 두 번째 실행(캐시) 차이. `--cold` 옵션과 `observe.sql` 의 pg_buffercache 결과
- `random_page_cost` 를 1.1 로 낮췄을 때 플래너 선택이 바뀌는 쿼리가 있는지
- `ANALYZE` 전후 rows 추정치 변화 (인덱스 생성 후 통계가 오래됐다면)

## 참고 문서

- EXPLAIN 읽는 법: https://www.postgresql.org/docs/current/using-explain.html
- 인덱스 종류: https://www.postgresql.org/docs/current/indexes-types.html
- 플래너 통계(pg_stats): https://www.postgresql.org/docs/current/planner-stats.html
