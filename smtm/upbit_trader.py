"""업비트 거래소를 통한 거래 처리"""

import os
import jwt  # PyJWT
import uuid
import hashlib
from urllib.parse import urlencode
import requests
import threading
from dotenv import load_dotenv

load_dotenv()

from .log_manager import LogManager
from .trader import Trader
from .worker import Worker


class UpbitTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    """

    RESULT_CHECKING_INTERVAL = 5
    MARKET = "KRW-BTC"

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.ACCESS_KEY = os.environ["UPBIT_OPEN_API_ACCESS_KEY"]
        self.SECRET_KEY = os.environ["UPBIT_OPEN_API_SECRET_KEY"]
        self.SERVER_URL = os.environ["UPBIT_OPEN_API_SERVER_URL"]
        self.worker = Worker("UpbitTrader-Worker")
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
            "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
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
        response = self._send_order(self.MARKET, is_buy, request["price"], request["amount"])
        if response is None:
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.request_map[request["id"]] = {
            "uuid": response["uuid"],
            "callback": task["callback"],
            "result": result,
        }
        self._start_timer()

    def _excute_query(self, task):
        response = self._query_account()
        callback = task["callback"]
        result = {"asset": {}}
        for item in response:
            if item["currency"] == "KRW":
                result["balance"] = item["balance"]
            else:
                name = item["currency"]
                price = item["avg_buy_price"]
                amount = item["balance"]
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

    def _query_order_result(self, task):
        results = self._query_order_list()
        waiting_request = {}
        self.logger.info(f"waiting order count {len(self.request_map)}")
        for request_id, request_info in self.request_map.items():
            for order in results:
                if order["uuid"] == request_info["uuid"]:
                    self.logger.info(f"find order! {request_info} {order}")
                    if order["state"] == "done":
                        result = request_info["result"]
                        result["date_time"] = order["created_at"]
                        request_info["callback"](result)
                    elif order["state"] == "wait":
                        waiting_request[request_id] = request_info
                    elif order["state"] == "cancel":
                        # 시장가 매수시 cancel로 처리됨 - 가격은 변동 폭이 있으므로 확인 필요
                        result = request_info["result"]
                        result["date_time"] = order["created_at"]
                        request_info["callback"](result)
        self.request_map = waiting_request
        self.logger.info(f"After update, waiting order count {len(self.request_map)}")
        self._stop_timer()
        if len(self.request_map) > 0:
            self._start_timer()

    def _send_order(self, market, is_buy, price=None, volume=None):
        """
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
        self.logger.info("ORDER #####")
        self.logger.info(f"market: {market} is_buy: {is_buy}, price: {price}, volume: {volume} ")
        if price is None and is_buy is False:
            # 시장가 매도
            query_string = self._create_market_price_order_query(market, volume=volume)
        elif volume is None and is_buy is True:
            # 시장가 매수
            query_string = self._create_market_price_order_query(market, price=price)
        elif price is not None and volume is not None:
            # 지정가 주문
            query_string = self._create_limit_order_query(market, is_buy, price, volume)
        else:
            # 잘못된 주문
            self.logger.error("Invalid order")

        self.logger.info(f"query_string {query_string}")
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

        try:
            response = requests.post(
                self.SERVER_URL + "/v1/orders", params=query_string, headers=headers
            )
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result

    def _create_limit_order_query(self, market, is_buy, price, volume):
        query = {
            "market": market,
            "side": "bid" if is_buy is True else "ask",
            "volume": str(volume),
            "price": str(price),
            "ord_type": "limit",
        }
        query_string = urlencode(query).encode()
        return query_string

    def _create_market_price_order_query(self, market, price=None, volume=None):
        query = {
            "market": market,
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

    def _query_order_list(self, states=None):
        """
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
        query_states = ["done", "wait", "cancel"]

        states_query_string = "&".join(["states[]={}".format(state) for state in query_states])
        query_string = states_query_string.encode()

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

        try:
            response = requests.get(
                self.SERVER_URL + "/v1/orders", params=query_string, headers=headers
            )
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result

    def _query_account(self):
        """
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

        try:
            response = requests.get(self.SERVER_URL + "/v1/accounts", headers=headers)
            response.raise_for_status()
            result = response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result
