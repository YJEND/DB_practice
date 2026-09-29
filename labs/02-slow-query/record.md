# Lab 02 기록 — 슬로우 쿼리 / 페이지네이션 / N+1

- 날짜:
- 데이터 규모:
- 인덱스 상태 (PK only / Lab01 인덱스 유지):

## Part A. pg_stat_statements

### 재현
- 워크로드: `workload.py --seconds __`, 처리량 __ queries/s
- 기준별 1위 쿼리 (queryid):

| 기준 | queryid | calls | total_ms | mean_ms | shared_blks_read |
|---|---|---:|---:|---:|---:|
| total_exec_time | | | | | |
| mean_exec_time | | | | | |
| calls | | | | | |
| shared_blks_read | | | | | |

- 먼저 고치기로 한 쿼리와 그 이유:

### 원인
-

### 해결
-

### 수치
| 항목 | Before | After | 변화 |
|---|---:|---:|---:|
| 해당 쿼리 mean_ms | | | |
| 해당 쿼리 total_ms (같은 시간 워크로드) | | | |
| 워크로드 처리량 (queries/s) | | | |

## Part B. 페이지네이션

| 페이지 | OFFSET ms | OFFSET buffers | keyset ms | keyset buffers |
|---|---:|---:|---:|---:|
| 1 | | | | |
| 1,000 | | | | |
| 10,000 | | | | |

- keyset 쿼리 (작성한 SQL):
- 필요한 인덱스:
- keyset 의 한계 / 주의점:

## Part C. N+1

| 항목 | naive | mine | rtt 5ms naive | rtt 5ms mine |
|---|---:|---:|---:|---:|
| 실행 시간 (ms) | | | | |
| SQL 수 | | | | |

- 해결 방식 (JOIN / IN / 배치 등) 과 선택 이유:
- ORM 을 쓴다면 어디서 이 문제가 생기는지:

## 배운 것 3줄
1.
2.
3.
