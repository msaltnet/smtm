"""빗썸 거래소를 통한 거래 처리"""

import os
import sys
import time
import math
import base64
import hmac, hashlib
import uuid
import hashlib
import requests
import threading
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv
import logging

load_dotenv()

from .log_manager import LogManager
from .trader import Trader
from .worker import Worker


class BithumbTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    """

    RESULT_CHECKING_INTERVAL = 5
    MARKET = "BTC"
    MARKET_KEY = "total_btc"
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.ACCESS_KEY = os.environ["BITHUMB_API_ACCESS_KEY"]
        self.SECRET_KEY = os.environ["BITHUMB_API_SECRET_KEY"]
        self.SERVER_URL = os.environ["BITHUMB_API_SERVER_URL"]
        self.worker = Worker("BithumbTrader-Worker")
        self.worker.start()
        self.timer = None
        self.request_map = {}

    def send_request(self, request, callback):
        """거래 요청을 처리한다
        request:
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간
        """
        self.worker.post_task(
            {"runnable": self._excute_order, "request": request, "callback": callback}
        )

    def send_account_info_request(self, callback):
        """계좌 요청 정보를 요청한다
        Returns:
            {
                balance: 계좌 현금 잔고
                asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
            }
        """
        self.worker.post_task({"runnable": self._excute_query, "callback": callback})

    def _excute_order(self, task):
        request = task["request"]
        is_buy = True if request["type"] == "buy" else False

        if request["price"] is None and is_buy is False:
            # 시장가 매도
            response = self._send_market_price_sell_order(self.MARKET, is_buy, request["amount"])
        elif request["amount"] is None and is_buy is True:
            # 시장가 매수
            snapshot = self.query_latest_trade(self.MARKET)
            if snapshot is not None:
                price = int(snapshot["data"][0]["price"])
                amount = request["price"] / price
                response = self._send_market_price_buy_order(self.MARKET, is_buy, amount)
            else:
                response = None
        elif request["price"] is not None and request["amount"] is not None:
            # 지정가 주문
            response = self._send_limit_order(
                self.MARKET, is_buy, request["price"], request["amount"]
            )
        else:
            # 잘못된 주문
            self.logger.error("Invalid order")

        if response["status"] != "0000":
            self.logger.error(f"Order error {response}")
            task["callback"]("error!")
            return

        print(response)
        result = self._create_success_result(request)
        self.request_map[request["id"]] = {
            "order_id": response["order_id"],
            "callback": task["callback"],
            "result": result,
        }
        self._start_timer()

    def _excute_query(self, task):
        response = self._query_balance()
        assets = response["data"]
        callback = task["callback"]
        result = {"asset": {}}
        for key, value in assets.items():
            if key == "total_krw":
                result["balance"] = value
            elif key == self.MARKET_KEY:
                snapshot = self.query_latest_trade(self.MARKET)
                if snapshot is not None:
                    price = snapshot["data"][0]["price"]
                name = self.MARKET
                amount = value
                result["asset"][name] = (price, amount)
        self.logger.info(f"account info {response}")
        callback(result)

    def _create_success_result(self, request):
        return {
            "request_id": request["id"],
            "type": request["type"],
            "price": request["price"],
            "amount": request["amount"],
            "msg": "success",
        }

    def _start_timer(self):
        if self.timer is not None:
            return

        def post_query_result_task():
            self.worker.post_task({"runnable": self._query_order_result})

        self.timer = threading.Timer(self.RESULT_CHECKING_INTERVAL, post_query_result_task)
        self.timer.start()

    def _stop_timer(self):
        if self.timer is None:
            return

        self.timer.cancel()
        self.timer = None

    def _convert_timestamp(self, timestamp):
        return datetime.fromtimestamp(int(int(timestamp) / 1000000)).strftime(self.ISO_DATEFORMAT)

    def _query_order_result(self, task):
        waiting_request = {}
        self.logger.info(f"waiting order count {len(self.request_map)}")
        for request_id, request_info in self.request_map.items():
            order = self._query_order(request_info["order_id"])
            if order["data"]["order_status"] == "Completed":
                result = request_info["result"]
                result["amount"] = float(order["data"]["order_qty"])
                result["date_time"] = self._convert_timestamp(int(order["data"]["order_date"]))
                if result["price"] is None:
                    result["price"] = self._get_total_trading_price(order["data"]["contract"])
                request_info["callback"](result)
            else:
                waiting_request[request_id] = request_info
        self.request_map = waiting_request
        self.logger.info(f"After update, waiting order count {len(self.request_map)}")
        self._stop_timer()
        if len(self.request_map) > 0:
            self._start_timer()

    def _get_total_trading_price(self, trading_list):
        total = 0
        for trading in trading_list:
            total = trading["total"]
        return total

    def _send_limit_order(self, market, is_buy, price=None, volume=None):
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
        print("ORDER #####")
        print(
            f"[LT] market: {market} is_buy: {is_buy}, price: {price}, volume: {volume} -> {final_volume}"
        )
        query = {
            "order_currency": market,
            "payment_currency": "KRW",
            "type": "bid" if is_buy is True else "ask",
            "units": str(final_volume),
            "price": str(price),
        }

        try:
            response = self.bithumbApiCall("/trade/place", query)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

    def _send_market_price_sell_order(self, market, is_buy, volume=None):
        """시작 가격 매도 주문 전송
        Params:
            order_currency: 주문 통화 (코인), String/필수
            payment_currency: 결제 통화 (마켓) KRW 혹은 BTC, String/필수
            units: 주문 수량 [최대 주문 금액]50억원, Float/필수
        Return:
            status, 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            order_id, 주문 번호, String
        """
        final_volume = "{0:.4f}".format(round(volume, 4))
        print("ORDER #####")
        print(f"[MP] market: {market} is_buy: {is_buy}, volume: {volume} -> {final_volume}")
        query = {
            "order_currency": market,
            "payment_currency": "KRW",
            "units": str(final_volume),
        }

        try:
            response = self.bithumbApiCall("/trade/market_sell", query)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

    def _send_market_price_buy_order(self, market, is_buy, volume=None):
        """시작 가격 매도 주문 전송
        Params:
            order_currency: 주문 통화 (코인), String/필수
            payment_currency: 결제 통화 (마켓) KRW 혹은 BTC, String/필수
            units: 주문 수량 [최대 주문 금액]50억원, Float/필수
        Return:
            status, 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            order_id, 주문 번호, String
        """
        final_volume = "{0:.4f}".format(round(volume, 4))
        print("ORDER #####")
        print(f"[MP] market: {market} is_buy: {is_buy}, volume: {volume} -> {final_volume}")
        query = {
            "order_currency": market,
            "payment_currency": "KRW",
            "units": str(final_volume),
        }

        try:
            response = self.bithumbApiCall("/trade/market_buy", query)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

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
        query = {"order_currency": "BTC", "payment_currency": "KRW"}
        if order_id is not None:
            query["order_id"] = order_id

        try:
            response = self.bithumbApiCall("/info/order_detail", query)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

    def _query_balance(self):
        """
        Returns:
            status: 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            total_{currency}: 전체 가상자산 수량, Number (String)
            total_krw: 전체 원화(KRW) 금액, Number (String)
            in_use_{currency}: 주문 중 묶여있는 가상자산 수량, Number (String)
            in_use_krw: 주문 중 묶여있는 원화(KRW) 금액, Number (String)
            available_{currency}: 주문 가능 가상자산 수량, Number (String)
            available_krw: 주문 가능 원화(KRW) 금액, Number (String)
            xcoin_last_{currency}: 마지막 체결된 거래 금액 ALL 호출 시 필드 명 – xcoin_last_{currency}, Number (String)
        """
        query = {"order_currency": "BTC", "payment_currency": "KRW"}

        try:
            response = self.bithumbApiCall("/info/balance", query)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

    def query_latest_trade(self, market):
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
            response = requests.request(
                "GET", self.SERVER_URL + f"/public/transaction_history/{market}", params=querystring
            )
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return

        return result

    def microtime(self, get_as_float=False):
        if get_as_float:
            return time.time()
        else:
            return "%f %d" % math.modf(time.time())

    def usecTime(self):
        mt = self.microtime(False)
        mt_array = mt.split(" ")[:2]
        return mt_array[1] + mt_array[0][2:5]

    def bithumbApiCall(self, endpoint, rgParams):
        """Api-Sign and Api-Nonce information generation.

        # - nonce: it is an arbitrary number that may only be used once.
        # - api_sign: API signature information created in various combinations values.
        """
        endpoint_item_array = {"endpoint": endpoint}

        uri_array = dict(endpoint_item_array, **rgParams)  # Concatenate the two arrays.
        print(f"uri_array {uri_array}")

        str_data = urlencode(uri_array)
        nonce = self.usecTime()

        data = endpoint + chr(0) + str_data + chr(0) + nonce
        utf8_data = data.encode("utf-8")

        key = self.SECRET_KEY
        utf8_key = key.encode("utf-8")

        h = hmac.new(bytes(utf8_key), utf8_data, hashlib.sha512)
        hex_output = h.hexdigest()
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

        res = requests.post(url, headers=headers, data=str_data)
        return res
