# Lab 06 — pgvector: HNSW vs IVFFlat

문서 청크 테이블에 384차원 더미 임베딩을 넣고, 인덱스 없음 / HNSW / IVFFlat 세 상태에서 **검색 시간, 재현율(recall), 인덱스 빌드 시간, 인덱스 크기** 를 비교합니다.

벡터는 랜덤이지만 100개의 중심점(cluster) 주변에 흩어지게 만들어서 "가까운 벡터" 가 실제로 존재합니다 (완전 균등 랜덤이면 ANN 인덱스가 비정상적으로 불리합니다).

## 준비

```bash
make venv
make sql FILE=labs/06-pgvector/setup.sql                       # 기본 10만 청크 (~150MB, 1~2분)
make sql FILE=labs/06-pgvector/setup.sql VARS="-v n=500000"    # 규모 조절 (50만이면 ~750MB, 5~10분)
make sql FILE=labs/06-pgvector/observe.sql
```

## 측정 도구

### 1) 단일 쿼리 계획 / 시간

`knn.sql` 은 청크 하나의 벡터를 질의 벡터로 써서 코사인 거리 기준 상위 10개를 찾습니다.

```bash
.venv/bin/python tools/measure.py --sql labs/06-pgvector/knn.sql --label knn_noindex
.venv/bin/python tools/measure.py --sql labs/06-pgvector/knn.sql --label knn_hnsw --set hnsw.ef_search=40
.venv/bin/python tools/measure.py --sql labs/06-pgvector/knn.sql --label knn_ivf  --set ivfflat.probes=10
```

### 2) 재현율 + 지연 (여러 질의 벡터 평균)

`recall.py` 는 질의 벡터 N 개를 뽑아, 인덱스를 끈 정확한 결과(`enable_indexscan = off`)와 인덱스를 쓴 결과를 비교해 recall@k 와 p50/p95 지연을 출력합니다.

```bash
.venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10
.venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10 --set hnsw.ef_search=100
.venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10 --set ivfflat.probes=1
.venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10 --set ivfflat.probes=50
```

인덱스가 여러 개 있으면 플래너가 하나를 고릅니다. 비교할 때는 하나만 남기거나 `--set enable_indexscan=off` 로 끄세요.

## 과제

1. **인덱스 없음**: `knn.sql` 의 계획과 시간, `recall.py` 의 exact 지연을 기준선으로 기록
2. **HNSW** 를 만들고 (`\timing on` 으로 빌드 시간, `observe.sql` 로 크기) 측정
   ```sql
   CREATE INDEX ON doc_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
   ```
   - `hnsw.ef_search` 를 10 / 40 / 100 / 400 으로 바꾸며 recall 과 지연이 어떻게 움직이는지
   - `m`, `ef_construction` 을 바꿔 다시 빌드하면 빌드 시간·크기·recall 이 어떻게 달라지는지 (한 조합 이상)
3. **IVFFlat** 을 만들고 같은 측정
   ```sql
   CREATE INDEX ON doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
   ```
   - `ivfflat.probes` 를 1 / 10 / 50 / 100 으로
   - `lists` 값을 바꿔 다시 빌드 (문서가 권장하는 공식과 비교: rows/1000 또는 sqrt(rows))
   - IVFFlat 은 **빌드 시점 데이터로 중심점을 잡습니다**. 인덱스를 만든 뒤 `setup.sql` 의 INSERT 부분만 다시 실행해 데이터를 2배로 늘리면 recall 이 어떻게 되는지 (HNSW 와 비교)
4. `WHERE doc_id < 1000` 같은 필터를 붙였을 때 (`knn_filtered.sql`) 인덱스가 쓰이는지, 결과 개수가 줄어드는지 (pgvector 0.8 의 iterative scan 옵션 `hnsw.iterative_scan` 도 시도)
5. 전체 비교표 작성: 빌드 시간 / 인덱스 크기 / recall@10 / p50 / p95 / 파라미터

## 참고 문서
- pgvector README (인덱스 옵션, 쿼리 옵션): https://github.com/pgvector/pgvector
