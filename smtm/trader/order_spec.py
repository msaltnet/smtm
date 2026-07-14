"""주문 유형(ord_type) 상수와 요청 헬퍼.

기존 요청 스키마 {id, type, price, amount, date_time}에 additive로 얹는
선택 필드 `ord_type` / `trigger` 를 일관되게 다루기 위한 공용 모듈.
"""

LIMIT = "limit"
MARKET = "market"
STOP_LOSS = "stop_loss"
TAKE_PROFIT = "take_profit"
OCO = "oco"

CONDITIONAL_ORD_TYPES = frozenset({STOP_LOSS, TAKE_PROFIT, OCO})


def get_ord_type(request):
    """요청의 ord_type을 반환. 없거나 falsy면 'limit'(기존 동작)."""
    return request.get("ord_type") or LIMIT


def is_conditional(request):
    """조건부 주문(stop_loss/take_profit/oco) 여부."""
    return get_ord_type(request) in CONDITIONAL_ORD_TYPES


def make_rejected_result(request, reason):
    """콜백에 전달할 표준 실패 결과 dict."""
    return {
        "request": request,
        "type": request.get("type"),
        "price": 0,
        "amount": 0,
        "msg": reason,
        "state": "failed",
    }
