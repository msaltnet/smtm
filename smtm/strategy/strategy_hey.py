import copy
from .strategy_sas import StrategySas
from ..log_manager import LogManager
import pandas as pd
import numpy as np


class StrategyHey(StrategySas):
    """
    이동 평균선, 변동성 돌파 전략등 주요 이벤트 발생시 알림을 전달하는 전략 클래스
    변동성 돌파 이벤트를 분봉을 기준으로 했을때, 너무 자주 발생됨 -> 주석 처리

    Moving average line, volatility breakout strategy, etc. Strategy class that delivers alerts when major events occur
    Volatility breakout events occur too frequently when based on minute candles -> Commented out

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
    NAME = "Hey Man Strategy"
    CODE = "HEY"
    SMA_SHORT = 10
    SMA_MID = 40
    SMA_LONG = 120
    MIN_MARGIN = 0.002
    ATR_PERIOD = 30
    VOLATILITY_BREAKOUT = 1.5

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
        self.current_process = "ready"
        self.loss_cut_alerted = False
        self.closing_price_list = []
        self.buy_price = 0
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.add_spot_callback = None
        self.add_line_callback = None
        self.true_ranges = []
        self.atr = None
        self.prev_close = None

    def initialize(
        self,
        budget,
        min_price=5000,
        add_spot_callback=None,
        add_line_callback=None,
        alert_callback=None,
    ):
        if self.is_intialized:
            return

        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
        self.add_spot_callback = add_spot_callback
        self.alert_callback = alert_callback
        self.add_line_callback = add_line_callback

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
        self._checking_sma(target)
        # 변동성 돌파 이벤트를 분봉을 기준으로 했을때, 너무 자주 발생됨
        # self._checking_volatility_breakout(target)

    def _checking_sma(self, info):
        current_price = info["closing_price"]
        current_idx = len(self.closing_price_list)
        self.closing_price_list.append(current_price)

        sma_short_list = (
            pd.Series(self.closing_price_list).rolling(self.SMA_SHORT).mean().values
        )
        sma_short = sma_short_list[-1]
        sma_mid_list = (
            pd.Series(self.closing_price_list).rolling(self.SMA_MID).mean().values
        )
        sma_mid = sma_mid_list[-1]
        sma_long_list = (
            pd.Series(self.closing_price_list).rolling(self.SMA_LONG).mean().values
        )
        sma_long = sma_long_list[-1]

        if np.isnan(sma_long) or current_idx <= self.SMA_LONG:
            return

        if (sma_short > sma_long > sma_mid) and self.current_process != "buy":
            self.current_process = "buy"
            self.buy_price = current_price
            self.loss_cut_alerted = False
            self.logger.debug(
                f"[HEY] BUY #{current_idx} {sma_short} : {sma_mid} : {sma_long}"
            )
        elif (sma_short < sma_mid < sma_long) and self.current_process != "sell":
            self.current_process = "sell"
            self.buy_price = 0
            self.loss_cut_alerted = False
            self.logger.debug(
                f"[HEY] SELL #{current_idx} {sma_short} : {sma_mid} : {sma_long}"
            )
        elif (
            self._is_loss_cut_entered(current_price)
            and self.current_process != "sell"
            and not self.loss_cut_alerted
        ):
            self.loss_cut_alerted = True
            self.logger.debug(
                f"[HEY] LOSS CUT #{current_idx} {sma_short} : {sma_mid} : {sma_long}"
            )
        else:
            return

        self._make_alert(
            info["date_time"],
            current_price,
            f"[HEY] SMA #{current_idx} {self.current_process} : {current_price}",
        )

    def _checking_volatility_breakout(self, info):
        self.update_atr_info(info)
        breakout_buy_signal, breakout_sell_signal = self.detect_breakout_signals()
        if breakout_buy_signal or breakout_sell_signal:
            self.logger.debug(
                f"[HEY] BREAKOUT {info['date_time']} {breakout_buy_signal} {breakout_sell_signal}"
            )
            self.logger.debug(
                f"-- {self.atr} {info['closing_price']} {self.prev_close}"
            )
            self._make_alert(
                info["date_time"],
                info["closing_price"],
                f"[HEY] BREAKOUT {info['date_time']} {breakout_buy_signal} {breakout_sell_signal}",
            )

    def update_atr_info(self, new_price_info):
        """
        새로운 거래 정보를 받아서 변동성 돌파 이벤트 정보를 업데이트

        Update volatility breakout event information by receiving new trading information
        """

        if len(self.data) > 1:
            # 이전 거래일 종가
            self.prev_close = self.data[-2]["closing_price"]

            # 새로운 True Range 계산
            current_high = new_price_info["high_price"]
            current_low = new_price_info["low_price"]
            prev_close = self.data[-2]["closing_price"]

            high_low = current_high - current_low
            high_close = abs(current_high - prev_close)
            low_close = abs(current_low - prev_close)

            true_range = max(high_low, high_close, low_close)
            self.true_ranges.append(true_range)

            # 최신 True Range 기반으로 ATR 업데이트
            if len(self.true_ranges) > self.ATR_PERIOD:
                self.true_ranges.pop(0)  # 가장 오래된 True Range 제거

            self.atr = np.mean(self.true_ranges)

    def detect_breakout_signals(self):
        """
        변동성 돌파 신호 감지

        Detecting volatility breakout signals
        """
        if len(self.data) < 2:
            return False, False

        current_price = self.data[-1]
        current_high = current_price["high_price"]
        current_low = current_price["low_price"]

        breakout_buy_signal = (
            current_high > self.prev_close + self.VOLATILITY_BREAKOUT * self.atr
        )
        breakout_sell_signal = (
            current_low < self.prev_close - self.VOLATILITY_BREAKOUT * self.atr
        )

        return breakout_buy_signal, breakout_sell_signal

    def _is_loss_cut_entered(self, current_price):
        if self.buy_price * (1 - self.MIN_MARGIN) > current_price:
            self.logger.info(f"[loss cut] loss! {current_price}")
            return True

        return False

    def _make_alert(self, date_time, price, msg):
        """
        거래 정보 기준으로 ALERT_INTERVAL_TICK 마다 한 번씩만 알림을 전달한다

        Deliver an alert only once every ALERT_INTERVAL_TICK based on trading information
        """
        if self.alert_callback is None:
            return

        self.alert_callback(msg)
        self.__add_drawing_spot(date_time, price)

    def __add_drawing_spot(self, date_time, value):
        if self.add_spot_callback is not None:
            self.logger.debug(f"[SPOT] {date_time} {value}")
            self.add_spot_callback(date_time, value)
