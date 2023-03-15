"""데모를 위해 계좌 정보가 없이 가상으로 거래 요청 및 계좌 조회 요청을 처리하는 클래스"""

from datetime import datetime
import requests
from .log_manager import LogManager
from .trader import Trader
from .worker import Worker


class DemoTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy, cancel
    price: 거래 가격
    amount: 거래 수량
    """

    RESULT_CHECKING_INTERVAL = 5
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    AVAILABLE_CURRENCY = {
        "BTC": ("KRW-BTC", "BTC"),
        "ETH": ("KRW-ETH", "ETH"),
        "DOGE": ("KRW-DOGE", "DOGE"),
        "XRP": ("KRW-XRP", "XRP"),
    }
    NAME = "DemoTrader"

    def __init__(self, budget=50000, currency="BTC", commission_ratio=0.0005, opt_mode=True):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        self.worker = Worker("DemoTrader-Worker")
        self.worker.start()
        self.SERVER_URL = "https://api.upbit.com"
        self.is_opt_mode = opt_mode
        self.asset = (0, 0)  # avr_price, amount
        self.balance = budget
        self.commission_ratio = commission_ratio
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    @staticmethod
    def _create_success_result(request):
        return {
            "state": "done",
            "request": request,
            "type": request["type"],
            "price": request["price"],
            "amount": request["amount"],
            "msg": "success",
            "date_time": request["date_time"],
        }

    def send_request(self, request_list, callback):
        """거래 요청을 처리한다

        request_list: 한 개 이상의 거래 요청 정보 리스트
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간
        }]
        callback(result):
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "state": 거래 상태 requested, done
            "msg": 거래 결과 메세지
            "date_time": 거래 체결 시간
        }
        """
        for request in request_list:
            self._execute_order({"request": request, "callback": callback})

    def get_account_info(self):
        """계좌 정보를 요청한다
        Returns:
            {
                balance: 계좌 현금 잔고
                asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
                quote: 종목별 현재 가격 딕셔너리
                date_time: 현재 시간
            }
        """
        trade_info = self.get_trade_tick()
        result = {
            "balance": self.balance,
            "asset": {self.market_currency: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        result["quote"][self.market_currency] = float(trade_info[0]["trade_price"])
        self.logger.debug(f"account info {result}")
        return result

    def cancel_request(self, request_id):
        """거래 요청을 취소한다, 모든 요청은 바로 처리되므로 사용되지 않는다
        request_id: 취소하고자 하는 request의 id
        """

    def cancel_all_requests(self):
        """모든 거래 요청을 취소한다, 모든 요청은 바로 처리되므로 사용되지 않는다
        체결되지 않고 대기중인 모든 거래 요청을 취소한다
        """

    def get_trade_tick(self):
        """최근 거래 정보 조회"""
        querystring = {"market": self.market, "count": "1"}
        return self._request_get(self.SERVER_URL + "/v1/trades/ticks", params=querystring)

    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        if request["price"] == 0:
            self.logger.warning("[REJECT] market price is not supported now")
            task["callback"]("error!")
            return

        is_buy = request["type"] == "buy"
        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            request_price = float(request["price"]) * float(request["amount"])
            self.logger.warning(f"[REJECT] balance is too small! {request_price} > {self.balance}")
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self._call_callback(task["callback"], result)
        self.logger.debug(f"request executed {request['id']}")

    def _call_callback(self, callback, result):
        result_value = float(result["price"]) * float(result["amount"])
        fee = result_value * self.commission_ratio

        if result["state"] == "done" and result["type"] == "buy":
            old_value = self.asset[0] * self.asset[1]
            new_value = old_value + result_value
            new_amount = self.asset[1] + float(result["amount"])
            new_amount = round(new_amount, 6)
            if new_amount == 0:
                avr_price = 0
            else:
                avr_price = round(new_value / new_amount, 6)
            self.asset = (avr_price, new_amount)
            self.balance -= round(result_value + fee)
        elif result["state"] == "done" and result["type"] == "sell":
            old_avr_price = self.asset[0]
            new_amount = self.asset[1] - float(result["amount"])
            new_amount = round(new_amount, 6)
            if new_amount == 0:
                old_avr_price = 0
            self.asset = (old_avr_price, new_amount)
            self.balance += round(result_value - fee)

        callback(result)

    def _request_get(self, url, headers=None, params=None):
        try:
            if params is not None:
                response = requests.get(url, params=params, headers=headers)
            else:
                response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
        except ValueError as err:
            self.logger.error(f"Invalid data from server: {err}")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result
