"""
공통 헬퍼: .env 를 읽어 PostgreSQL / Redis 접속 정보를 만듭니다.
tools/ 와 labs/*/ 의 스크립트가 모두 이 모듈을 씁니다.

우선순위: 환경변수 DATABASE_URL > 환경변수 POSTGRES_* > .env 파일 > 기본값(lab/lab@localhost:5432)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


def load_dotenv(path: Path = ENV_FILE) -> dict[str, str]:
    """아주 단순한 .env 파서 (KEY=VALUE, # 주석). 이미 있는 환경변수는 덮어쓰지 않습니다."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _get(key: str, default: str) -> str:
    return os.environ.get(key) or load_dotenv().get(key) or default


def pg_dsn() -> str:
    """psycopg 용 DSN. 컨테이너 밖(호스트)에서 접속하므로 host 는 localhost 입니다."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return (
        f"host=localhost port={_get('POSTGRES_PORT', '5432')} "
        f"user={_get('POSTGRES_USER', 'lab')} password={_get('POSTGRES_PASSWORD', 'lab')} "
        f"dbname={_get('POSTGRES_DB', 'lab')}"
    )


def redis_kwargs() -> dict:
    return {"host": "localhost", "port": int(_get("REDIS_PORT", "6379")), "decode_responses": True}


_GUC_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def set_guc(conn_or_cur, key: str, value) -> None:
    """SET <key> = '<value>'.  SET 은 바인드 파라미터($1)를 못 쓰므로 이름은 검증하고 값은 리터럴로 인용합니다."""
    from psycopg import sql

    key = key.strip()
    if not _GUC_NAME.match(key):
        raise ValueError(f"잘못된 설정 이름: {key!r}")
    conn_or_cur.execute(sql.SQL("SET {} = {}").format(sql.SQL(key), sql.Literal(str(value).strip())))


def apply_settings(conn_or_cur, settings: list[str]) -> None:
    """['work_mem=64MB', 'enable_seqscan=off'] 형태를 순서대로 SET"""
    for kv in settings:
        k, _, v = kv.partition("=")
        set_guc(conn_or_cur, k, v)


def pg_connect(**kw):
    import psycopg  # 지연 import: redis 만 쓰는 스크립트가 psycopg 없이도 돌게

    return psycopg.connect(pg_dsn(), **kw)


def redis_connect():
    import redis

    return redis.Redis(**redis_kwargs())


def results_dir(date: str | None = None) -> Path:
    """results/YYYY-MM-DD/ 를 만들어 돌려줍니다."""
    from datetime import datetime

    d = date or datetime.now().strftime("%Y-%m-%d")
    p = REPO_ROOT / "results" / d
    p.mkdir(parents=True, exist_ok=True)
    return p
