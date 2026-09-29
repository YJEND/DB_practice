# Lab 07 기록 — Redis

- 날짜:
- 데이터 규모 / orders 인덱스 상태:

## Part A. PG vs Redis
| 조회 | p50 (ms) | p95 (ms) | p99 (ms) | req/s |
|---|---:|---:|---:|---:|
| PG PK lookup | | | | |
| PG aggregate (인덱스 없음) | | | | |
| PG aggregate (user_id 인덱스) | | | | |
| Redis GET | | | | |

- 차이의 원인:
- 캐시가 필요한 쿼리 vs 인덱스로 충분한 쿼리를 나누는 기준:

## Part B. 캐시 어사이드
### 재현 (TTL 만 있는 구현)
| ttl | writes | 히트율 | p50 | p95 | DB 쿼리 수 | stale |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 0 | | | | | |
| 30 | 50 | | | | | |

### 원인 (stale 이 생기는 이유)
-

### 해결 (무효화 구현 후)
| ttl | writes | 히트율 | stale |
|---|---:|---:|---:|
| 5 | 50 | | |
| 30 | 50 | | |
| 300 | 50 | | |

- concurrency 20 에서 DB 쿼리 수 (stampede):
- 키 규칙 / 직렬화 방식과 이유:

## Part C. rate limit
| 시나리오 | fixed 허용 | sliding 허용 | 기대 | 비고 |
|---|---:|---:|---:|---|
| burst | | | | |
| boundary (1초 구간) | | | | |
| steady (총 허용) | | | | |
| concurrent | | | | |

- 지연 / 요청당 Redis 명령 수:
- 원자성 문제와 해결:
- 슬라이딩 로그의 메모리:

## 배운 것 3줄
1.
2.
3.
