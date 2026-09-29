"""Lab 04 하네스 공통: SQL 파일을 문장 단위로 실행하는 러너"""
from __future__ import annotations

import re
import time
from pathlib import Path

PARAM_RE = re.compile(r"%\((\w+)\)s")


def load_statements(path: str) -> list[str]:
    text = Path(path).read_text()
    # 주석 줄 제거 후 세미콜론으로 분리
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    stmts = [s.strip() for s in "\n".join(lines).split(";")]
    return [s for s in stmts if s]


def run_statements(cur, stmts: list[str], params: dict, think_s: float = 0.0):
    """문장을 순서대로 실행. 행을 돌려준 문장의 첫 컬럼을 params['last'] 로 넘김.
    반환: (마지막 문장의 rows, 마지막 문장의 rowcount)"""
    rows, rowcount = [], 0
    for i, stmt in enumerate(stmts):
        needed = {k for k in PARAM_RE.findall(stmt)}
        missing = needed - params.keys()
        if missing == {"last"}:
            # 직전 문장이 0행 → 이어지는 문장은 실행할 수 없음 = "품절 / 큐 비었음" 으로 처리
            return [], 0
        if missing:
            raise KeyError(f"SQL 파라미터 {missing} 값이 없습니다. 사용 가능: product_id, worker, last")
        cur.execute(stmt, {k: params[k] for k in needed})
        rowcount = cur.rowcount
        rows = cur.fetchall() if cur.description else []
        if rows:
            params["last"] = rows[0][0]
        if think_s and i < len(stmts) - 1:
            time.sleep(think_s)
    return rows, rowcount


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))
    return s[k]
