"""RSI Relativce Strength Index 상대 강도 지수를 활용한 매매 전략 클래스"""
import copy
import math
from datetime import datetime
import numpy as np
from .strategy import Strategy
from .log_manager import LogManager
from .date_converter import DateConverter


class StrategyRsi(Strategy):
    """
    RSI Relativce Strength Index 상대 강도 지수를 활용한 매매 전략
    http://www.investopedia.com/terms/r/rsi.asp
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    RSI_LOW = 30
    RSI_HIGH = 70
    RSI_COUNT = 14
    NAME = "RSI"

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.rsi_info = None
        self.rsi = []
        self.data = []
        self.result = []
        self.add_spot_callback = None
        self.budget = 0
        self.balance = 0
        self.asset_amount = 0
        self.min_price = 0
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.position = None

    def initialize(self, budget, min_price=100, add_spot_callback=None):
        """예산을 설정하고 초기화한다

        budget: 예산
        min_price: 최소 거래 금액, 거래소의 최소 거래 금액
        add_spot_callback(date_time, value): 그래프에 그려질 spot을 추가하는 콜백 함수
        """
        if self.is_intialized:
            return

        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
        self.add_spot_callback = add_spot_callback

    def get_request(self):
        """현재 업데이트 된 포지션에 따라 거래 요청 정보를 생성한다
        완료되지 않은 거래가 waiting_requests에 있으면 취소 요청한다

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

            if last_data is None or self.position is None:
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

            request = None
            if self.position == "buy":
                # 종가로 최대 매수
                request = self.__create_buy(self.data[-1]["closing_price"])
            elif self.position == "sell":
                # 종가로 전량 매도
                request = self.__create_sell(self.data[-1]["closing_price"], self.asset_amount)

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

    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트

        info:
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
        if self.is_intialized is not True or info is None:
            return
        self.data.append(copy.deepcopy(info))
        self._update_rsi(info["closing_price"])
        self._update_position()

    def _update_position(self):
        """매수, 매도 포지션을 결정해서 업데이트, 언제든 매매 요청 정보를 회신할 수 있도록 준비

        기본적으로 low보다 낮으면 최선을 다해 매수, high보다 높으면 최선을 다해 매도하도록 함
        """
        if self.rsi_info is None:
            self.position = None
        elif self.rsi[-1] < self.RSI_LOW:
            self.position = "buy"
            self.logger.debug(f"[RSI] Update position to BUY {self.rsi[-1]}")
        elif self.rsi[-1] > self.RSI_HIGH:
            self.position = "sell"
            self.logger.debug(f"[RSI] Update position to SELL {self.rsi[-1]}")

    def _update_rsi(self, price):
        """전달 받은 종가 정보로 rsi 정보를 업데이트"""

        # 필요 갯수만큼 데이터 채우기
        if len(self.rsi) < self.RSI_COUNT:
            self.logger.debug(f"[RSI] Fill to ready {price}")
            self.rsi.append(price)
            return

        # 초기값을 생성
        if len(self.rsi) == self.RSI_COUNT:
            self.logger.debug(f"[RSI] Make seed {price}")
            self.rsi.append(price)
            deltas = np.diff(self.rsi)
            up_avg = deltas[deltas >= 0].sum() / self.RSI_COUNT
            down_avg = -deltas[deltas < 0].sum() / self.RSI_COUNT
            r_strength = up_avg / down_avg
            self.rsi_info = (down_avg, up_avg, price)
            for i in range(len(self.rsi)):
                self.rsi[i] = 100.0 - 100.0 / (1.0 + r_strength)
            return

        # 최신 RSI 업데이트
        if self.rsi_info is not None:
            up_val = 0.0
            down_val = 0.0
            delta = price - self.rsi_info[2]

            if delta > 0:
                up_val = delta
            else:
                down_val = -delta

            down_avg = (self.rsi_info[0] * (self.RSI_COUNT - 1) + down_val) / self.RSI_COUNT
            up_avg = (self.rsi_info[1] * (self.RSI_COUNT - 1) + up_val) / self.RSI_COUNT

            r_strength = up_avg / down_avg
            self.rsi.append(100.0 - 100.0 / (1.0 + r_strength))
            self.rsi_info = (down_avg, up_avg, price)
            self.logger.debug(f"[RSI] Update RSI {self.rsi_info}, {self.rsi[-1]}")
            return

    def update_result(self, result):
        """요청한 거래의 결과를 업데이트

        request: 거래 요청 정보
        result:
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "state": 거래 상태 requested, done
            "msg": 거래 결과 메세지
            "date_time": 거래 체결 시간, 시뮬레이션 모드에서는 데이터 시간 +2초
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

    def __create_buy(self, price, amount=0):
        req_amount = amount
        req_price = float(price)
        req_value = req_price * req_amount
        total_req_value = req_value + (req_value * self.COMMISSION_RATIO)

        # 총액이 잔액보다 크거나 수량이 0인 매수 요청의 경우 가능한 최대치로 수량 조정
        if total_req_value > self.balance or amount == 0:
            req_amount = self.balance / (req_price * (1 + self.COMMISSION_RATIO))

        # 소숫점 4자리 아래 버림
        req_amount = math.floor(req_amount * 10000) / 10000
        final_value = req_amount * req_price

        if self.min_price > final_value:
            self.logger.info(f"target_value is too small {final_value}")
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
            "price": req_price,
            "amount": req_amount,
        }

    def __create_sell(self, price, amount):
        req_amount = amount

        # 요청 수량이 보유 수량보다 큰 경우 보유 수량으로 조정
        if req_amount > self.asset_amount:
            req_amount = self.asset_amount

        # 소숫점 4자리 아래 버림
        req_amount = math.floor(amount * 10000) / 10000

        req_price = float(price)
        total_value = req_price * req_amount

        if req_amount <= 0 or total_value < self.min_price:
            self.logger.info(f"asset is too small {req_amount}, {total_value}")
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
            "price": req_price,
            "amount": req_amount,
        }
