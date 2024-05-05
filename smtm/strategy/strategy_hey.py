"""이동 평균선, 변동성 돌파 전략등 주요 이벤트 발생시 알림을 전달하는 전략 클래스"""

import copy
from .strategy_sas import StrategySas
from ..log_manager import LogManager
import pandas as pd
import numpy as np


class StrategyHey(StrategySas):
    """
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
        self.closing_price_list = []
        self.buy_price = 0
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
        self._checking_sma(target)

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
            self.logger.debug(f"[HEY] BUY #{current_idx} {sma_short} : {sma_mid} : {sma_long}")
        elif (
            sma_short < sma_mid < sma_long or self._is_loss_cut_entered(current_price)
        ) and self.current_process != "sell":
            self.current_process = "sell"
            self.buy_price = 0
            self.logger.debug(f"[HEY] SELL #{current_idx} {sma_short} : {sma_mid} : {sma_long}")
        else:
            return

        self._make_alert(
            info["date_time"],
            current_price,
            f"[HEY] SMA #{current_idx} {self.current_process} : {current_price}",
        )

    def _is_loss_cut_entered(self, current_price):
        if self.buy_price * (1 - self.MIN_MARGIN) > current_price:
            self.logger.info(f"[loss cut] loss! {current_price}")
            return True

        return False

    def _make_alert(self, date_time, price, msg):
        """
        거래 정보 기준으로 ALERT_INTERVAL_TICK 마다 한 번씩만 알림을 전달한다
        """
        if self.alert_callback is None:
            return

        self.alert_callback(msg)
        self.__add_drawing_spot(date_time, price)

    def __add_drawing_spot(self, date_time, value):
        if self.add_spot_callback is not None:
            self.logger.debug(f"[SPOT] {date_time} {value}")
            self.add_spot_callback(date_time, value)
