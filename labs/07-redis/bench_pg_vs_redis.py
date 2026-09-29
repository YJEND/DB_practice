#!/usr/bin/env python3
"""
PostgreSQL 조회 vs Redis 조회 지연 비교.

  .venv/bin/python labs/07-redis/bench_pg_vs_redis.py --requests 2000
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import labenv  # noqa: E402


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


def bench(name, fn, ids):
    lat = []
    for uid in ids[:20]:
        fn(uid)  # 예열
    t0 = time.perf_counter()
    for uid in ids:
        s = time.perf_counter()
        fn(uid)
        lat.append((time.perf_counter() - s) * 1000)
    total = time.perf_counter() - t0
    row = {"name": name, "p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99), "ops": len(ids) / total}
    print(f"{name:<28} p50={row['p50']:>8.3f}ms  p95={row['p95']:>8.3f}ms  p99={row['p99']:>8.3f}ms  {row['ops']:>8.0f} req/s")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    random.seed(args.seed)

    pg = labenv.pg_connect(autocommit=True)
    r = labenv.redis_connect()
    n_users = pg.execute("SELECT max(id) FROM users").fetchone()[0]
    # 편향된 유저 선택: 주문이 많은(작은 id) 유저가 자주 조회됨
    ids = [1 + int((random.random() ** 4) * n_users) for _ in range(args.requests)]

    # Redis 에 미리 요약값을 넣어둠 (Part B 에서는 이 부분을 직접 구현하게 됨)
    distinct = sorted(set(ids))
    rows = pg.execute("SELECT user_id, count(*), coalesce(sum(total_amount), 0) FROM orders WHERE user_id = ANY(%s) GROUP BY user_id",
                      (distinct,)).fetchall()
    pipe = r.pipeline()
    for uid, cnt, total in rows:
        pipe.set(f"bench:user_summary:{uid}", json.dumps({"orders": cnt, "total": str(total)}), ex=600)
    pipe.execute()

    print(f"requests={args.requests}  distinct users={len(distinct)}  (PG {labenv.pg_dsn().split('password')[0]}...)\n")
    results = [
        bench("PG PK lookup (users)", lambda uid: pg.execute("SELECT id, name, tier FROM users WHERE id = %s", (uid,)).fetchone(), ids),
        bench("PG aggregate (orders by user)", lambda uid: pg.execute("SELECT count(*), sum(total_amount) FROM orders WHERE user_id = %s", (uid,)).fetchone(), ids),
        bench("Redis GET (precomputed)", lambda uid: r.get(f"bench:user_summary:{uid}"), ids),
    ]
    idx = [x[0] for x in pg.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'orders' AND indexname <> 'orders_pkey'").fetchall()]
    print(f"\norders 의 PK 외 인덱스: {idx or '없음'}")
    out = labenv.results_dir() / f"{datetime.now().strftime('%H%M%S')}_pg_vs_redis.json"
    out.write_text(json.dumps({"requests": args.requests, "orders_indexes": idx, "results": results}, indent=2))
    print(f"저장: {out.relative_to(labenv.REPO_ROOT)}")


if __name__ == "__main__":
    main()
