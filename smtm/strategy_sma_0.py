"""이동 평균선을 이용한 기본 전략"""

import copy
import time
from datetime import datetime, timedelta
from .strategy import Strategy
from .log_manager import LogManager


class StrategySma0(Strategy):
    """
    이동 평균선을 이용한 기본 전략

    isInitialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0
        self.min_price = 0
        self.result = []
        self.request = None
        self.logger = LogManager.get_logger(__name__)

    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트"""
        if self.is_intialized is not True:
            return
        self.data.append(copy.deepcopy(info))

    def update_result(self, result):
        """요청한 거래의 결과를 업데이트"""
        if self.is_intialized is not True:
            return

        try:
            self.balance = result["balance"]
            self.logger.info(f"[RESULT] id: {result['request_id']} ================")
            self.logger.info(f"type: {result['type']}, msg: {result['msg']}")
            self.logger.info(f"price: {result['price']}, amount: {result['amount']}")
            self.logger.info(f"balance: {self.balance}")
            self.logger.info("================================================")
            self.result.append(copy.deepcopy(result))
        except AttributeError as msg:
            self.logger.warning(msg)

    def get_request(self):
        """이동 평균선을 이용한 기본 전략

        장기 이동 평균선과 단기 이동 평균선이 교차할 때부터 3회에 걸쳐 매매 주문 요청
        Returns:
            {
                "id": 요청 정보 id "1607862457.560075"
                "type": 거래 유형 sell, buy
                "price": 거래 가격
                "amount": 거래 수량
                "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간 +1초
            }
        """
        if self.is_intialized is not True:
            return None

        try:
            last_data = self.data[-1]
            now = datetime.now().strftime(self.ISO_DATEFORMAT)

            if self.is_simulation:
                last_dt = datetime.strptime(self.data[-1]["date_time"], self.ISO_DATEFORMAT)
                now = last_dt.isoformat()

            target_budget = self.budget / 10
            if last_data is None:
                return {
                    "id": str(round(time.time(), 3)),
                    "type": "buy",
                    "price": 0,
                    "amount": 0,
                    "date_time": now,
                }

            if self.min_price > target_budget:
                self.logger.info("target_budget is too small")
                return {
                    "id": str(round(time.time(), 3)),
                    "type": "buy",
                    "price": 0,
                    "amount": 0,
                    "date_time": now,
                }

            if target_budget > self.balance:
                self.logger.info("blance is too small")
                return {
                    "id": str(round(time.time(), 3)),
                    "type": "buy",
                    "price": 0,
                    "amount": 0,
                    "date_time": now,
                }

            target_amount = target_budget / last_data["closing_price"]
            trading_request = {
                "id": str(round(time.time(), 3)),
                "type": "buy",
                "price": last_data["closing_price"],
                "amount": target_amount,
                "date_time": now,
            }
            self.logger.info(f"[REQ] id: {trading_request['id']} =====================")
            self.logger.info(f"type: {trading_request['type']}")
            self.logger.info(
                f"price: {trading_request['price']}, amount: {trading_request['amount']}"
            )
            self.logger.info("================================================")
            return trading_request
        except (ValueError, KeyError):
            self.logger.error("invalid data")
        except IndexError:
            self.logger.error("empty data")
        except AttributeError as msg:
            self.logger.error(msg)

    def initialize(self, budget, min_price=100, is_simulation=True):
        """
        예산과 최소 거래 가능 금액을 설정한다
        """
        if self.is_intialized:
            return

        self.is_intialized = True
        self.is_simulation = is_simulation
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
