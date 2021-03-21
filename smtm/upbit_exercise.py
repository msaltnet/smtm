"""upbit api 테스트 해보기 위한 모듈"""

import os
import jwt  # PyJWT
import uuid
import hashlib
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv

load_dotenv()


class UpbitApi:
    def __init__(self):
        self.ACCESS_KEY = os.environ["UPBIT_OPEN_API_ACCESS_KEY"]
        self.SECRET_KEY = os.environ["UPBIT_OPEN_API_SECRET_KEY"]
        self.SERVER_URL = os.environ["UPBIT_OPEN_API_SERVER_URL"]

    def query_latest_trade(self, market):
        """최근 거래 내역 조회
        response:
            trade_date_utc: 체결 일자(UTC 기준), String
            trade_time_utc: 체결 시각(UTC 기준), String
            timestamp: 체결 타임스탬프, Long
            trade_price: 체결 가격, Double
            trade_volume: 체결량, Double
            prev_closing_price: 전일 종가, Double
            change_price: 변화량, Double
            ask_bid: 매도/매수, String
            sequential_id: 체결 번호(Unique), Long
        """
        querystring = {
            "market": market,
            "count":"1"
        }

        response = requests.request("GET", self.SERVER_URL + "/v1/trades/ticks", params=querystring)

        print(response.json())
        return response.json()

    def create_token(self, query=None):
        """API에 사용될 토큰을 생성"""
        if query is None:
            print("Start create token without query")
            payload = {
                "access_key": self.ACCESS_KEY,
                "nonce": str(uuid.uuid4()),
            }

            jwt_token = jwt.encode(payload, self.SECRET_KEY)
            authorization_token = "Bearer {}".format(jwt_token)
            return authorization_token

        # query는 dict 타입입니다.
        print("Start create token without query")
        print(query)
        m = hashlib.sha512()
        m.update(urlencode(query).encode())
        print("url encoded_query")
        print(urlencode(query).encode())
        query_hash = m.hexdigest()

        print("hash of encoded_query")
        print(query_hash)

        payload = {
            "access_key": self.ACCESS_KEY,
            "nonce": str(uuid.uuid4()),
            "query_hash": query_hash,
            "query_hash_alg": "SHA512",
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorization_token = "Bearer {}".format(jwt_token)
        return authorization_token

    def query_account(self):
        """계좌 정보 조회
        response:
            currency: 화폐를 의미하는 영문 대문자 코드, String
            balance: 주문가능 금액/수량, NumberString
            locked: 주문 중 묶여있는 금액/수량, NumberString
            avg_buy_price: 매수평균가, NumberString
            avg_buy_price_modified: 매수평균가 수정 여부, Boolean
            unit_currency: 평단가 기준 화폐, String
        """
        payload = {
            "access_key": self.ACCESS_KEY,
            "nonce": str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorize_token = "Bearer {}".format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = requests.get(self.SERVER_URL + "/v1/accounts", headers=headers)
        print(res.json())
        return res.json()

    def query_order(self, order_uuid=None, order_identifier=None):
        """주문 조회
        response:
            uuid:, 주문의 고유 아이디, String
            side:, 주문 종류, String
            ord_type:, 주문 방식, String
            price:, 주문 당시 화폐 가격, NumberString
            state:, 주문 상태, String
            market:, 마켓의 유일키, String
            created_at:, 주문 생성 시간, DateString
            volume:, 사용자가 입력한 주문 양, NumberString
            remaining_volume:, 체결 후 남은 주문 양, NumberString
            reserved_fee:, 수수료로 예약된 비용, NumberString
            remaining_fee:, 남은 수수료, NumberString
            paid_fee:, 사용된 수수료, NumberString
            locked:, 거래에 사용중인 비용, NumberString
            executed_volume:, 체결된 양, NumberString
            trade_count:, 해당 주문에 걸린 체결 수, Integer
            trades:, 체결	, Array[Object]
                trades.market: 마켓의 유일 키, String
                trades.uuid: 체결의 고유 아이디, String
                trades.price: 체결 가격, NumberString
                trades.volume: 체결 양, NumberString
                trades.funds: 체결된 총 가격, NumberString
                trades.side: 체결 종류, String
                trades.created_at: 체결 시각, DateString
        """
        query = {}
        if order_uuid is not None:
            query["uuid"] = order_uuid
        elif order_identifier is not None:
            query["identifier"] = order_identifier
        else:
            return

        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            "access_key": self.ACCESS_KEY,
            "nonce": str(uuid.uuid4()),
            "query_hash": query_hash,
            "query_hash_alg": "SHA512",
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorize_token = "Bearer {}".format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = requests.get(self.SERVER_URL + "/v1/order", params=query, headers=headers)

        print(res.json())
        return res.json()

    def query_order_list(self, states=None):
        """ 주문 목록 조회
        response:
            uuid: 주문의 고유 아이디, String
            side: 주문 종류, String
            ord_type: 주문 방식, String
            price: 주문 당시 화폐 가격, NumberString
            state: 주문 상태, String
            market: 마켓의 유일키, String
            created_at: 주문 생성 시간, DateString
            volume: 사용자가 입력한 주문 양, NumberString
            remaining_volume: 체결 후 남은 주문 양, NumberString
            reserved_fee: 수수료로 예약된 비용, NumberString
            remaining_fee: 남은 수수료, NumberString
            paid_fee: 사용된 수수료, NumberString
            locked: 거래에 사용중인 비용, NumberString
            executed_volume: 체결된 양, NumberString
            trade_count: 해당 주문에 걸린 체결 수, Integer
        """
        query_states = [
            "done",
            "wait",
            "cancel"
        ]
        if states is not None:
            query_states = states

        states_query_string = '&'.join(["states[]={}".format(state) for state in query_states])
        query_string = states_query_string.encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': self.ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = requests.get(self.SERVER_URL + "/v1/orders", params=query_string, headers=headers)

        # print(res.json())
        return res.json()

    def cancel_order(self, order_uuid=None):
        """주문 취소
        response:
            uuid: 주문의 고유 아이디, String
            side: 주문 종류, String
            ord_type: 주문 방식, String
            price: 주문 당시 화폐 가격, NumberString
            state: 주문 상태, String
            market: 마켓의 유일키, String
            created_at: 주문 생성 시간, String
            volume: 사용자가 입력한 주문 양, NumberString
            remaining_volume: 체결 후 남은 주문 양, NumberString
            reserved_fee: 수수료로 예약된 비용, NumberString
            remaing_fee: 남은 수수료, NumberString
            paid_fee: 사용된 수수료, NumberString
            locked: 거래에 사용중인 비용, NumberString
            executed_volume: 체결된 양, NumberString
            trade_count: 해당 주문에 걸린 체결 수, Integer
        """
        if order_uuid is None:
            return

        query = {
            'uuid': order_uuid,
        }
        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': self.ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = requests.delete(self.SERVER_URL + "/v1/order", params=query, headers=headers)

        # print(res.json())
        return res.json()

    def send_order(self, market, is_buy, price=None, volume=None):
        """주문 전송
        request:
            market *: 마켓 ID (필수)
            side *: 주문 종류 (필수)
            - bid : 매수
            - ask : 매도
            volume *: 주문량 (지정가, 시장가 매도 시 필수)
            price *: 주문 가격. (지정가, 시장가 매수 시 필수)
            ex) KRW-BTC 마켓에서 1BTC당 1,000 KRW로 거래할 경우, 값은 1000 이 된다.
            ex) KRW-BTC 마켓에서 1BTC당 매도 1호가가 500 KRW 인 경우, 시장가 매수 시 값을 1000으로 세팅하면 2BTC가 매수된다.
            (수수료가 존재하거나 매도 1호가의 수량에 따라 상이할 수 있음)
            ord_type *: 주문 타입 (필수)
            - limit : 지정가 주문
            - price : 시장가 주문(매수)
            - market : 시장가 주문(매도)
            identifier: 조회용 사용자 지정값 (선택)

        response:
            uuid: 주문의 고유 아이디, String
            side: 주문 종류, String
            ord_type: 주문 방식, String
            price: 주문 당시 화폐 가격, NumberString
            avg_price: 체결 가격의 평균가, NumberString
            state: 주문 상태, String
            market: 마켓의 유일키, String
            created_at: 주문 생성 시간, String
            volume: 사용자가 입력한 주문 양, NumberString
            remaining_volume: 체결 후 남은 주문 양, NumberString
            reserved_fee: 수수료로 예약된 비용, NumberString
            remaining_fee: 남은 수수료, NumberString
            paid_fee: 사용된 수수료, NumberString
            locked: 거래에 사용중인 비용, NumberString
            executed_volume: 체결된 양, NumberString
            trade_count: 해당 주문에 걸린 체결 수, Integer
        """
        print("ORDER #####")
        print(f"market: {market} is_buy: {is_buy}, price: {price}, volume: {volume} ")
        if price is None and is_buy is False:
            # 시장가 매도
            query_string = self.create_market_price_order_query(market, volume=volume)
        elif volume is None and is_buy is True:
            # 시장가 매수
            query_string = self.create_market_price_order_query(market, price=price)
        elif price is not None and volume is not None:
            # 지정가 주문
            query_string = self.create_limit_order_query(market, is_buy, price, volume)
        else:
            # 잘못된 주문
            print("Invalid order")

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': self.ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, self.SECRET_KEY)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
        print(query_string)
        res = requests.post(self.SERVER_URL + "/v1/orders", params=query_string, headers=headers)
        # print(res.json())
        return res.json()

    def create_limit_order_query(self, market, is_buy, price, volume):
        query = {
            'market': market,
            'side': 'bid' if is_buy is True else 'ask',
            'volume': str(volume),
            'price': str(price),
            'ord_type': 'limit',
        }
        query_string = urlencode(query).encode()
        return query_string

    def create_market_price_order_query(self, market, price=None, volume=None):
        query = {
            'market': market,
        }

        if price is None and volume is not None:
            query["side"] = "ask"
            query["volume"] = str(volume)
            query["ord_type"] = "market"
        elif price is not None and volume is None:
            query["side"] = "bid"
            query["price"] = str(price)
            query["ord_type"] = "price"
        else:
            return

        query_string = urlencode(query).encode()
        return query_string

    def send_lower_order_10000(self):
        market = "KRW-BTC"
        tick = self.query_latest_trade(market)
        target_price = round(float(tick[0]["trade_price"] * 0.95), -3)
        target_volume = "{0:.8f}".format(round(10000 / target_price, 8))
        return self.send_order(market, True, str(target_price), str(target_volume))

    def send_market_price_order_10000(self):
        market = "KRW-BTC"
        return self.send_order(market, True, price=10000)

    def send_sell_with_tick_10000(self):
        market = "KRW-BTC"
        tick = self.query_latest_trade(market)
        target_price = tick[0]["trade_price"]
        target_volume = "{0:.8f}".format(round(10000 / target_price, 8))
        return self.send_order(market, False, str(target_price), str(target_volume))

if __name__ == "__main__":
    api = UpbitApi()
    # print("")
    # print("send_lower_order_10000 ======================================")
    #lower_response = api.send_lower_order_10000()
    # print("")
    # print("query_order ======================================")
    # one = api.query_order(order_uuid="b290b6ca-faed-4e0b-853d-24065d3cad2e")
    # print("")
    # print("query_order_list all ======================================")
    # order_list = api.query_order_list()
    # print(order_list[:3])
    # print("")
    # print("query_order_list wait ======================================")
    # order_list = api.query_order_list(["wait"])
    # print(order_list[:3])
    # print("")
    # print("query_order_list wait cancel ======================================")
    # order_list = api.query_order_list(["wait", "cancel"])
    # print(order_list[:3])
    # print("")
    # print("cancel_order ======================================")
    # cancel = api.cancel_order("b290b6ca-faed-4e0b-853d-24065d3cad2e")
    # print(cancel)
    # print("")
    # print("query_order_list wait ======================================")
    # order_list = api.query_order_list(["wait"])
    # print(order_list[:3])
    # print("")
    # print("query_order_list wait cancel ======================================")
    # order_list = api.query_order_list(["wait", "cancel"])
    # print(order_list[:3])
    # print("")
    # print("send_market_price_order_10000 ======================================")
    # market_order = api.send_market_price_order_10000()
    # print(market_order)
    # print("")
    # market_order_query = api.query_order(order_uuid=market_order["uuid"])
    # print(market_order_query)
    # print("")
    # print("query_order_list done ======================================")
    # order_list = api.query_order_list(["done"])
    # print(order_list[:3])
    # print("")
    # print("send_sell_with_tick done ======================================")
    # sell_order = api.send_sell_with_tick_10000()
    # print(sell_order)
    # print("")
    # sell_order_query = api.query_order(order_uuid=sell_order["uuid"])
    # print(sell_order_query)
    # print("")
    
    # print(api.create_token())
    # print("======================================")
    # print(api.create_token({"test": "test_query"}))
    # print("======================================")
    # print("query_account ======================================")
    # api.query_account()

# 1. 시세 - 10% 10000원 매수 주문 넣기 - a
# 2. 주문 내역 조회 - uuid
# 3. 주문 내역 상태로 조회 - wait
# 4. a 주문 취소하기
# 5. 주문 내역 상태로 조회 - cancel
# 6. 시장 가격 5000원 거래 주문 넣기
# 7. 주문 내역 상태로 조회 - wait, done, cancel
# 8. 시세로 팔기
# 9. 주문 내역 조회 - uuid
