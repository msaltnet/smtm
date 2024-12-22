import copy
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from .strategy import Strategy
from ..log_manager import LogManager
from ..date_converter import DateConverter


class StrategySmaMl(Strategy):
    """
    이동 평균선을 이용한 기본 전략에 간단한 ML을 추가

    SHORT, MID, LONG 세개의 이동 평균선을 계산한다

    매수 조건
    SHORT > MID > LONG 조건을 만족하고, 기울기가 양수일때, 직전 매도 후 WAITING_STABLE 만큼 지났을때

    매도 조건
    SHORT < MID < LONG 조건을 만족할 때
    또는 손절 가격에 도달 하고 SHORT < MID 일때

    Adding simple ML to a basic strategy using moving average lines

    Calculate three moving average lines: SHORT, MID, LONG

    Buy condition
    When SHORT > MID > LONG conditions are met, the slope is positive, and WAITING_STABLE has passed since the last sell.

    Sell condition
    When the condition SHORT < MID < LONG is fulfilled
    or when the stop loss price is reached and SHORT < MID

    is_intialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    current_process: 현재 진행해야 할 매매 타입, buy, sell
    process_unit: 분할 매매를 진행할 단위
    lower_list: 지지포인트 (date_time, price)
    upper_list: 저항포인트 (date_time, price)
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    SHORT = 10
    MID = 40
    LONG = 120
    STEP = 1
    NAME = "SML-R7-1126"
    CODE = "SML"
    M_LR_COUNT = 40
    L_LR_COUNT = 40
    LR_FIT_SCORE = 0.7
    WAITING_STABLE = 40
    TREND_WIDTH = 60
    MIN_MARGIN = 0.002
    SPOIL_LIMIT = 2
    LR_LOWER_LIMIT = -0.0000068
    LR_MID_LIMIT = -0.0000027
    LR_UPPER_LIMIT = 0.000014

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
        self.request = None
        self.current_process = "ready"
        self.closing_price_list = []
        self.process_unit = (0, 0)  # budget and amount
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.cross_info = [{"price": 0, "index": 0}, {"price": 0, "index": 0}]
        self.add_spot_callback = None
        self.lower_list = []
        self.upper_list = []
        self.last_lower = None
        self.last_upper = None

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
        self.lower_list = []
        self.upper_list = []

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
        self.__update_process(target)

    def __add_drawing_spot(self, date_time, value):
        if self.add_spot_callback is not None:
            self.logger.debug(f"[SPOT] {date_time} {value}")
            self.add_spot_callback(date_time, value)

    @staticmethod
    def _get_linear_regression_model(price_list, count):
        """check input data and get linear regression model
        if input data is not enough, return None
        """

        if len(price_list) < count:
            return None
        target_list = price_list[-count:]

        for price in target_list:
            if np.isnan(price):
                return None

        x = np.array(range(len(target_list))).reshape(-1, 1)
        reg = LinearRegression().fit(x, target_list)
        coef = reg.coef_
        score = reg.score(x, target_list)
        return coef, score

    def _is_loss_cut_entered(self, current_price):
        asset_total = self.asset_price * self.asset_amount
        if asset_total < self.min_price:
            return False

        if self.asset_price * (1 - self.MIN_MARGIN) > current_price:
            self.logger.info(f"[loss cut] loss! {current_price}")
            return True

        return False

    def __update_process(self, info):
        try:
            current_price = info["closing_price"]
            current_idx = len(self.closing_price_list)
            self.logger.info(f"# update process :: {current_idx}")
            self.closing_price_list.append(current_price)

            sma_short_list = (
                pd.Series(self.closing_price_list).rolling(self.SHORT).mean().values
            )
            sma_short = sma_short_list[-1]
            sma_mid_list = (
                pd.Series(self.closing_price_list).rolling(self.MID).mean().values
            )
            sma_mid = sma_mid_list[-1]
            sma_long_list = (
                pd.Series(self.closing_price_list).rolling(self.LONG).mean().values
            )
            sma_long = sma_long_list[-1]

            if np.isnan(sma_long) or current_idx <= self.LONG:
                return

            # linear regression
            mid_lr = self._get_linear_regression_model(sma_mid_list, self.M_LR_COUNT)
            long_lr = self._get_linear_regression_model(sma_long_list, self.L_LR_COUNT)

            if mid_lr is None or long_lr is None:
                self.logger.debug("[SML] waiting queueing")
                return

            if (sma_short > sma_long > sma_mid) and self.current_process != "buy":
                # for debugging
                # ref_datetime = datetime.strptime(info["date_time"], self.ISO_DATEFORMAT)
                # for i in range(lr_count):
                #     dt = DateConverter.to_iso_string(ref_datetime - timedelta(minutes=lr_count-i))
                #     self.__add_drawing_spot(dt, linear_model.predict([[i]]))

                self.current_process = "buy"
                self.process_unit = (round(self.balance / self.STEP), 0)

                self.logger.debug(f"[SML] Try to buy {sma_short} {sma_mid} {sma_long}")
                self.logger.debug("prev: %s", self.cross_info[0])

                prev_sell_idx = self.cross_info[1]["index"]
                target_cd = self.WAITING_STABLE
                # if linear_model is not None and linear_model.coef_ > 0:
                #     target_cd = 5

                self.logger.debug(
                    f"[SML] LONG LR coef: {long_lr[0]}, score: {long_lr[1]}"
                )
                self.logger.debug(f"[SML] MID LR coef: {mid_lr[0]}, score: {mid_lr[1]}")

                long_lr_ratio = long_lr[0] / current_price
                mid_lr_ratio = mid_lr[0] / current_price

                if long_lr_ratio < self.LR_LOWER_LIMIT:
                    # long 하락 기울기가 클 때 무조건 매수 skip
                    self.cross_info[1] = {"price": 0, "index": current_idx}
                    self.logger.debug(f"[SML] SKIP BUY === Long down term {long_lr[0]}")
                elif long_lr_ratio < self.LR_MID_LIMIT and mid_lr_ratio < 0:
                    # long 하락 기울기이고, mid가 하락 기울기일때 매수 skip
                    self.cross_info[1] = {"price": 0, "index": current_idx}
                    self.logger.debug(
                        f"[SML] SKIP BUY === Long, Mid down term {long_lr[0]} {mid_lr[0]}"
                    )
                elif mid_lr_ratio < 0 and mid_lr[1] > self.LR_FIT_SCORE:
                    # mid 하락 기울기일때 무조건 매수 skip
                    self.cross_info[1] = {"price": 0, "index": current_idx}
                    self.logger.debug("[SML] SKIP BUY === Mid down term")
                elif prev_sell_idx + target_cd > current_idx:
                    # 매도 후 일정 기간 내에 재매수 방지
                    # self.cross_info[1] = {"price": 0, "index": current_idx}
                    # self.logger.debug(f"[SML] SKIP BUY === Too early {prev_sell_idx}")
                    if (
                        long_lr_ratio > self.LR_UPPER_LIMIT
                        and long_lr[1] > self.LR_FIT_SCORE
                    ):
                        # long 상승 기울기일때는 매수 skip 하지 않음
                        self.logger.debug(
                            f"[SML] no SKIP due to strong Long! {prev_sell_idx}"
                        )
                    else:
                        self.cross_info[1] = {"price": 0, "index": current_idx}
                        self.logger.debug(
                            f"[SML] SKIP BUY === Too early {prev_sell_idx}"
                        )
            elif (
                sma_short < sma_mid < sma_long
                # sma_short < sma_long and sma_mid < sma_long
                or (sma_short < sma_mid and self._is_loss_cut_entered(current_price))
            ) and self.current_process != "sell":
                self.current_process = "sell"
                self.process_unit = (0, self.asset_amount / self.STEP)
                self.logger.debug(
                    f"[SML] Try to sell {sma_short} {sma_mid} {sma_long}, amout: {self.process_unit[1]}"
                )
            else:
                return

            self.__add_drawing_spot(info["date_time"], current_price)
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

    def _is_not_spoiled(self, index):
        """check request index is too old, so spoiled
        요청 index가 너무 오래되어서 유효한지 확인, 오래 체결안되는 경우에 대한 예외처리
        """
        current_idx = len(self.closing_price_list)
        not_spoiled = current_idx - index < self.SPOIL_LIMIT
        if not_spoiled is False:
            self.logger.info(f"Spoiled! current_idx: {current_idx}, index: {index}")
        return not_spoiled

    def get_request(self):
        """
        이동 평균선을 이용한 기본 전략

        장기 이동 평균선과 단기 이동 평균선이 교차할 때부터 n회에 걸쳐 매매 주문 요청
        교차 지점과 거래 단위는 update_trading_info에서 결정
        사전에 결정된 정보를 바탕으로 매매 요청 생성

        Basic strategy using moving average lines

        Requests buy and sell orders n times from the crossing of a long-term moving average line
        with a short-term moving average line.
        Crossing points and trading units are determined in update_trading_info
        Generate trade requests based on predetermined information

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
                last_dt = datetime.strptime(
                    self.data[-1]["date_time"], self.ISO_DATEFORMAT
                )
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

            current_idx = len(self.closing_price_list)
            request = None
            if self.cross_info[0]["price"] <= 0 or self.cross_info[1]["price"] <= 0:
                request = None
            elif self.current_process == "buy" and self._is_not_spoiled(current_idx):
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
            self.logger.info(
                f"[REQ] id: {request['id']} : {request['type']} =============="
            )
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
        final_value = amount * price

        # 소숫점 4자리 아래 버림
        amount = Decimal(str(amount)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

        if (
            self.min_price > budget
            or self.process_unit[0] <= 0
            or final_value > self.balance
        ):
            self.logger.info(
                f"target_budget is too small or invalid unit {self.process_unit}"
            )
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
            "price": str(price),
            "amount": str(amount.normalize()),
        }

    def __create_sell(self):
        amount = self.process_unit[1]
        if amount > self.asset_amount:
            amount = self.asset_amount

        price = float(self.data[-1]["closing_price"])
        total_value = price * amount

        # 소숫점 4자리 아래 버림
        amount = Decimal(str(amount)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

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
            "price": str(price),
            "amount": str(amount.normalize()),
        }
