"""빗썸 거래소를 통한 거래 처리 및 계좌 정보 조회 할 수 있는 BithumbTrader 클래스"""

import os
import copy
import time
import math
import threading
from datetime import datetime
from urllib.parse import urlencode
import base64
import hmac
import hashlib
import requests
from dotenv import load_dotenv
from .log_manager import LogManager
from .trader import Trader
from .worker import Worker

load_dotenv()


class BithumbTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy, cancel
    price: 거래 가격
    amount: 거래 수량
    """

    RESULT_CHECKING_INTERVAL = 5
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    AVAILABLE_CURRENCY = {"BTC": ("BTC", "KRW"), "ETH": ("ETH", "KRW")}
    NAME = "Bithumb"

    def __init__(self, budget=50000, currency="BTC", commission_ratio=0.0005, opt_mode=True):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        self.worker = Worker("BTR-Worker")
        self.worker.start()
        self.timer = None
        self.order_map = {}
        self.ACCESS_KEY = os.environ.get("BITHUMB_API_ACCESS_KEY", "bithumb_access_key")
        self.SECRET_KEY = os.environ.get("BITHUMB_API_SECRET_KEY", "bithumb_secret_key")
        self.SERVER_URL = os.environ.get("BITHUMB_API_SERVER_URL", "bithumb_server_url")
        self.is_opt_mode = opt_mode
        self.asset = (0, 0)  # avr_price, amount
        self.balance = budget
        self.commission_ratio = commission_ratio
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    @staticmethod
    def _convert_timestamp(timestamp):
        return datetime.fromtimestamp(int(int(timestamp) / 1000000)).strftime(
            BithumbTrader.ISO_DATEFORMAT
        )

    @staticmethod
    def _create_success_result(request):
        return {
            "state": "requested",
            "request": request,
            "type": request["type"],
            "price": request["price"],
            "amount": request["amount"],
            "msg": "success",
        }

    @staticmethod
    def _timestamp_millisec():
        mt_string = "%f %d" % math.modf(time.time())
        mt_array = mt_string.split(" ")[:2]
        return mt_array[1] + mt_array[0][2:5]

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
        callback(result): 결과를 전달할 콜백함수
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
            self.worker.post_task(
                {"runnable": self._execute_order, "request": request, "callback": callback}
            )

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
            "asset": {self.market: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        if trade_info is not None and trade_info["status"] == "0000":
            result["quote"][self.market] = float(trade_info["data"][0]["price"])
        else:
            self.logger.error("fail query quote")
        self.logger.debug(f"account {result['balance']}, {result['asset']}, {result['quote']}")
        return result

    def cancel_request(self, request_id):
        """거래 요청을 취소한다
        request_id: 취소하고자 하는 request의 id
        """
        if request_id not in self.order_map:
            self.logger.debug(f"already canceled: {request_id}")
            return

        order = self.order_map[request_id]
        result = copy.deepcopy(order["result"])
        response = self._cancel_order(order["order_id"])

        result["state"] = "done"
        result["date_time"] = datetime.now().strftime(BithumbTrader.ISO_DATEFORMAT)
        result["amount"] = 0

        if response is None or response["status"] != "0000":
            # 이미 체결된 경우, 취소가 안되므로 주문 정보를 조회
            response = self._query_order(order["order_id"])
            self.logger.debug(f"cancel query: {response}")
            if response is None or response["data"]["order_status"] != "Completed":
                self.logger.warning(f"can't cancel and query {request_id}, {order['order_id']}")
                return

            result["amount"] = float(response["data"]["order_qty"])
            result["date_time"] = self._convert_timestamp(int(response["data"]["transaction_date"]))
            if "price" not in result or result["price"] is None:
                result["price"] = float(response["data"]["order_price"])

        del self.order_map[request_id]
        self.logger.debug(f"canceled: {request_id}")
        self._call_callback(order["callback"], result)

    def cancel_all_requests(self):
        """모든 거래 요청을 취소한다
        체결되지 않고 대기중인 모든 거래 요청을 취소한다
        """
        orders = copy.deepcopy(self.order_map)
        for request_id in orders.keys():
            self.cancel_request(request_id)

    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        is_buy = request["type"] == "buy"

        if request["price"] == 0:
            self.logger.warning("invalid price request.")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning("invalid price request. balance is too small!")
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning("invalid price request. rest asset amount is less than request!")
            task["callback"]("error!")
            return

        response = self._send_limit_order(is_buy, request["price"], request["amount"])

        if response is None or response["status"] != "0000":
            self.logger.error(f"Order error {response}")
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["order_id"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()

    def _cancel_order(self, order_id):
        """
        거래 요청 취소 api 호출
        Returns:
            status: 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            total_{currency}: 전체 가상자산 수량, Number (String)
            total_krw: 전체 원화(KRW) 금액, Number (String)
            in_use_{currency}: 주문 중 묶여있는 가상자산 수량, Number (String)
            in_use_krw: 주문 중 묶여있는 원화(KRW) 금액, Number (String)
            available_{currency}: 주문 가능 가상자산 수량, Number (String)
            available_krw: 주문 가능 원화(KRW) 금액, Number (String)
        """
        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "order_id": order_id,
        }
        return self.bithumb_api_call("/trade/cancel", query)

    def _start_timer(self):
        if self.timer is not None:
            return

        def post_query_result_task():
            self.worker.post_task({"runnable": self._update_order_result})

        self.timer = threading.Timer(self.RESULT_CHECKING_INTERVAL, post_query_result_task)
        self.timer.start()

    def _stop_timer(self):
        if self.timer is None:
            return

        self.timer.cancel()
        self.timer = None

    def _update_order_result(self, task):
        del task
        waiting_request = {}
        self.logger.debug(f"waiting order count {len(self.order_map)}")
        for request_id, order in self.order_map.items():
            try:
                response = self._query_order(order["order_id"])
                self.logger.debug(f"try to find order {order} : response {response}")
                if response["data"]["order_status"] == "Completed":
                    result = order["result"]
                    result["amount"] = float(response["data"]["order_qty"])
                    result["date_time"] = self._convert_timestamp(
                        int(response["data"]["contract"][0]["transaction_date"])
                    )
                    if "price" not in result or result["price"] is None:
                        result["price"] = float(response["data"]["order_price"])
                    result["state"] = "done"
                    self._call_callback(order["callback"], result)
                else:
                    waiting_request[request_id] = order
            except KeyError as err:
                self.logger.error(f"query_order fail! request_id {request_id}: {err}")

        self.order_map = waiting_request
        self.logger.debug(f"After update, waiting order count {len(self.order_map)}")
        self._stop_timer()
        if len(self.order_map) > 0:
            self._start_timer()

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
                avr_price = new_value / new_amount
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

    def _send_limit_order(self, is_buy, price=None, volume=0.0001):
        """지정 가격 주문 전송

        Params:
            order_currency: 주문 통화 (코인), String/필수
            payment_currency: 결제 통화 (마켓) 입력값: : KRW 혹은 BTC, String/필수
            units: 주문 수량 [최대 주문 금액]50억원, Float/필수
            price: Currency 거래가, Integer/필수
            type: 거래유형 (bid : 매수 ask : 매도), String/필수
        Return:
            status, 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            order_id, 주문 번호, String
        """
        final_volume = "{0:.4f}".format(round(volume, 4))
        final_price = price
        if self.is_opt_mode:
            final_price = self._optimize_price(price, is_buy)

        final_price = math.floor(final_price)
        self.logger.info(f"ORDER ##### {'BUY' if is_buy else 'SELL'}")
        self.logger.info(f"{self.market},price: {price}, volume: {final_volume}")

        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "type": "bid" if is_buy is True else "ask",
            "units": str(final_volume),
            "price": str(final_price),
        }

        self.logger.debug(f"query :{query}")
        return self.bithumb_api_call("/trade/place", query)

    def _optimize_price(self, price, is_buy):
        latest = self.get_trade_tick()
        if latest is None or latest["status"] != "0000":
            return price

        latest_price = float(latest["data"][0]["price"])

        if (is_buy is True and latest_price < price) or (is_buy is False and latest_price > price):
            self.logger.info(f"price optimized! ##### {price} -> {latest_price}")
            return latest_price

        return price

    def _query_order(self, order_id=None):
        """주문 조회

        request:
            order_id: 매수/매도 주문 등록된 주문번호(입력 시 해당 데이터만 추출), String
            type: 거래유형 (bid : 매수 ask : 매도), String
            count: 1~1000 (기본값 : 100), Integer
            after: 입력한 시간보다 나중의 데이터 추출 YYYY-MM-DD hh:mm:ss 의 UNIX Timestamp, Integer
            order_currency: 주문 통화 (코인), String/필수
            payment_currency: 결제 통화 (마켓)
            입력값 : KRW 혹은 BTC, String
        response:
            status: 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            order_currency: 주문 통화 (코인), String
            payment_currency: 결제 통화 (마켓), String
            order_id: 매수/매도 주문 등록된 주문번호, String
            order_date: 주문일시 타임 스탬프, Integer
            type: 주문 요청 구분 (bid : 매수 ask : 매도), String
            watch_price: 주문 접수가 진행되는 가격 (자동주문시), String
            units: 거래요청 Currency, String
            units_remaining: 주문 체결 잔액, Number (String)
            price: 1Currency당 주문 가격, Number (String)
        """
        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "order_id": order_id,
        }
        if order_id is None:
            return None

        return self.bithumb_api_call("/info/order_detail", query)

    def _query_balance(self, market):
        """
        잔고 조회 api 호출
        Returns:
            status: 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            total_{currency}: 전체 가상자산 수량, Number (String)
            total_krw: 전체 원화(KRW) 금액, Number (String)
            in_use_{currency}: 주문 중 묶여있는 가상자산 수량, Number (String)
            in_use_krw: 주문 중 묶여있는 원화(KRW) 금액, Number (String)
            available_{currency}: 주문 가능 가상자산 수량, Number (String)
            available_krw: 주문 가능 원화(KRW) 금액, Number (String)
        """
        query = {"order_currency": market, "payment_currency": self.market_currency}
        return self.bithumb_api_call("/info/balance", query)

    def get_trade_tick(self):
        """최근 거래 내역 조회
        response:
            status: 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            transaction_date: 거래 체결 시간 타임 스탬프(YYYY-MM-DD HH:MM:SS), Integer (String)
            type: 거래 유형 bid : 매수 ask : 매도, String
            units_traded: Currency 거래량, Number (String)
            price: Currency 거래가, Number (String)
            total: 총 거래 금액, Number (String)
        """
        querystring = {"count": "1"}

        try:
            response = requests.get(
                f"{self.SERVER_URL}/public/transaction_history/{self.market}_{self.market_currency}",
                params=querystring,
            )
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

    def bithumb_api_call(self, endpoint, params):
        """빗썸 api wrapper
        nonce: it is an arbitrary number that may only be used once.
        api_sign: API signature information created in various combinations values.
        """
        uri_array = dict({"endpoint": endpoint}, **params)  # Concatenate the two arrays.

        str_data = urlencode(uri_array)
        nonce = self._timestamp_millisec()

        data = endpoint + chr(0) + str_data + chr(0) + nonce
        utf8_data = data.encode("utf-8")

        key = self.SECRET_KEY
        utf8_key = key.encode("utf-8")

        hmac_output = hmac.new(bytes(utf8_key), utf8_data, hashlib.sha512)
        hex_output = hmac_output.hexdigest()
        utf8_hex_output = hex_output.encode("utf-8")
        api_sign = base64.b64encode(utf8_hex_output)
        utf8_api_sign = api_sign.decode("utf-8")

        url = self.SERVER_URL + endpoint
        headers = {
            "Api-Key": self.ACCESS_KEY,
            "Api-Sign": utf8_api_sign,
            "Api-Nonce": nonce,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = requests.post(url, headers=headers, data=str_data)
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
