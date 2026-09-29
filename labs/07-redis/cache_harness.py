#!/usr/bin/env python3
"""
캐시 어사이드 하네스: my_cache.get_user_summary 를 호출해 히트율, 지연, stale 여부를 측정합니다.

  .venv/bin/python labs/07-redis/cache_harness.py --requests 3000 --ttl 30
  .venv/bin/python labs/07-redis/cache_harness.py --requests 3000 --ttl 30 --writes 50 --concurrency 1
"""
from __future__ import annotations

import argparse
import random
import sys
import threading
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))
import labenv  # noqa: E402
import my_cache  # noqa: E402

TRUTH = "SELECT count(*), coalesce(sum(total_amount), 0) FROM orders WHERE user_id = %s"


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=3000)
    ap.add_argument("--ttl", type=int, default=30, help="구현에 넘겨줄 TTL(초)")
    ap.add_argument("--writes", type=int, default=0, help="요청 중간에 끼워 넣을 주문 INSERT 수")
    ap.add_argument("--concurrency", type=int, default=1, help="동시 스레드 수 (stampede 관찰용)")
    ap.add_argument("--hot-users", type=int, default=200, help="자주 조회되는 유저 풀 크기")
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    random.seed(args.seed)

    r = labenv.redis_connect()
    setup = labenv.pg_connect(autocommit=True)
    n_users = setup.execute("SELECT max(id) FROM users").fetchone()[0]
    hot = random.sample(range(1, n_users + 1), args.hot_users)
    reqs = [random.choice(hot) if random.random() < 0.9 else random.randint(1, n_users) for _ in range(args.requests)]
    write_at = set(random.sample(range(args.requests), min(args.writes, args.requests))) if args.writes else set()
    try:
        my_cache.get_user_summary(setup, r, hot[0], args.ttl)
    except NotImplementedError as e:
        sys.exit(f"my_cache.py 를 먼저 구현하세요: {e}")
    stats_before = r.info("stats")
    pgss_before = setup.execute("SELECT coalesce(sum(calls), 0) FROM pg_stat_statements WHERE query ILIKE '%FROM orders WHERE user_id%'").fetchone()[0]

    lat, sources, errors = [], Counter(), Counter()
    written = []
    lock = threading.Lock()

    def run(chunk):
        pg = labenv.pg_connect(autocommit=True)
        for i, uid in chunk:
            if i in write_at:
                pg.execute("INSERT INTO orders (user_id, status, total_amount, created_at) VALUES (%s, 'pending', 12.34, now())", (uid,))
                my_cache.on_order_created(r, uid)
                with lock:
                    written.append(uid)
            t0 = time.perf_counter()
            try:
                res = my_cache.get_user_summary(pg, r, uid, args.ttl)
                with lock:
                    lat.append((time.perf_counter() - t0) * 1000)
                    sources[res.get("source", "?")] += 1
            except NotImplementedError as e:
                sys.exit(f"my_cache.py 를 먼저 구현하세요: {e}")
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors[type(e).__name__] += 1
        pg.close()

    indexed = list(enumerate(reqs))
    chunks = [indexed[i::args.concurrency] for i in range(args.concurrency)]
    t0 = time.perf_counter()
    threads = [threading.Thread(target=run, args=(c,)) for c in chunks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0

    stats_after = r.info("stats")
    pgss_after = setup.execute("SELECT coalesce(sum(calls), 0) FROM pg_stat_statements WHERE query ILIKE '%FROM orders WHERE user_id%'").fetchone()[0]

    # stale 검사: 캐시가 있는 유저에 대해 구현이 돌려주는 값 vs DB 진짜 값
    stale, checked = 0, 0
    for uid in sorted(set(written) | set(hot[:50])):
        truth = setup.execute(TRUTH, (uid,)).fetchone()
        res = my_cache.get_user_summary(setup, r, uid, args.ttl)
        if res.get("source") == "cache":
            checked += 1
            if int(res["orders"]) != truth[0] or Decimal(str(res["total"])) != Decimal(str(truth[1])):
                stale += 1

    total = sum(sources.values())
    print(f"\nrequests={args.requests} ttl={args.ttl}s writes={args.writes} concurrency={args.concurrency}")
    print(f"  source 별      : {dict(sources)}   히트율={100 * sources['cache'] / max(total, 1):.1f}%")
    print(f"  지연           : p50={pct(lat, 50):.3f}ms p95={pct(lat, 95):.3f}ms   처리량={total / elapsed:.0f} req/s")
    print(f"  Redis 서버 통계: hits +{stats_after['keyspace_hits'] - stats_before['keyspace_hits']}  misses +{stats_after['keyspace_misses'] - stats_before['keyspace_misses']}")
    print(f"  DB 집계 쿼리 수: +{pgss_after - pgss_before}  (pg_stat_statements 기준)")
    print(f"  stale          : {stale} / {checked} (캐시에 있는 유저 중 DB 와 값이 다른 수)" + ("  <-- 확인" if stale else ""))
    if errors:
        print(f"  에러           : {dict(errors)}")
    if written:
        setup.execute("DELETE FROM orders WHERE status = 'pending' AND total_amount = 12.34 AND created_at > now() - interval '1 hour'")
        print(f"  (하네스가 넣은 주문 {len(written)}건 삭제함. 캐시는 그대로이니 다음 실행 전 FLUSHALL 또는 무효화 구현을 확인)")


if __name__ == "__main__":
    main()
