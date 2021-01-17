"""거래 결과"""
import time


class TradingResult:
    """
    거래 요청의 결과 정보를 담고 있는 읽기 전용 클래스

    request_id: 요청 정보 id
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    msg: 거래 결과 메세지
    balance: 거래 후 계좌 현금 잔고
    """

    def __init__(self, request_id, trading_type, price, amount, msg="", balance=None):
        self.request_id = request_id
        self.type = trading_type
        self.price = price
        self.amount = amount
        self.msg = msg
        self.balance = balance
        self.timestamp = time.time()
