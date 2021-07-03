"""bithumb api 테스트 해보기 위한 모듈"""

import os
import sys
import time
import math
import base64
import hmac, hashlib
import uuid
import hashlib
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
import logging

load_dotenv()


class BithumbApi:
    def __init__(self):
        self.ACCESS_KEY = os.environ["BITHUMB_API_ACCESS_KEY"]
        self.SECRET_KEY = os.environ["BITHUMB_API_SECRET_KEY"]
        self.SERVER_URL = os.environ["BITHUMB_API_SERVER_URL"]

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

        response = requests.request(
            "GET", self.SERVER_URL + f"/public/transaction_history/{market}", params=querystring
        )

        print(self.SERVER_URL + f"/public/transaction_history/{market}")
        return response.json()

    # def send_lower_order_10000(self):
    #     market = "BTC"
    #     tick = self.query_latest_trade(market)
    #     target_price = round(float(tick[0]["price"] * 0.95), -3)
    #     target_volume = "{0:.8f}".format(round(10000 / target_price, 8))
    #     return self.send_order(market, True, str(target_price), str(target_volume))

    def query_account(self):
        query = {"order_currency": "BTC", "payment_currency": "KRW"}
        res = self.bithumbApiCall("/info/account", query)
        print(res.json())

    def query_balance(self):
        query = {"order_currency": "BTC", "payment_currency": "KRW"}
        res = self.bithumbApiCall("/info/balance", query)
        print(res.json())

    def query_order(self, order_id=None):
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
        query = {}
        if order_id is not None:
            query["order_id"] = order_id

        query = {"order_currency": "BTC", "payment_currency": "KRW"}
        res = self.bithumbApiCall("/info/orders", query)

        print(res.json())
        return res.json()

    def send_order(self, market, is_buy, price=None, volume=None):
        """지정 가격 주문 전송
        Params:
            apiKey: 사용자 API Key, String/필수
            secretKey: 사용자 Secret Key, String/필수
            order_currency: 주문 통화 (코인), String/필수
            payment_currency: 결제 통화 (마켓)
            입력값: : KRW 혹은 BTC, String/필수
            units: 주문 수량 [최대 주문 금액]50억원, Float/필수
            price: Currency 거래가, Integer/필수
            type: 거래유형 (bid : 매수 ask : 매도), String/필수
        Return:
            status, 결과 상태 코드 (정상: 0000, 그 외 에러 코드 참조), String
            order_id, 주문 번호, String
        """
        print("ORDER #####")
        print(f"market: {market} is_buy: {is_buy}, price: {price}, volume: {volume} ")
        query = {
            "order_currency": market,
            "payment_currency": "KRW",
            "type": "bid" if is_buy is True else "ask",
            "units": str(volume),
            "price": str(price),
        }
        res = self.bithumbApiCall("/trade/place", query)

        print(res.json())
        return res.json()

    def cancel_order(self, market=None, order_id=None):
        """주문 취소
        Params:
            type, 거래유형 (bid : 매수 ask : 매도), String/필수
            order_id, 매수/매도 주문 등록된 주문번호, String/필수
        """
        if order_id is None or market is None:
            return

        query = {
            "order_currency": market,
            "payment_currency": "KRW",
            "order_id": order_id,
        }
        res = self.bithumbApiCall("/trade/cancel", query)

        print(res.json())
        return res.json()

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

    def send_lower_order_10000(self):
        market = "BTC"
        tick = self.query_latest_trade(market)
        target_price = round(round(int(tick["data"][0]["price"]) * 0.95), -3)
        target_volume = "{0:.4f}".format(round(10000 / target_price, 4))
        return self.send_order(market, True, str(target_price), str(target_volume))

    def send_order_buy_10000(self):
        market = "BTC"
        tick = self.query_latest_trade(market)
        target_price = int(tick["data"][0]["price"])
        target_volume = "{0:.4f}".format(round(10000 / target_price, 4))
        return self.send_order(market, True, str(target_price), str(target_volume))

    def send_order_sell_10000(self):
        market = "BTC"
        tick = self.query_latest_trade(market)
        target_price = int(tick["data"][0]["price"])
        target_volume = "{0:.4f}".format(round(10000 / target_price, 4))
        return self.send_order(market, False, str(target_price), str(target_volume))


if __name__ == "__main__":
    api = BithumbApi()
    # print("")
    # #최근 거래 내역 조회
    # print("query_latest_trade ======================================")
    # lower_response = api.query_latest_trade("BTC")
    # print("")
    # #계좌 조회
    # print("query_latest_trade ======================================")
    # query_response = api.query_account()
    # print("")
    # #계좌 잔액 조회
    # print("query_balance ======================================")
    # query_response = api.query_balance()
    # print("")
    # #주문 조회
    print("query_latest_trade ======================================")
    query_response = api.query_order()
    # print("")
    # #시세 - 10% 10000원 매수 주문 넣기 - a
    # print("send_lower_order_10000 ======================================")
    # lower_response = api.send_lower_order_10000()
    # print("")
    # #주문 취소
    # print("cancel_order ======================================")
    # one = api.cancel_order("BTC", order_id=query_response["data"][0]["order_id"])
    print("")
    # #주문 조회
    print("query_latest_trade ======================================")
    query_response = api.query_order()
    print("")
    # #시세 - 100% 10000원 매수 주문 넣기 - a
    print("send_lower_order_10000 ======================================")
    lower_response = api.send_order_buy_10000()
    print("")
    # #주문 조회
    print("query_latest_trade ======================================")
    query_response = api.query_order()
    print("")
    # #시세 - 100% 10000원 매도 주문 넣기 - a
    print("send_lower_order_10000 ======================================")
    lower_response = api.send_order_sell_10000()
    print("")
    # #계좌 잔액 조회
    print("query_balance ======================================")
    query_response = api.query_balance()
