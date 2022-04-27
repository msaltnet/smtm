"""이동 평균선을 이용한 기본 전략 StrategySma0 클래스"""

import copy
from datetime import datetime
import math
import pandas as pd
import numpy as np
from .strategy import Strategy
from .log_manager import LogManager
from .date_converter import DateConverter


class StrategySma0(Strategy):
    """
    이동 평균선을 이용한 기본 전략

    is_intialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    current_process: 현재 진행해야 할 매매 타입, buy, sell
    process_unit: 분할 매매를 진행할 단위
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    SHORT = 10
    MID = 40
    LONG = 60
    STEP = 1
    NAME = "SMA0-I"
    STD_K = 25
    STD_RATIO = 0.00015
    PREDICT_N = 3

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0
        self.asset_amount = 0
        self.min_price = 0
        self.result = []
        self.request = None
        self.current_process = "ready"
        self.closing_price_list = []
        self.process_unit = (0, 0)  # budget and amount
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.cross_info = [{"price": 0, "index": 0}, {"price": 0, "index": 0}]
        self.add_spot_callback = None

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
        self.__update_process(info)

    @staticmethod
    def _get_deviation_ratio(std, last):
        if last == 0:
            return 0
        ratio = std / last * 1000000
        return math.floor(ratio) / 1000000

    def __add_drawing_spot(self, date_time, value):
        if self.add_spot_callback is not None:
            self.add_spot_callback(date_time, value)

    def __update_process(self, info):
        try:
            current_price = info["closing_price"]
            current_idx = len(self.closing_price_list)
            self.logger.info(f"# update process :: {current_idx}")
            self.closing_price_list.append(current_price)
            feeded_list = copy.deepcopy(self.closing_price_list)
            for i in range(self.PREDICT_N):
                feeded_list.append(current_price)

            sma_short = pd.Series(feeded_list).rolling(self.SHORT).mean().values[-1]
            sma_mid = pd.Series(feeded_list).rolling(self.MID).mean().values[-1]
            sma_long_list = pd.Series(feeded_list).rolling(self.LONG).mean().values
            sma_long = sma_long_list[-1]

            self.logger.debug(f"[SMA] Start current index {current_idx}")
            if np.isnan(sma_long) or current_idx + 1 < self.LONG:
                return

            if sma_short > sma_mid > sma_long and self.current_process != "buy":
                is_skip = False
                self.current_process = "buy"
                self.process_unit = (round(self.balance / self.STEP), 0)

                self.logger.debug(
                    f"[SMA] Try to buy {sma_short} {sma_mid} {sma_long}, price: {self.process_unit[0]}"
                )
                if current_idx > self.LONG:
                    deviation_count = current_idx - self.LONG
                    if deviation_count > self.STD_K:
                        deviation_count = self.STD_K

                    std_ratio = self._get_deviation_ratio(
                        np.std(sma_long_list[-deviation_count:]), sma_long_list[-1]
                    )

                    if std_ratio > self.STD_RATIO:
                        self.cross_info[1] = {"price": 0, "index": current_idx}
                        self.logger.debug(f"[SMA] SKIP BUY !!! === Stand deviation:{std_ratio:.6f}")
                        is_skip = True

                self.__add_drawing_spot(info["date_time"], current_price)
            elif sma_short < sma_mid < sma_long and self.current_process != "sell":
                self.current_process = "sell"
                self.process_unit = (0, self.asset_amount / self.STEP)
                self.logger.debug(
                    f"[SMA] Try to sell {sma_short} {sma_mid} {sma_long}, amout: {self.process_unit[1]}"
                )
                self.__add_drawing_spot(info["date_time"], current_price)
            else:
                return
            self.cross_info[0] = self.cross_info[1]
            self.cross_info[1] = {"price": current_price, "index": current_idx}

        except (KeyError, TypeError) as err:
            self.logger.warning(f"invalid info: {err}")

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
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            if result["msg"] == "success":
                if result["type"] == "buy":
                    self.asset_amount = round(self.asset_amount + amount, 6)
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)

            self.logger.info(f"[RESULT] id: {result['request']['id']} ================")
            self.logger.info(f"type: {result['type']}, msg: {result['msg']}")
            self.logger.info(f"price: {price}, amount: {amount}")
            self.logger.info(f"balance: {self.balance}, asset_amount: {self.asset_amount}")
            self.logger.info("================================================")
            self.result.append(copy.deepcopy(result))
        except (AttributeError, TypeError) as msg:
            self.logger.error(msg)

    def get_request(self):
        """이동 평균선을 이용한 기본 전략

        장기 이동 평균선과 단기 이동 평균선이 교차할 때부터 n회에 걸쳐 매매 주문 요청
        교차 지점과 거래 단위는 update_trading_info에서 결정
        사전에 결정된 정보를 바탕으로 매매 요청 생성
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
            last_data = self.data[-1]
            now = datetime.now().strftime(self.ISO_DATEFORMAT)

            if self.is_simulation:
                last_dt = datetime.strptime(self.data[-1]["date_time"], self.ISO_DATEFORMAT)
                now = last_dt.isoformat()

            if last_data is None:
                return [
                    {
                        "id": DateConverter.timestamp_id(),
                        "type": "buy",
                        "price": 0,
                        "amount": 0,
                        "date_time": now,
                    }
                ]

            request = None
            if self.cross_info[0]["price"] <= 0 or self.cross_info[1]["price"] <= 0:
                request = None
            elif self.current_process == "buy":
                request = self.__create_buy()
            elif self.current_process == "sell":
                request = self.__create_sell()

            if request is None:
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
            request["date_time"] = now
            self.logger.info(f"[REQ] id: {request['id']} : {request['type']} ==============")
            self.logger.info(f"price: {request['price']}, amount: {request['amount']}")
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
            final_requests.append(request)
            return final_requests
        except (ValueError, KeyError) as msg:
            self.logger.error(f"invalid data {msg}")
        except IndexError:
            self.logger.error("empty data")
        except AttributeError as msg:
            self.logger.error(msg)

    def __create_buy(self):
        budget = self.process_unit[0]
        if budget > self.balance:
            budget = self.balance

        budget -= budget * self.COMMISSION_RATIO
        price = float(self.data[-1]["closing_price"])
        amount = budget / price

        # 소숫점 4자리 아래 버림
        amount = math.floor(amount * 10000) / 10000
        final_value = amount * price

        if self.min_price > budget or self.process_unit[0] <= 0 or final_value > self.balance:
            self.logger.info(f"target_budget is too small or invalid unit {self.process_unit}")
            if self.is_simulation:
                return {
                    "id": DateConverter.timestamp_id(),
                    "type": "buy",
                    "price": 0,
                    "amount": 0,
                }
            return None

        return {
            "id": DateConverter.timestamp_id(),
            "type": "buy",
            "price": price,
            "amount": amount,
        }

    def __create_sell(self):
        amount = self.process_unit[1]
        if amount > self.asset_amount:
            amount = self.asset_amount

        # 소숫점 4자리 아래 버림
        amount = math.floor(amount * 10000) / 10000

        price = float(self.data[-1]["closing_price"])
        total_value = price * amount

        if amount <= 0 or total_value < self.min_price:
            self.logger.info(f"asset is too small or invalid unit {self.process_unit}")
            if self.is_simulation:
                return {
                    "id": DateConverter.timestamp_id(),
                    "type": "sell",
                    "price": 0,
                    "amount": 0,
                }
            return None

        return {
            "id": DateConverter.timestamp_id(),
            "type": "sell",
            "price": price,
            "amount": amount,
        }

    def initialize(self, budget, min_price=5000, add_spot_callback=None):
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
