"""
Part B 과제: 캐시 어사이드 구현.

get_user_summary(pg, r, user_id, ttl)
  - pg: psycopg 연결 (autocommit)   r: redis.Redis (decode_responses=True)
  - 반환: {"orders": int, "total": Decimal 또는 float, "source": "db" | "cache"}
  - DB 원본 쿼리: SELECT count(*), coalesce(sum(total_amount), 0) FROM orders WHERE user_id = %s

on_order_created(r, user_id)
  - 하네스가 해당 유저의 주문을 INSERT 한 직후 호출합니다. 처음엔 비워두고(pass) stale 을 관찰한 뒤 구현하세요.
"""


def get_user_summary(pg, r, user_id: int, ttl: int) -> dict:
    raise NotImplementedError("여기를 구현하세요")


def on_order_created(r, user_id: int) -> None:
    pass
