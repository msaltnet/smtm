import copy
from datetime import datetime
from .strategy import Strategy
from ..date_converter import DateConverter
from ..log_manager import LogManager


class StrategySas(Strategy):
    """
    특정 상황을 만족하게 되었을 때 알림만을 전달하는 전략, 거래는 진행하지 않음

    Strategy that only delivers alerts when certain conditions are met, no trading is done

    is_intialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    NAME = "Simple Alert Strategy"
    CODE = "SAS"
    ALERT_INTERVAL_TICK = 5

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0
        self.asset_amount = 0
        self.asset_price = 0
        self.min_price = 0
        self.result = []
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.add_spot_callback = None

    def initialize(
        self,
        budget,
        min_price=5000,
        add_spot_callback=None,
        add_line_callback=None,
        alert_callback=None,
    ):
        """
        예산과 최소 거래 가능 금액을 설정한다
        """
        if self.is_intialized:
            return

        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
        self.add_spot_callback = add_spot_callback
        self.alert_callback = alert_callback

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
        target = None
        for item in info:
            if item["type"] == "primary_candle":
                target = item
                break

        if target is None:
            return

        self.data.append(copy.deepcopy(target))
        self._make_alert(info)

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

            price = float(result["price"])
            amount = float(result["amount"])
            total = price * amount
            fee = total * self.COMMISSION_RATIO
            asset_total = self.asset_price * self.asset_amount
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            if result["msg"] == "success":
                if result["type"] == "buy":
                    self.asset_amount = round(self.asset_amount + amount, 6)
                    self.asset_price = round(asset_total + total / self.asset_amount)
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)

            self.logger.info(f"[RESULT] id: {result['request']['id']} ================")
            self.logger.info(f"type: {result['type']}, msg: {result['msg']}")
            self.logger.info(f"price: {price}, amount: {amount}")
            self.logger.info(
                f"balance: {self.balance}, asset_amount: {self.asset_amount}, asset_price {self.asset_price}"
            )
            self.logger.info("================================================")
            self.result.append(copy.deepcopy(result))
        except (AttributeError, TypeError) as msg:
            self.logger.error(msg)

    def get_request(self):
        """
        거래 정보를 생성하지 않기 때문에 항상 None을 반환한다

        Since no trading information is generated, always return None
        """
        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        if self.is_simulation is True:
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

    def _make_alert(self, info):
        """
        거래 정보 기준으로 ALERT_INTERVAL_TICK 마다 한 번씩만 알림을 전달한다

        Deliver an alert only once every ALERT_INTERVAL_TICK based on trading information
        """
        if self.alert_callback is None:
            return

        alert_msg = f"Simple Alert Strategy: {info[-1]['date_time']} {info[-1]['closing_price']}"

        if len(self.data) % self.ALERT_INTERVAL_TICK != 0:
            return

        self.alert_callback(alert_msg)
        self.__add_drawing_spot(info[-1]["date_time"], info[-1]["closing_price"])

    def __add_drawing_spot(self, date_time, value):
        if self.add_spot_callback is not None:
            self.logger.debug(f"[SPOT] {date_time} {value}")
            self.add_spot_callback(date_time, value)
