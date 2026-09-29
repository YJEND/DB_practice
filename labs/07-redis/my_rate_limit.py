"""
Part C 과제: rate limiter 구현. 두 함수 모두 "이번 요청을 허용하면 True" 를 돌려줍니다.

  r: redis.Redis (decode_responses=True)
  key: 유저/클라이언트 식별자 (예: "rl:user:42")  — 키 이름 규칙은 자유
  limit: window_sec 동안 허용할 최대 요청 수
"""


def is_allowed_fixed(r, key: str, limit: int, window_sec: int) -> bool:
    raise NotImplementedError("고정 윈도우를 구현하세요")


def is_allowed_sliding(r, key: str, limit: int, window_sec: int) -> bool:
    raise NotImplementedError("슬라이딩 윈도우를 구현하세요")
