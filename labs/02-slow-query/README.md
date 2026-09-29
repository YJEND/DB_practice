# Lab 02 — 슬로우 쿼리 찾기, 페이지네이션, N+1

세 파트로 나뉩니다. A 는 "어떤 쿼리가 문제인지 찾는 법", B 와 C 는 자주 나오는 두 가지 안티패턴의 재현입니다.

## 준비

```bash
make seed-small && make venv
make sql FILE=labs/01-index-explain/reset_indexes.sql   # Lab 01 에서 만든 인덱스가 있으면 결과가 달라지므로 초기 상태로
```

---

## Part A. pg_stat_statements 로 느린 쿼리 찾기

`workload.py` 는 실제 서비스처럼 여러 종류의 쿼리를 섞어서 반복 실행합니다. 어떤 쿼리가 있는지 미리 보지 말고, 통계만으로 찾아보세요.

```bash
make psql -c "SELECT pg_stat_statements_reset();"     # 또는 psql 안에서 실행
.venv/bin/python labs/02-slow-query/workload.py --seconds 60
make sql FILE=labs/02-slow-query/pgss_top.sql
```

`pgss_top.sql` 은 같은 통계를 5가지 기준(총 실행 시간, 평균, 호출 수, 디스크 읽기, 행 수)으로 정렬해 보여줍니다.

기록할 것
- 기준마다 1위 쿼리가 다른가? 서비스 관점에서 "먼저 고쳐야 할" 쿼리는 어느 기준으로 골라야 하는가
- 고르기로 한 쿼리의 `queryid`, `calls`, `mean_exec_time`, `shared_blks_read`
- 그 쿼리의 실행 계획 (`EXPLAIN (ANALYZE, BUFFERS)`) 과 해결 후 같은 워크로드에서의 수치 변화
- 워크로드 전체 처리량(`workload.py` 가 끝날 때 출력하는 초당 쿼리 수) before/after

### auto_explain 켜기 (느린 쿼리의 계획을 로그로 자동 기록)

라이브러리는 이미 로드돼 있고(`shared_preload_libraries`), 기본은 꺼짐(-1)입니다.

```sql
-- 현재 세션만
SET auto_explain.log_min_duration = 200;   -- 200ms 이상 걸린 쿼리
-- 전체 (재시작 불필요, 새 세션부터 적용)
ALTER SYSTEM SET auto_explain.log_min_duration = 200;
SELECT pg_reload_conf();
-- 끄기
ALTER SYSTEM RESET auto_explain.log_min_duration; SELECT pg_reload_conf();
```

로그는 `make logs` 로 봅니다. `workload.py` 를 켜둔 채 로그를 보면 어떤 쿼리가 걸리는지 실시간으로 보입니다.

---

## Part B. 페이지네이션: OFFSET vs keyset

`pagination.sql` 에는 OFFSET 방식으로 1페이지, 1,000페이지, 10,000페이지를 가져오는 쿼리가 있습니다.

```bash
.venv/bin/python tools/measure.py --sql labs/02-slow-query/pagination_p1.sql     --label offset_p1
.venv/bin/python tools/measure.py --sql labs/02-slow-query/pagination_p1000.sql  --label offset_p1000
.venv/bin/python tools/measure.py --sql labs/02-slow-query/pagination_p10000.sql --label offset_p10000
```

과제
1. 페이지 번호에 따라 시간과 Buffers 가 어떻게 변하는지 표로 기록
2. 같은 결과를 **keyset(커서) 방식** 으로 가져오는 쿼리를 직접 작성하고 같은 세 페이지를 측정
3. 두 방식에 필요한 인덱스가 같은지, 정렬 키가 유일하지 않을 때(같은 created_at 이 여러 개) 어떤 문제가 생기는지
4. keyset 이 불가능한 UI 요구사항이 있다면 무엇인지 (기록에 남기기)

---

## Part C. N+1 재현

`n_plus_one.py --mode naive` 는 최근 주문 300건을 가져온 뒤, 주문마다 유저와 상품 정보를 따로 조회합니다.

```bash
make psql -c "SELECT pg_stat_statements_reset();"
.venv/bin/python labs/02-slow-query/n_plus_one.py --mode naive
make sql FILE=labs/02-slow-query/pgss_top.sql      # calls 기준으로 정렬된 표를 보세요
```

과제
1. 총 실행 시간, 실행된 SQL 개수(`pgss_top.sql` 의 calls 합), 쿼리 하나당 평균 시간을 기록
2. `my_solution.py` 의 `fetch_orders_with_details()` 를 구현해서 같은 결과를 더 적은 쿼리로 만들기
   (결과가 같은지 스크립트가 검증합니다)
3. `--mode mine` 으로 측정해 시간·쿼리 수 비교
4. 네트워크 왕복(RTT)이 1ms, 10ms 라면 차이가 얼마나 벌어질지 계산해서 기록 (`--rtt-ms` 옵션으로 인위적 지연을 넣어 실측 가능)

---

## 참고 문서
- pg_stat_statements: https://www.postgresql.org/docs/current/pgstatstatements.html
- auto_explain: https://www.postgresql.org/docs/current/auto-explain.html
