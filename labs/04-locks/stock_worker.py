#!/usr/bin/env python3
"""
재고 차감 동시성 하네스.

  .venv/bin/python labs/04-locks/stock_worker.py --sql labs/04-locks/decrement_naive.sql
  옵션: --workers 10 --iterations 10 --stock 50 --product 1 --think-ms 0
        --isolation {read_committed,repeatable_read,serializable} --retry
        --sql-alt FILE   (홀수 워커는 이 파일 사용: 데드락 유도용)

SQL 파일 규칙은 README 참고. 마지막 문장이 1행 이상 → 판매 성공, 0행 → 품절.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))
import labenv  # noqa: E402
from _harness import load_statements, run_statements, percentile  # noqa: E402

ISO = {"read_committed": "READ COMMITTED", "repeatable_read": "REPEATABLE READ", "serializable": "SERIALIZABLE"}


def worker(idx, stmts, args, stats, lock, barrier):
    import psycopg

    conn = labenv.pg_connect(autocommit=False)
    conn.execute(f"SET application_name = 'stock_w{idx}'")
    conn.execute(f"SET default_transaction_isolation = '{ISO[args.isolation]}'")
    conn.commit()
    cur = conn.cursor()
    local = Counter()
    latencies = []
    barrier.wait()
    for _ in range(args.iterations):
        attempts = 0
        while True:
            attempts += 1
            params = {"product_id": args.product, "worker": f"w{idx}"}
            t0 = time.perf_counter()
            try:
                rows, _ = run_statements(cur, stmts, params, args.think_ms / 1000)
                conn.commit()
                latencies.append(time.perf_counter() - t0)
                local["sold" if rows else "sold_out"] += 1
                break
            except psycopg.Error as e:
                conn.rollback()
                code = e.sqlstate or "?????"
                local[f"err:{code}"] += 1
                if args.retry and code in ("40001", "40P01") and attempts < 20:
                    local["retries"] += 1
                    continue
                break
    conn.close()
    with lock:
        stats["counts"].update(local)
        stats["latencies"].extend(latencies)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sql", required=True)
    ap.add_argument("--sql-alt", help="홀수 워커가 쓸 SQL 파일")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--stock", type=int, default=50, help="시작 재고")
    ap.add_argument("--product", type=int, default=1)
    ap.add_argument("--think-ms", type=float, default=0, help="문장 사이 대기(ms). 경합 창을 넓힘")
    ap.add_argument("--isolation", choices=ISO.keys(), default="read_committed")
    ap.add_argument("--retry", action="store_true", help="40001/40P01 에러 시 재시도")
    args = ap.parse_args()

    stmts_a = load_statements(args.sql)
    stmts_b = load_statements(args.sql_alt) if args.sql_alt else stmts_a

    setup = labenv.pg_connect(autocommit=True)
    products = [args.product] if not args.sql_alt else sorted({args.product, 1, 2})
    setup.execute("UPDATE products SET stock = %s WHERE id = ANY(%s)", (args.stock, products))
    before = setup.execute("SELECT count(*) FROM pg_stat_database WHERE datname = current_database()").fetchone()
    deadlocks_before = setup.execute("SELECT deadlocks FROM pg_stat_database WHERE datname = current_database()").fetchone()[0]

    stats = {"counts": Counter(), "latencies": []}
    lock, barrier = threading.Lock(), threading.Barrier(args.workers)
    threads = [threading.Thread(target=worker, args=(i, stmts_a if i % 2 == 0 else stmts_b, args, stats, lock, barrier))
               for i in range(args.workers)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0

    final = {r[0]: r[1] for r in setup.execute("SELECT id, stock FROM products WHERE id = ANY(%s)", (products,)).fetchall()}
    deadlocks = setup.execute("SELECT deadlocks FROM pg_stat_database WHERE datname = current_database()").fetchone()[0] - deadlocks_before
    c = stats["counts"]
    attempts = args.workers * args.iterations
    sold, sold_out = c["sold"], c["sold_out"]
    errors = {k: v for k, v in c.items() if k.startswith("err:")}

    print(f"\nsql={args.sql}" + (f" alt={args.sql_alt}" if args.sql_alt else ""))
    print(f"workers={args.workers} iterations={args.iterations} attempts={attempts} isolation={ISO[args.isolation]} "
          f"think={args.think_ms}ms retry={args.retry}")
    print(f"  시작 재고            : {args.stock}" + (f"  (products {products})" if len(products) > 1 else ""))
    print(f"  판매 성공 (sold)     : {sold}")
    print(f"  품절 거절 (sold_out) : {sold_out}")
    print(f"  에러                 : {dict(errors) or '없음'}   재시도={c['retries']}   서버 집계 deadlocks={deadlocks}")
    for pid, st in sorted(final.items()):
        print(f"  최종 재고 product {pid}: {st}")
    if not args.sql_alt:
        st = final[args.product]
        oversold = max(0, sold - args.stock)          # 재고보다 많이 팔림
        drift = st - (args.stock - sold)              # 성공 수만큼 줄지 않음 (사라진 차감)
        print(f"  검증: 초과 판매={oversold}  (성공 {sold} - 시작 재고 {args.stock})"
              + ("  <-- 문제" if oversold else "  OK"))
        print(f"        재고 불일치={drift:+d}  (최종 {st} - (시작 {args.stock} - 성공 {sold}))"
              + ("  <-- 문제" if drift else "  OK") + ("   음수 재고!" if st < 0 else ""))
    lat = [x * 1000 for x in stats["latencies"]]
    print(f"  소요 {elapsed:.2f}s, 처리량 {attempts / elapsed:.0f} attempts/s, "
          f"지연 p50={percentile(lat, 50):.1f}ms p95={percentile(lat, 95):.1f}ms max={max(lat) if lat else 0:.1f}ms")


if __name__ == "__main__":
    main()
