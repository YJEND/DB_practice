#!/usr/bin/env python3
"""
measure.py 결과(JSON) 두 개를 비교해 record.md 에 붙여넣을 수 있는 마크다운 표를 출력합니다.

사용 예
  .venv/bin/python tools/compare.py q1_before q1_after            # label 로 지정 → results/ 에서 가장 최근 파일을 찾음
  .venv/bin/python tools/compare.py results/2026-09-29/101010_q1_before.json results/2026-09-29/102020_q1_after.json
  .venv/bin/python tools/compare.py q1_before q1_after --date 2026-09-29
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labenv  # noqa: E402


def find_result(ref: str, date: str | None) -> Path:
    p = Path(ref)
    if p.suffix == ".json" and p.exists():
        return p
    root = labenv.REPO_ROOT / "results"
    dirs = [root / date] if date else sorted(root.glob("????-??-??"), reverse=True)
    for d in dirs:
        matches = sorted(d.glob(f"*_{ref}.json"), reverse=True)
        if matches:
            return matches[0]
    sys.exit(f"결과를 찾을 수 없음: {ref}  (results/ 아래 *_{ref}.json)")


def pct(before, after):
    if before in (None, 0) or after is None:
        return ""
    return f"{(after - before) / before * 100:+.1f}%"


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return f"{v:,}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--date", help="results/YYYY-MM-DD 폴더 지정 (label 로 찾을 때)")
    args = ap.parse_args()

    pb, pa = find_result(args.before, args.date), find_result(args.after, args.date)
    b, a = json.loads(pb.read_text()), json.loads(pa.read_text())

    rows = [("wall clock median (ms)", b["wall_ms"]["median"], a["wall_ms"]["median"]),
            ("wall clock min (ms)", b["wall_ms"]["min"], a["wall_ms"]["min"])]
    if b.get("explain") and a.get("explain"):
        eb, ea = b["explain"], a["explain"]
        rows += [("execution median (ms)", eb["execution_ms"]["median"], ea["execution_ms"]["median"]),
                 ("planning median (ms)", eb["planning_ms"]["median"], ea["planning_ms"]["median"])]
        for k in eb["buffers"]:
            rows.append((k.lower(), eb["buffers"].get(k, 0), ea["buffers"].get(k, 0)))
    rows.append(("rows returned", b.get("rows_returned"), a.get("rows_returned")))

    print(f"before: {pb.relative_to(labenv.REPO_ROOT)}  ({b['timestamp']})")
    print(f"after : {pa.relative_to(labenv.REPO_ROOT)}  ({a['timestamp']})")
    if b["settings"] != a["settings"]:
        print(f"주의: 세션 설정이 다릅니다\n  before={b['settings']}\n  after ={a['settings']}")
    print()
    print(f"| 항목 | Before ({b['label']}) | After ({a['label']}) | 변화 |")
    print("|---|---:|---:|---:|")
    for name, vb, va in rows:
        print(f"| {name} | {fmt(vb)} | {fmt(va)} | {pct(vb, va) if isinstance(vb, (int, float)) and isinstance(va, (int, float)) else ''} |")


if __name__ == "__main__":
    main()
