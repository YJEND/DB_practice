#!/usr/bin/env python3
"""
서비스 워크로드 흉내: 여러 쿼리를 가중치에 따라 섞어서 반복 실행합니다.
어떤 쿼리가 느린지 pg_stat_statements 로 찾는 것이 Part A 의 과제이므로,
이 파일의 쿼리 목록을 미리 읽지 않는 편이 실습에 좋습니다.

  .venv/bin/python labs/02-slow-query/workload.py --seconds 60
  .venv/bin/python labs/02-slow-query/workload.py --iterations 500
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import labenv  # noqa: E402

# (이름, 가중치, SQL, 파라미터 생성 함수)
QUERIES = [
    ("order_by_pk", 40,
     "SELECT * FROM orders WHERE id = %s",
     lambda n: (random.randint(1, n["orders"]),)),
    ("user_recent_orders", 20,
     "SELECT id, status, total_amount, created_at FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
     lambda n: (1 + int((random.random() ** 4) * n["users"]),)),
    ("user_by_email", 15,
     "SELECT id, name, tier FROM users WHERE lower(email) = %s",
     lambda n: (f"user{random.randint(1, n['users'])}@example.com",)),
    ("orders_page", 10,
     "SELECT id, user_id, total_amount, created_at FROM orders ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET %s",
     lambda n: (20 * random.randint(0, 3000),)),
    ("daily_sales", 6,
     "SELECT count(*), sum(total_amount) FROM orders WHERE created_at >= date_trunc('day', now()) - interval '1 day' AND created_at < date_trunc('day', now())",
     lambda n: ()),
    ("pending_latest", 5,
     "SELECT id, user_id, created_at FROM orders WHERE status = 'pending' ORDER BY created_at DESC LIMIT 100",
     lambda n: ()),
    ("disputed_count", 2,
     "SELECT count(*) FROM orders WHERE status = 'disputed'",
     lambda n: ()),
    ("category_sales_7d", 1,
     "SELECT p.category, sum(oi.quantity * oi.unit_price) FROM orders o JOIN order_items oi ON oi.order_id = o.id "
     "JOIN products p ON p.id = oi.product_id WHERE o.created_at >= date_trunc('day', now()) - interval '7 days' "
     "GROUP BY p.category ORDER BY 2 DESC",
     lambda n: ()),
    ("order_items_of_order", 25,
     "SELECT oi.product_id, oi.quantity, oi.unit_price FROM order_items oi WHERE oi.order_id = %s",
     lambda n: (random.randint(1, n["orders"]),)),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=0, help="이 시간 동안 실행 (기본: --iterations 사용)")
    ap.add_argument("--iterations", type=int, default=300, help="실행 횟수 (--seconds 가 없을 때)")
    ap.add_argument("--seed", type=int, default=42, help="난수 시드 (같은 순서로 재현)")
    ap.add_argument("--timeout", type=int, default=120, help="statement_timeout 초")
    args = ap.parse_args()
    random.seed(args.seed)

    conn = labenv.pg_connect(autocommit=True)
    conn.execute("SET application_name = 'workload'")
    labenv.set_guc(conn, "statement_timeout", f"{args.timeout}s")
    n = {"orders": conn.execute("SELECT max(id) FROM orders").fetchone()[0],
         "users": conn.execute("SELECT max(id) FROM users").fetchone()[0]}

    names = [q[0] for q in QUERIES]
    weights = [q[1] for q in QUERIES]
    counts, times = Counter(), Counter()
    t_start = time.perf_counter()
    done = 0
    try:
        while True:
            if args.seconds and time.perf_counter() - t_start >= args.seconds:
                break
            if not args.seconds and done >= args.iterations:
                break
            name, _, sql, params = random.choices(QUERIES, weights=weights)[0]
            t0 = time.perf_counter()
            conn.execute(sql, params(n)).fetchall()
            dt = time.perf_counter() - t0
            counts[name] += 1
            times[name] += dt
            done += 1
            if done % 100 == 0:
                print(f"\r  {done} queries, {time.perf_counter() - t_start:.0f}s", end="", flush=True)
    except KeyboardInterrupt:
        pass
    elapsed = time.perf_counter() - t_start
    print(f"\n\n총 {done} 쿼리, {elapsed:.1f}s, {done / elapsed:.1f} queries/s")
    print(f"{'query':<24}{'calls':>8}{'total_s':>10}{'mean_ms':>10}")
    for name in names:
        if counts[name]:
            print(f"{name:<24}{counts[name]:>8}{times[name]:>10.2f}{1000 * times[name] / counts[name]:>10.2f}")
    print("\n이제 make sql FILE=labs/02-slow-query/pgss_top.sql 로 서버 쪽 통계를 확인하세요.")


if __name__ == "__main__":
    main()
