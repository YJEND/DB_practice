"""
Part C 과제: N+1 없이 같은 결과를 만드는 함수를 구현하세요.
n_plus_one.py --mode mine 이 이 함수를 호출하고, naive 결과와 같은지 검증합니다.

반환 형식 (naive 와 동일해야 함):
  list[dict]  각 원소 = {
      "order_id": int, "status": str, "total_amount": Decimal, "created_at": datetime,
      "user": {"id": int, "name": str, "email": str, "tier": str},
      "items": [ {"product_id": int, "product_name": str, "category": str, "quantity": int, "unit_price": Decimal}, ... ]
        # items 는 product_id 오름차순, 같은 product_id 는 id 오름차순
  }
  주문은 created_at DESC, id DESC 순서로 limit 개
"""


def fetch_orders_with_details(conn, limit: int) -> list[dict]:
    raise NotImplementedError("여기를 구현하세요")
