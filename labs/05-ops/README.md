# Lab 05 — VACUUM 과 bloat 관찰

대량 UPDATE 가 남기는 dead tuple 을 직접 보고, VACUUM / VACUUM FULL / autovacuum 이 각각 무엇을 바꾸는지 수치로 기록합니다.

## 준비

```bash
make seed-small && make venv
make sql FILE=labs/05-ops/bloat.sql        # 기준선(baseline) 캡처. 결과를 record.md 에 먼저 적어두세요
```

`bloat.sql` 이 보여주는 것: 테이블 크기, `n_live_tup` / `n_dead_tup`, 일반 UPDATE 와 HOT UPDATE 수, 마지막 (auto)vacuum 시각, `pgstattuple` 의 dead tuple 비율과 free space, PK 인덱스의 bloat 상태.

## 실습 순서

### 1. autovacuum 을 잠시 끄고 dead tuple 쌓기

autovacuum 이 중간에 치워버리면 관찰이 안 되므로 orders 테이블만 끕니다.

```sql
ALTER TABLE orders SET (autovacuum_enabled = false);
```

`update_workload.sql` 은 orders 의 약 20% 행을 갱신합니다. 한 번 실행할 때마다 `bloat.sql` 을 다시 실행해 기록하세요. 3회 반복.

```bash
make sql FILE=labs/05-ops/update_workload.sql
make sql FILE=labs/05-ops/bloat.sql
```

기록: 실행마다 테이블 크기, n_dead_tup, dead_tuple_percent, HOT 비율(n_tup_hot_upd / n_tup_upd), UPDATE 소요 시간.

### 2. bloat 가 쿼리에 미치는 영향

Lab 01 의 Q1(범위 조회, 인덱스 없는 상태) 을 bloat 전/후로 측정합니다.

```bash
.venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_bloated
.venv/bin/python tools/compare.py q1_before q1_bloated       # q1_before 는 Lab 01 에서 저장한 것
```

### 3. VACUUM 과 VACUUM FULL

```sql
\timing on
VACUUM (VERBOSE, ANALYZE) orders;           -- 출력 메시지 전체를 record.md 에 붙이세요
```

`bloat.sql` 다시 실행. 그다음:

```sql
VACUUM FULL orders;                         -- 실행 중 다른 터미널에서 orders 를 SELECT 해보세요
```

`bloat.sql` 다시 실행. 기록: 두 명령의 소요 시간, 전후 테이블 크기, n_dead_tup, 다른 세션이 막혔는지(`labs/04-locks/locks.sql`), 어떤 락 모드였는지.

### 4. autovacuum 이 알아서 하게 두기

```sql
ALTER TABLE orders RESET (autovacuum_enabled);
-- 기본 임계값(scale_factor 0.2 = 행의 20%) 을 낮춰서 빨리 돌게
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.01, autovacuum_vacuum_threshold = 1000);
```

다시 `update_workload.sql` 을 실행하고 `make logs` 로 autovacuum 로그(`log_autovacuum_min_duration = 0`)를 관찰. 진행 중이면 `SELECT * FROM pg_stat_progress_vacuum;`.

기록: autovacuum 이 시작되기까지 걸린 시간, 로그에 찍힌 "removed N dead tuples", 실행 중 UPDATE 처리 시간 변화.

### 5. HOT UPDATE 와 fillfactor (심화)

- `update_workload.sql` 의 갱신 컬럼(`memo`)에 인덱스가 있을 때와 없을 때 HOT 비율이 어떻게 달라지는지
- `ALTER TABLE orders SET (fillfactor = 70); VACUUM FULL orders;` 후 같은 워크로드에서 HOT 비율·테이블 크기 비교
- 인덱스 bloat: `bloat.sql` 의 `pgstatindex` 결과(avg_leaf_density, leaf_fragmentation) 가 UPDATE 반복 후 어떻게 변하는가. `REINDEX INDEX CONCURRENTLY orders_pkey` 전후

## 정리

```sql
ALTER TABLE orders RESET (autovacuum_enabled, autovacuum_vacuum_scale_factor, autovacuum_vacuum_threshold, fillfactor);
UPDATE orders SET memo = regexp_replace(memo, ' \[upd\d+\]', '', 'g') WHERE memo LIKE '%[upd%';   -- 워크로드가 붙인 표식 제거 (이것도 UPDATE 라 dead tuple 이 또 생김)
VACUUM FULL orders; ANALYZE orders;
```

## 참고 문서
- Routine Vacuuming: https://www.postgresql.org/docs/current/routine-vacuuming.html
- pgstattuple: https://www.postgresql.org/docs/current/pgstattuple.html
