#!/usr/bin/env python3
"""
rate limit 하네스: my_rate_limit 의 구현을 네 가지 시나리오로 검증합니다.

  .venv/bin/python labs/07-redis/rate_limit_harness.py --impl fixed   --limit 100 --window 10
  .venv/bin/python labs/07-redis/rate_limit_harness.py --impl sliding --limit 100 --window 10
  --scenario burst|boundary|steady|concurrent|all (기본 all)
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))
import labenv  # noqa: E402
import my_rate_limit  # noqa: E402


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))] if s else 0


def cmd_count(r):
    return sum(v["calls"] for v in r.info("commandstats").values())


def fresh_key(r, name):
    key = f"rl:{name}:{int(time.time() * 1000)}"
    for k in r.scan_iter(f"{key}*"):
        r.delete(k)
    return key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", choices=["fixed", "sliding"], required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--window", type=int, default=10, help="초. 짧게 잡으면 boundary 시나리오가 빨리 끝남")
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()

    r = labenv.redis_connect()
    fn = my_rate_limit.is_allowed_fixed if args.impl == "fixed" else my_rate_limit.is_allowed_sliding
    L, W = args.limit, args.window
    print(f"impl={args.impl} limit={L} window={W}s\n")

    def call(key):
        try:
            return fn(r, key, L, W)
        except NotImplementedError as e:
            sys.exit(f"my_rate_limit.py 를 먼저 구현하세요: {e}")

    want = args.scenario
    if want in ("burst", "all"):
        key, lat = fresh_key(r, "burst"), []
        c0 = cmd_count(r)
        allowed = 0
        for _ in range(L * 3):
            t0 = time.perf_counter()
            allowed += call(key)
            lat.append((time.perf_counter() - t0) * 1000)
        print(f"[burst]      {L * 3} 요청 즉시 → 허용 {allowed} (기대 {L})   p50={pct(lat, 50):.3f}ms p95={pct(lat, 95):.3f}ms  redis cmds/req={(cmd_count(r) - c0) / (L * 3):.1f}"
              + ("" if allowed == L else "  <-- 확인"))

    if want in ("boundary", "all"):
        key = fresh_key(r, "boundary")
        # 윈도우 경계 직전 0.5초에 L 개, 경계 직후 0.5초에 L 개. 고정 윈도우는 경계를 "초 단위 시각" 으로 잡는 구현이 많으므로
        # 다음 W 의 배수 시각에 맞춰 시작합니다.
        now = time.time()
        edge = (int(now) // W + 1) * W
        if edge - now < 1.0:
            edge += W
        print(f"[boundary]   경계 시각까지 {edge - now:.1f}s 대기...", end="", flush=True)
        time.sleep(max(0, edge - 0.5 - time.time()))
        before = sum(call(key) for _ in range(L))
        time.sleep(max(0, edge + 0.05 - time.time()))
        after = sum(call(key) for _ in range(L))
        print(f"\r[boundary]   경계 직전 0.5s 허용 {before}, 직후 허용 {after} → 약 1초 동안 총 {before + after} (limit {L})")

    if want in ("steady", "all"):
        key = fresh_key(r, "steady")
        rate = max(1, int(L * 1.5 / W))  # 초당 요청 수: limit 의 1.5배 속도
        dur = W * 2
        print(f"[steady]     초당 {rate} 요청을 {dur}s 동안 (limit 의 1.5배 속도)")
        buckets = []
        start = time.time()
        for sec in range(dur):
            ok = 0
            for _ in range(rate):
                ok += call(key)
            buckets.append(ok)
            time.sleep(max(0, start + sec + 1 - time.time()))
        line = "".join("#" if b == rate else ("+" if b else ".") for b in buckets)
        print(f"             초별 허용 수: {buckets}")
        print(f"             (# 전부 허용, + 일부, . 전부 거절) {line}")
        print(f"             총 허용 {sum(buckets)} / {rate * dur}   (윈도우 2개 분량이면 기대 최대 {2 * L}~{3 * L})")

    if want in ("concurrent", "all"):
        key = fresh_key(r, "concurrent")
        n_threads, per = 20, max(1, L * 3 // 20)
        results, lock = [], threading.Lock()

        def worker():
            local = 0
            for _ in range(per):
                local += call(key)
            with lock:
                results.append(local)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        allowed = sum(results)
        print(f"[concurrent] 스레드 {n_threads} × {per} 요청 동시에 → 허용 {allowed} (기대 {L})" + ("" if allowed <= L else "  <-- limit 초과: 원자성 확인"))

    key_sizes = [(k, r.memory_usage(k)) for k in r.scan_iter("rl:*")]
    if key_sizes:
        biggest = max(key_sizes, key=lambda x: x[1] or 0)
        print(f"\n키 {len(key_sizes)}개, 가장 큰 키 {biggest[0]} = {biggest[1]} bytes  (TTL {r.ttl(biggest[0])}s)")


if __name__ == "__main__":
    main()
