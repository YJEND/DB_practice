# Lab 05 기록 — VACUUM / bloat

- 날짜:
- 데이터 규모:
- orders 에 인덱스: PK only / 그 외 (있으면 HOT 에 영향)

## 재현: UPDATE 반복
| 라운드 | UPDATE 시간 (ms) | table_size | n_dead_tup | dead_pct (pgstattuple) | n_tup_upd | n_tup_hot_upd | hot_pct |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | - | | | | | | |
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

## 원인 (MVCC 관점에서 왜 크기가 늘고 dead tuple 이 남는가)
-

## 쿼리 영향
| 항목 | bloat 전 (q1_before) | bloat 후 (q1_bloated) | VACUUM 후 | VACUUM FULL 후 |
|---|---:|---:|---:|---:|
| execution (ms) | | | | |
| shared read blocks | | | | |

## 해결: VACUUM vs VACUUM FULL
| 항목 | VACUUM | VACUUM FULL |
|---|---:|---:|
| 소요 시간 | | |
| 전 table_size → 후 | | |
| n_dead_tup 후 | | |
| 다른 세션 SELECT 가능 여부 / 락 모드 | | |
| VERBOSE 출력 요약 | | |

## autovacuum
- 임계값 변경 후 첫 autovacuum 까지 걸린 시간:
- 로그 발췌:
- 운영에서 autovacuum 이 못 따라가는 상황은 언제 생기는가 (생각 정리):

## 심화 (HOT / fillfactor / 인덱스 bloat)
-

## 배운 것 3줄
1.
2.
3.
