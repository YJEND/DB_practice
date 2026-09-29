# Lab 06 기록 — pgvector

- 날짜:
- doc_chunks 행 수 / 테이블 크기:
- 거리 함수: cosine (`<=>`)

## 재현: 인덱스 없음 (기준선)
- `knn.sql` 계획 (스캔 방식, 시간):
- `recall.py` exact p50 / p95:

## 원인 (왜 느린가, 벡터 검색에서 정확 탐색의 비용)
-

## 해결: 인덱스 비교표
| 인덱스 | 파라미터 (빌드) | 빌드 시간 | 크기 | 검색 파라미터 | recall@10 | p50 (ms) | p95 (ms) |
|---|---|---:|---:|---|---:|---:|---:|
| 없음 | - | - | - | - | 1.000 | | |
| HNSW | m=16, ef_construction=64 | | | ef_search=40 | | | |
| HNSW | | | | ef_search=100 | | | |
| HNSW | | | | ef_search=400 | | | |
| HNSW | m=__, ef_construction=__ | | | | | | |
| IVFFlat | lists=100 | | | probes=1 | | | |
| IVFFlat | | | | probes=10 | | | |
| IVFFlat | | | | probes=50 | | | |
| IVFFlat | lists=__ | | | | | | |

## 데이터 2배 증가 후 (IVFFlat 중심점 문제)
| 인덱스 | recall 전 | recall 후 |
|---|---:|---:|

## 필터 결합 (`knn_filtered.sql`)
- 결과 개수 / 계획 / iterative_scan 설정 전후:

## 어떤 상황에 어떤 인덱스를 고를지 (정리)
-

## 배운 것 3줄
1.
2.
3.
