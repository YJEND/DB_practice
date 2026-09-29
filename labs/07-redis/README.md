# Lab 07 — Redis: 캐시 어사이드, TTL, rate limit

세 파트: (A) PostgreSQL 조회 vs Redis 조회 측정, (B) 캐시 어사이드 패턴 구현과 검증, (C) rate limit (고정 윈도우 / 슬라이딩 윈도우).
B 와 C 는 **템플릿 파일의 함수를 여러분이 구현** 하고, 하네스가 정확성과 성능을 측정합니다.

## 준비

```bash
make up && make seed-small && make venv
make redis-cli            # PING → PONG 확인. 실습 중 관찰: MONITOR, INFO stats, TTL <key>, MEMORY USAGE <key>
```

Redis 키를 전부 지우려면 `make redis-cli` 안에서 `FLUSHALL`.

---

## Part A. PostgreSQL 조회 vs Redis 조회

```bash
.venv/bin/python labs/07-redis/bench_pg_vs_redis.py --requests 2000
```

세 가지를 같은 횟수만큼 측정합니다.
1. PG PK 조회: `SELECT ... FROM users WHERE id = $1`
2. PG 집계 조회: `SELECT count(*), sum(total_amount) FROM orders WHERE user_id = $1` (유저 요약 카드 같은 것)
3. Redis GET: 2번 결과를 미리 넣어둔 키

기록: 각각의 p50 / p95 / p99 (ms), 초당 처리량. 그리고 **왜 이 차이가 나는지** (네트워크 왕복은 셋 다 비슷한데 무엇이 다른가).
Lab 01 에서 orders(user_id) 인덱스를 만든 상태라면 2번이 어떻게 달라지는지도 비교하세요. 캐시가 필요한 쿼리와 인덱스로 충분한 쿼리를 구분하는 기준을 적어보세요.

---

## Part B. 캐시 어사이드 (cache-aside) + TTL

`my_cache.py` 의 `get_user_summary(pg, r, user_id)` 를 구현하세요. 반환값은 `{"orders": int, "total": Decimal|float, "source": "db"|"cache"}`.

```bash
.venv/bin/python labs/07-redis/cache_harness.py --requests 3000 --ttl 30
.venv/bin/python labs/07-redis/cache_harness.py --requests 3000 --ttl 30 --writes 50    # 중간에 주문이 들어오는 상황
```

하네스가 하는 일
- 편향된 유저 분포(일부 유저가 자주 조회됨)로 요청을 보내고 p50/p95 지연, 히트율(`source` 기준), Redis `keyspace_hits/misses` 를 출력
- `--writes N` 이면 요청 사이사이에 무작위 유저에게 주문을 INSERT 합니다. 끝날 때 **캐시 값과 DB 실제 값이 다른 유저 수(stale)** 를 셉니다
- `--ttl` 은 여러분의 구현이 참고할 값으로 넘겨줄 뿐, 실제 만료 설정은 구현에서 합니다

과제
1. TTL 만 있는 단순 구현으로 히트율·지연·stale 수 기록
2. 쓰기 시 캐시를 무효화하는 방법을 `on_order_created(r, user_id)` 에 구현 (하네스가 INSERT 직후 호출) → stale 수 변화
3. TTL 을 5초 / 30초 / 300초로 바꿨을 때 히트율과 stale 의 관계
4. 동시에 같은 키가 만료되면 무슨 일이 생기는지 (`--concurrency 20` 으로 스레드 늘려서 DB 쿼리 수 관찰: cache stampede)
5. 캐시에 넣을 값의 직렬화 방식(JSON / 해시 자료형 등)과 키 이름 규칙을 정하고 이유 기록

---

## Part C. rate limit

`my_rate_limit.py` 의 두 함수를 구현하세요.
- `is_allowed_fixed(r, key, limit, window_sec) -> bool` — 고정 윈도우
- `is_allowed_sliding(r, key, limit, window_sec) -> bool` — 슬라이딩 윈도우 (로그 방식이든 카운터 근사든 자유)

```bash
.venv/bin/python labs/07-redis/rate_limit_harness.py --impl fixed   --limit 100 --window 10
.venv/bin/python labs/07-redis/rate_limit_harness.py --impl sliding --limit 100 --window 10
```

하네스가 하는 일
- 시나리오 1 "burst": 한 유저가 순간적으로 limit × 3 개 요청 → 허용 수가 limit 인지
- 시나리오 2 "boundary": 윈도우 끝 직전에 limit 개, 윈도우 시작 직후에 limit 개 → 짧은 구간(1초)에 허용된 총 수
- 시나리오 3 "steady": 초당 일정 속도로 window 의 2배 시간 동안 → 시간대별 허용/거절 그래프(텍스트)
- 시나리오 4 "concurrent": 스레드 20개가 동시에 요청 → 허용 수가 limit 을 넘는지 (원자성)
- 각 시나리오의 호출 지연 p50/p95, 사용된 Redis 명령 수(`INFO commandstats` 차이)

과제
1. 두 방식의 시나리오별 결과표
2. 경계(boundary)에서 고정 윈도우가 허용한 수와 그 의미
3. 동시성 시나리오에서 limit 을 넘겼다면 원인과 원자적으로 만드는 방법 (MULTI/EXEC, Lua, INCR+EXPIRE 의 순서 문제 등 직접 조사)
4. 슬라이딩 로그 방식의 메모리 사용량(`MEMORY USAGE key`) 과 limit 이 100만일 때의 문제

---

## 참고 문서
- redis-py: https://redis.readthedocs.io/
- Redis 명령: https://redis.io/docs/latest/commands/
