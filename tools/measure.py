#!/usr/bin/env python3
"""
쿼리 실행 시간 + EXPLAIN (ANALYZE, BUFFERS) 를 results/YYYY-MM-DD/ 에 저장합니다.
before/after 를 같은 label 로 저장한 뒤 tools/compare.py 로 비교하세요.

사용 예
  .venv/bin/python tools/measure.py --sql labs/01-index-explain/queries/q1_range.sql --label q1_before
  .venv/bin/python tools/measure.py --query "SELECT count(*) FROM orders WHERE status = 'disputed'" --label rare_before
  .venv/bin/python tools/measure.py --sql q.sql --label q_workmem --set work_mem=64MB --set enable_seqscan=off
  .venv/bin/python tools/measure.py --sql upd.sql --label upd --rollback     # UPDATE/DELETE 는 롤백하며 측정

측정 방식
  1) 쿼리를 그대로 --runs 번 실행해 벽시계 시간(ms)의 중앙값/최소값을 구합니다. (EXPLAIN ANALYZE 의 계측 오버헤드가 없는 값)
  2) EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) 을 --runs 번 실행해 Execution/Planning Time, 버퍼 수치를 뽑습니다.
  3) 사람이 읽을 TEXT 포맷 계획을 1번 뽑아 파일에 붙입니다.
  * 첫 실행은 캐시 워밍 성격이 강하므로 --cold 를 주지 않으면 1회 예열 후 측정합니다.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labenv  # noqa: E402

BUFFER_KEYS = [
    "Shared Hit Blocks", "Shared Read Blocks", "Shared Dirtied Blocks", "Shared Written Blocks",
    "Temp Read Blocks", "Temp Written Blocks",
]


def read_query(args) -> str:
    if args.sql:
        text = Path(args.sql).read_text()
    else:
        text = args.query
    # 파일 안의 '-- ' 주석 줄은 유지해도 되지만, 마지막 세미콜론은 EXPLAIN 에 붙일 때 문제라서 제거
    return text.strip().rstrip(";").strip()


def top_node_buffers(plan_json) -> dict:
    root = plan_json[0]["Plan"]
    return {k: root.get(k, 0) for k in BUFFER_KEYS}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sql", help="SQL 파일 경로")
    src.add_argument("--query", help="인라인 SQL")
    ap.add_argument("--label", required=True, help="결과 파일 이름 (예: q1_before)")
    ap.add_argument("--runs", type=int, default=3, help="반복 횟수 (기본 3)")
    ap.add_argument("--set", action="append", default=[], metavar="K=V", help="세션 SET (반복 가능) 예: --set work_mem=64MB")
    ap.add_argument("--rollback", action="store_true", help="트랜잭션 안에서 실행하고 매번 ROLLBACK (DML 측정용)")
    ap.add_argument("--cold", action="store_true", help="예열 실행 생략")
    ap.add_argument("--no-explain", action="store_true", help="EXPLAIN 없이 시간만 측정")
    ap.add_argument("--timeout", type=int, default=600, help="statement_timeout 초 (기본 600)")
    args = ap.parse_args()

    query = read_query(args)
    label = args.label
    out_dir = labenv.results_dir()
    stamp = datetime.now().strftime("%H%M%S")
    out_txt = out_dir / f"{stamp}_{label}.txt"
    out_json = out_dir / f"{stamp}_{label}.json"

    conn = labenv.pg_connect(autocommit=not args.rollback)
    cur = conn.cursor()
    labenv.set_guc(cur, "statement_timeout", f"{args.timeout}s")
    labenv.apply_settings(cur, args.set)
    cur.execute("SELECT version()")
    pg_version = cur.fetchone()[0].split(",")[0]
    cur.execute("SELECT current_setting('work_mem'), current_setting('random_page_cost'), current_setting('shared_buffers'), current_setting('effective_cache_size')")
    work_mem, rpc, shared_buffers, ecs = cur.fetchone()

    def run_once(sql: str, fetch: bool):
        # --rollback 이면 autocommit=False 라 첫 execute 에서 트랜잭션이 열리고, 끝에 ROLLBACK 합니다.
        t0 = time.perf_counter()
        cur.execute(sql)
        rows = cur.fetchall() if (fetch and cur.description is not None) else None  # UPDATE/DELETE 는 결과 행이 없음
        elapsed = (time.perf_counter() - t0) * 1000
        if args.rollback:
            conn.rollback()
        return elapsed, rows

    # 1) 예열
    if not args.cold:
        run_once(query, fetch=True)

    # 2) 벽시계 시간
    wall_times, rowcount = [], None
    for _ in range(args.runs):
        ms, rows = run_once(query, fetch=True)
        wall_times.append(ms)
        rowcount = len(rows) if rows is not None else cur.rowcount

    # 3) EXPLAIN ANALYZE (JSON)  → 수치 추출
    exec_times, plan_times, buffers, text_plan = [], [], {}, ""
    if not args.no_explain:
        for _ in range(args.runs):
            _, rows = run_once(f"EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) {query}", fetch=True)
            pj = rows[0][0]
            if isinstance(pj, str):
                pj = json.loads(pj)
            exec_times.append(pj[0]["Execution Time"])
            plan_times.append(pj[0]["Planning Time"])
            buffers = top_node_buffers(pj)
        _, rows = run_once(f"EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT) {query}", fetch=True)
        text_plan = "\n".join(r[0] for r in rows)

    summary = {
        "label": label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pg_version": pg_version,
        "settings": {"work_mem": work_mem, "random_page_cost": rpc, "shared_buffers": shared_buffers,
                     "effective_cache_size": ecs, "session_set": args.set},
        "runs": args.runs,
        "rows_returned": rowcount,
        "wall_ms": {"median": statistics.median(wall_times), "min": min(wall_times), "all": wall_times},
        "explain": None if args.no_explain else {
            "execution_ms": {"median": statistics.median(exec_times), "min": min(exec_times), "all": exec_times},
            "planning_ms": {"median": statistics.median(plan_times)},
            "buffers": buffers,
        },
        "query": query,
    }

    lines = [
        f"# {label}   {summary['timestamp']}",
        f"# {pg_version}",
        f"# work_mem={work_mem} random_page_cost={rpc} shared_buffers={shared_buffers} effective_cache_size={ecs} session_set={args.set}",
        f"# runs={args.runs} rows_returned={rowcount}",
        "",
        "## 시간 (ms)",
        f"  wall clock   median={summary['wall_ms']['median']:.2f}  min={summary['wall_ms']['min']:.2f}  all={[round(x, 2) for x in wall_times]}",
    ]
    if not args.no_explain:
        e = summary["explain"]
        lines += [
            f"  execution    median={e['execution_ms']['median']:.2f}  min={e['execution_ms']['min']:.2f}",
            f"  planning     median={e['planning_ms']['median']:.3f}",
            "",
            "## 버퍼 (최상위 노드, 8KB 블록)",
        ] + [f"  {k:<24} {v:>12,}" for k, v in buffers.items()] + [
            "",
            "## 쿼리",
            query,
            "",
            "## EXPLAIN (ANALYZE, BUFFERS, SETTINGS)",
            text_plan,
        ]
    else:
        lines += ["", "## 쿼리", query]

    out_txt.write_text("\n".join(lines) + "\n")
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print("\n".join(lines[:12]))
    print(f"\n저장: {out_txt.relative_to(labenv.REPO_ROOT)}")
    print(f"      {out_json.relative_to(labenv.REPO_ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()
