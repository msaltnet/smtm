"""분할 매수 후 홀딩 하는 간단한 전략 StrategyBuyAndHold 클래스"""

import copy
import math
from datetime import datetime
from .strategy import Strategy
from .log_manager import LogManager
from .date_converter import DateConverter


class StrategyBuyAndHold(Strategy):
    """
    분할 매수 후 홀딩 하는 간단한 전략

    isInitialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    NAME = "BnH"

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0.0
        self.min_price = 0
        self.result = []
        self.request = None
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}

    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트

        Returns: 거래 정보 딕셔너리
        {
            "market": 거래 시장 종류 BTC
            "date_time": 정보의 기준 시간
            "opening_price": 시작 거래 가격
            "high_price": 최고 거래 가격
            "low_price": 최저 거래 가격
            "closing_price": 마지막 거래 가격
            "acc_price": 단위 시간내 누적 거래 금액
            "acc_volume": 단위 시간내 누적 거래 양
        }
        """
        if self.is_intialized is not True:
            return
        self.data.append(copy.deepcopy(info))

    def update_result(self, result):
        """요청한 거래의 결과를 업데이트

        request: 거래 요청 정보
        result:
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "msg": 거래 결과 메세지
            "state": 거래 상태 requested, done
            "date_time": 시뮬레이션 모드에서는 데이터 시간 +2초
        }
        """
        if self.is_intialized is not True:
            return

        try:
            request = result["request"]
            if result["state"] == "requested":
                self.waiting_requests[request["id"]] = result
                return

            if result["state"] == "done" and request["id"] in self.waiting_requests:
                del self.waiting_requests[request["id"]]

            total = float(result["price"]) * float(result["amount"])
            fee = total * self.COMMISSION_RATIO
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            self.logger.info(f"[RESULT] id: {result['request']['id']} ================")
            self.logger.info(f"type: {result['type']}, msg: {result['msg']}")
            self.logger.info(f"price: {result['price']}, amount: {result['amount']}")
            self.logger.info(f"total: {total}, balance: {self.balance}")
            self.logger.info("================================================")
            self.result.append(copy.deepcopy(result))
        except (AttributeError, TypeError) as msg:
            self.logger.error(msg)

    def get_request(self):
        """
        데이터 분석 결과에 따라 거래 요청 정보를 생성한다

        5번에 걸쳐 분할 매수 후 홀딩하는 전략
        마지막 종가로 처음 예산의 1/5에 해당하는 양 만큼 매수시도
        Returns: 배열에 한 개 이상의 요청 정보를 전달
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
        }]
        """
        if self.is_intialized is not True:
            return None

        try:
            if len(self.data) == 0 or self.data[-1] is None:
                raise UserWarning("data is empty")

            last_closing_price = self.data[-1]["closing_price"]
            now = datetime.now().strftime(self.ISO_DATEFORMAT)

            if self.is_simulation:
                now = self.data[-1]["date_time"]

            target_budget = self.budget / 5
            if target_budget > self.balance:
                target_budget = self.balance

            amount = math.floor((target_budget / last_closing_price) * 10000) / 10000
            trading_request = {
                "id": DateConverter.timestamp_id(),
                "type": "buy",
                "price": last_closing_price,
                "amount": amount,
                "date_time": now,
            }
            total_value = round(float(last_closing_price) * amount)

            if self.min_price > total_value or total_value > self.balance:
                raise UserWarning("total_value or balance is too small")

            self.logger.info(f"[REQ] id: {trading_request['id']} =====================")
            self.logger.info(f"price: {last_closing_price}, amount: {amount}")
            self.logger.info(f"type: buy, total value: {total_value}")
            self.logger.info("================================================")
            final_requests = []
            for request_id in self.waiting_requests:
                self.logger.info(f"cancel request added! {request_id}")
                final_requests.append(
                    {
                        "id": request_id,
                        "type": "cancel",
                        "price": 0,
                        "amount": 0,
                        "date_time": now,
                    }
                )
            final_requests.append(trading_request)
            return final_requests
        except (ValueError, KeyError) as msg:
            self.logger.error(f"invalid data {msg}")
        except IndexError:
            self.logger.error("empty data")
        except AttributeError as msg:
            self.logger.error(msg)
        except UserWarning as msg:
            self.logger.info(msg)
            if self.is_simulation:
                return [
                    {
                        "id": DateConverter.timestamp_id(),
                        "type": "buy",
                        "price": 0,
                        "amount": 0,
                        "date_time": now,
                    }
                ]
            return None

    def initialize(self, budget, min_price=5000, add_spot_callback=None):
        """예산과 최소 거래 가능 금액을 설정한다"""
        if self.is_intialized:
            return

        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
