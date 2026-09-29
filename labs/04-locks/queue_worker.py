#!/usr/bin/env python3
"""
작업 큐 동시성 하네스 (FOR UPDATE / SKIP LOCKED 실습).

  make sql FILE=labs/04-locks/setup.sql
  .venv/bin/python labs/04-locks/queue_worker.py --sql labs/04-locks/pick_naive.sql --workers 8 --work-ms 5

집기 SQL 의 마지막 문장이 돌려주는 첫 컬럼 = 작업 id. 0행이면 큐가 비었다고 보고 워커 종료.
집은 뒤 --work-ms 동안 대기(처리 흉내) 후 같은 트랜잭션에서 done 표시 → COMMIT.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))
import labenv  # noqa: E402
from _harness import load_statements, run_statements, percentile  # noqa: E402

MARK_DONE = "UPDATE lab04_jobs SET status = 'done', done_at = now(), locked_by = %(worker)s WHERE id = %(job)s"


def worker(idx, stmts, args, out, lock, barrier):
    import psycopg

    conn = labenv.pg_connect(autocommit=False)
    conn.execute(f"SET application_name = 'queue_w{idx}'")
    conn.commit()
    cur = conn.cursor()
    claimed, pick_lat, errors = [], [], Counter()
    barrier.wait()
    empty_streak = 0
    while empty_streak < 3:
        params = {"worker": f"w{idx}"}
        t0 = time.perf_counter()
        try:
            rows, _ = run_statements(cur, stmts, params)
            pick_lat.append(time.perf_counter() - t0)
            if not rows:
                conn.rollback()
                empty_streak += 1
                continue
            empty_streak = 0
            job = rows[0][0]
            time.sleep(args.work_ms / 1000)
            cur.execute(MARK_DONE, {"worker": f"w{idx}", "job": job})
            conn.commit()
            claimed.append(job)
        except psycopg.Error as e:
            conn.rollback()
            errors[e.sqlstate or "?????"] += 1
    conn.close()
    with lock:
        out["claims"][idx] = claimed
        out["pick_lat"].extend(pick_lat)
        out["errors"].update(errors)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sql", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--work-ms", type=float, default=5, help="작업 하나 처리 시간 흉내")
    args = ap.parse_args()

    stmts = load_statements(args.sql)
    setup = labenv.pg_connect(autocommit=True)
    total = setup.execute("SELECT count(*) FROM lab04_jobs").fetchone()[0]
    pending = setup.execute("SELECT count(*) FROM lab04_jobs WHERE status = 'pending'").fetchone()[0]
    if pending == 0:
        sys.exit("pending 작업이 없습니다. make sql FILE=labs/04-locks/setup.sql 로 초기화하세요.")

    out = {"claims": {}, "pick_lat": [], "errors": Counter()}
    lock, barrier = threading.Lock(), threading.Barrier(args.workers)
    threads = [threading.Thread(target=worker, args=(i, stmts, args, out, lock, barrier)) for i in range(args.workers)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0

    owners = defaultdict(list)
    for w, jobs in out["claims"].items():
        for j in jobs:
            owners[j].append(w)
    dup_jobs = {j: ws for j, ws in owners.items() if len(ws) > 1}
    processed = sum(len(v) for v in out["claims"].values())
    done = setup.execute("SELECT count(*) FROM lab04_jobs WHERE status = 'done'").fetchone()[0]
    left = setup.execute("SELECT count(*) FROM lab04_jobs WHERE status <> 'done'").fetchone()[0]
    lat = [x * 1000 for x in out["pick_lat"]]

    print(f"\nsql={args.sql} workers={args.workers} work={args.work_ms}ms  (pending {pending} / total {total})")
    print(f"  워커별 처리 수      : {[len(out['claims'].get(i, [])) for i in range(args.workers)]}")
    print(f"  처리 시도 합계      : {processed}")
    print(f"  중복 처리된 작업 수 : {len(dup_jobs)}" + ("  <-- 문제" if dup_jobs else "  OK") +
          (f"   예: {dict(list(dup_jobs.items())[:3])}" if dup_jobs else ""))
    print(f"  DB 에서 done 인 작업: {done}   아직 done 이 아닌 작업: {left}")
    print(f"  에러                : {dict(out['errors']) or '없음'}")
    print(f"  소요 {elapsed:.2f}s, 처리량 {processed / elapsed:.0f} jobs/s, "
          f"집기 지연 p50={percentile(lat, 50):.1f}ms p95={percentile(lat, 95):.1f}ms max={max(lat) if lat else 0:.1f}ms")


if __name__ == "__main__":
    main()
