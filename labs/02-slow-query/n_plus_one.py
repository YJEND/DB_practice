#!/usr/bin/env python3
"""
N+1 재현 및 비교 하네스.

  .venv/bin/python labs/02-slow-query/n_plus_one.py --mode naive
  .venv/bin/python labs/02-slow-query/n_plus_one.py --mode mine          # my_solution.py 구현 후
  .venv/bin/python labs/02-slow-query/n_plus_one.py --mode naive --rtt-ms 5   # 왕복 지연 흉내

출력: 실행 시간, 실행된 SQL 문 수, (mine 모드일 때) naive 와 결과 동일 여부
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))
import labenv  # noqa: E402


class CountingConn:
    """conn.execute 호출 수를 세는 얇은 래퍼 (+ 선택적 RTT 지연)"""

    def __init__(self, conn, rtt_ms: float):
        self._conn, self.rtt, self.calls = conn, rtt_ms / 1000, 0

    def execute(self, *a, **kw):
        self.calls += 1
        if self.rtt:
            time.sleep(self.rtt)
        return self._conn.execute(*a, **kw)

    def cursor(self, *a, **kw):
        return self._conn.cursor(*a, **kw)


def fetch_naive(conn, limit: int) -> list[dict]:
    """전형적인 N+1: 주문 목록 1번 + 주문마다 유저 1번 + 주문마다 상품 목록 1번 + 상품마다 상품 정보 1번"""
    orders = conn.execute(
        "SELECT id, user_id, status, total_amount, created_at FROM orders ORDER BY created_at DESC, id DESC LIMIT %s",
        (limit,)).fetchall()
    result = []
    for oid, uid, status, total, created in orders:
        u = conn.execute("SELECT id, name, email, tier FROM users WHERE id = %s", (uid,)).fetchone()
        items = conn.execute(
            "SELECT product_id, quantity, unit_price FROM order_items WHERE order_id = %s ORDER BY product_id, id",
            (oid,)).fetchall()
        item_dicts = []
        for pid, qty, price in items:
            p = conn.execute("SELECT name, category FROM products WHERE id = %s", (pid,)).fetchone()
            item_dicts.append({"product_id": pid, "product_name": p[0], "category": p[1],
                               "quantity": qty, "unit_price": price})
        result.append({"order_id": oid, "status": status, "total_amount": total, "created_at": created,
                       "user": {"id": u[0], "name": u[1], "email": u[2], "tier": u[3]},
                       "items": item_dicts})
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["naive", "mine"], default="naive")
    ap.add_argument("--limit", type=int, default=300, help="가져올 주문 수")
    ap.add_argument("--rtt-ms", type=float, default=0, help="쿼리마다 인위적 왕복 지연(ms)")
    args = ap.parse_args()

    raw = labenv.pg_connect(autocommit=True)
    raw.execute("SET application_name = 'n_plus_one'")
    conn = CountingConn(raw, args.rtt_ms)

    if args.mode == "mine":
        import my_solution
        fn = my_solution.fetch_orders_with_details
    else:
        fn = fetch_naive

    t0 = time.perf_counter()
    result = fn(conn, args.limit)
    elapsed = time.perf_counter() - t0
    n_items = sum(len(o["items"]) for o in result)
    print(f"mode={args.mode} limit={args.limit} rtt={args.rtt_ms}ms")
    print(f"  주문 {len(result)}건, 아이템 {n_items}개")
    print(f"  실행 시간: {elapsed * 1000:.1f} ms")
    print(f"  실행된 SQL 수: {conn.calls}")

    if args.mode == "mine":
        expected = fetch_naive(CountingConn(raw, 0), args.limit)
        if result == expected:
            print("  검증: naive 결과와 동일 ✔")
        else:
            print("  검증: naive 결과와 다름 ✘  (순서, 필드 이름, 타입(Decimal/datetime) 을 확인하세요)")
            for i, (a, b) in enumerate(zip(result, expected)):
                if a != b:
                    print(f"    첫 차이 index={i}\n      mine    ={str(a)[:200]}\n      expected={str(b)[:200]}")
                    break
            if len(result) != len(expected):
                print(f"    길이 차이: mine={len(result)} expected={len(expected)}")


if __name__ == "__main__":
    main()
