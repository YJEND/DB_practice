#!/usr/bin/env python3
"""
recall@k 와 지연 측정: 인덱스를 끈 정확한 kNN vs 현재 인덱스/설정으로 얻은 kNN 비교.

  .venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10
  .venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10 --set hnsw.ef_search=100
  .venv/bin/python labs/06-pgvector/recall.py --queries 100 --k 10 --set ivfflat.probes=20 --label ivf_p20
결과는 results/YYYY-MM-DD/HHMMSS_vec_<label>.json 에도 저장됩니다.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import labenv  # noqa: E402

KNN = ("SELECT id FROM doc_chunks WHERE id <> %(qid)s "
       "ORDER BY embedding <=> (SELECT embedding FROM doc_chunks WHERE id = %(qid)s) LIMIT %(k)s")


def run(conn, qids, k):
    lat, results = [], {}
    for qid in qids:
        t0 = time.perf_counter()
        rows = conn.execute(KNN, {"qid": qid, "k": k}).fetchall()
        lat.append((time.perf_counter() - t0) * 1000)
        results[qid] = [r[0] for r in rows]
    return results, lat


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", type=int, default=100)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--set", action="append", default=[], metavar="K=V")
    ap.add_argument("--label", default="")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)

    conn = labenv.pg_connect(autocommit=True)
    labenv.apply_settings(conn, args.set)
    max_id = conn.execute("SELECT max(id) FROM doc_chunks").fetchone()[0]
    qids = random.sample(range(1, max_id + 1), args.queries)
    indexes = [r[0] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'doc_chunks' AND indexname <> 'doc_chunks_pkey'")]

    # 정확한 결과 (인덱스 사용 금지)
    conn.execute("SET enable_indexscan = off")
    conn.execute("SET enable_bitmapscan = off")
    run(conn, qids[:3], args.k)  # 예열
    exact, exact_lat = run(conn, qids, args.k)
    conn.execute("SET enable_indexscan = on")
    conn.execute("SET enable_bitmapscan = on")

    # 인덱스 사용 결과
    run(conn, qids[:3], args.k)
    approx, approx_lat = run(conn, qids, args.k)
    plan = conn.execute("EXPLAIN " + KNN, {"qid": qids[0], "k": args.k}).fetchall()
    plan_first = plan[0][0] if plan else ""
    # PK 인덱스(서브쿼리의 id 조회)가 아니라 벡터 인덱스 이름이 계획에 나오는지로 판정
    uses_index = any(name in r[0] for r in plan for name in indexes)

    recalls = [len(set(exact[q]) & set(approx[q])) / args.k for q in qids]
    summary = {
        "label": args.label or "vec", "timestamp": datetime.now().isoformat(timespec="seconds"),
        "k": args.k, "queries": args.queries, "session_set": args.set, "indexes": indexes,
        "uses_index": uses_index, "recall_mean": statistics.mean(recalls), "recall_min": min(recalls),
        "exact_ms": {"p50": pct(exact_lat, 50), "p95": pct(exact_lat, 95)},
        "approx_ms": {"p50": pct(approx_lat, 50), "p95": pct(approx_lat, 95)},
    }
    print(f"indexes={indexes or '없음'}  set={args.set}")
    print(f"plan (index 사용 여부={uses_index}): {plan_first[:100]}")
    print(f"recall@{args.k}: mean={summary['recall_mean']:.3f} min={summary['recall_min']:.2f}   ({args.queries} queries)")
    print(f"exact  : p50={summary['exact_ms']['p50']:.2f}ms p95={summary['exact_ms']['p95']:.2f}ms")
    print(f"indexed: p50={summary['approx_ms']['p50']:.2f}ms p95={summary['approx_ms']['p95']:.2f}ms")
    out = labenv.results_dir() / f"{datetime.now().strftime('%H%M%S')}_vec_{summary['label']}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"저장: {out.relative_to(labenv.REPO_ROOT)}")


if __name__ == "__main__":
    main()
