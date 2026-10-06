import time
import math
import threading
from decimal import Decimal, DecimalException, Inexact, Rounded, localcontext
from datetime import datetime
from urllib.parse import urlencode
import base64
import hmac
import hashlib
import requests
from .base_exchange_trader import BaseExchangeTrader
from . import order_spec


class BithumbTrader(BaseExchangeTrader):
    """
    빗썸 거래소를 통한 거래 처리 및 계좌 정보 조회 할 수 있는 BithumbTrader 클래스

    BithumbTrader class that can process transactions and check account information through Bithumb exchange

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy, cancel
    price: 거래 가격
    amount: 거래 수량
    """

    AVAILABLE_CURRENCY = {"BTC": ("BTC", "KRW"), "ETH": ("ETH", "KRW")}
    NAME = "Bithumb"
    CODE = "BTH"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})

    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.0005, opt_mode=True,
        access_key_env=None, secret_key_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="BithumbTrader",
            worker_name="BTR-Worker",
            env_key_names=(
                access_key_env or "BITHUMB_API_ACCESS_KEY",
                secret_key_env or "BITHUMB_API_SECRET_KEY",
                "BITHUMB_API_SERVER_URL",
            ),
        )
        self._order_lock = threading.Lock()
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    @staticmethod
    def _convert_timestamp(timestamp):
        return datetime.fromtimestamp(int(int(timestamp) / 1000000)).strftime(
            BithumbTrader.ISO_DATEFORMAT
        )

    @staticmethod
    def _timestamp_millisec():
        mt_string = "%f %d" % math.modf(time.time())
        mt_array = mt_string.split(" ")[:2]
        return mt_array[1] + mt_array[0][2:5]

    def get_account_info(self):
        """
        계좌 정보를 요청한다

        Request account information
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
        self.logger.debug(
            f"account {result['balance']}, {result['asset']}, {result['quote']}"
        )
        return result

    def cancel_all_requests(self):
        # Snapshot IDs without copying callback owners or a changing dictionary.
        with self._order_lock:
            request_ids = list(self.order_map)
        for request_id in request_ids:
            self.cancel_request(request_id)

    def cancel_request(self, request_id):
        """A cancellation ACK has no fill totals; always query terminal detail."""
        with self._order_lock:
            order = self.order_map.get(request_id)
        if order is None:
            return
        try:
            self._cancel_order(order["order_id"])
            with self._order_lock:
                if self.order_map.get(request_id) is not order:
                    return
            response = self._query_order(order["order_id"])
            self._complete_order(request_id, order, response)
        finally:
            with self._order_lock:
                if self.order_map:
                    self._start_timer()

    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        ord_type = order_spec.get_ord_type(request)
        if ord_type not in self.SUPPORTED_ORD_TYPES:
            task["callback"](order_spec.make_rejected_result(
                request, f"unsupported ord_type: {ord_type}"))
            return

        is_buy = request["type"] == "buy"
        is_market = ord_type == order_spec.MARKET

        if not is_market and request["price"] == 0:
            self.logger.warning("invalid price request.")
            return

        # NOTE: 시장가 매수는 요청에 단가가 없고(units 기준) 캐시된 시세도 없어
        # 클라이언트단 예산 가드를 적용할 수 없다. 예산 초과 주문은 거래소가
        # 거부하며, 그 응답은 아래 status != "0000" 경로에서 "error!"로 처리된다.
        if is_buy and not is_market and \
                float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning("invalid price request. balance is too small!")
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                "invalid price request. rest asset amount is less than request!"
            )
            task["callback"]("error!")
            return

        if is_market:
            response = self._send_market_order(is_buy, request["amount"])
        else:
            response = self._send_limit_order(
                is_buy, request["price"], request["amount"])

        if response is None or response["status"] != "0000":
            self.logger.error(f"Order error {response}")
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        with self._order_lock:
            self.order_map[request["id"]] = {
                "order_id": response["order_id"],
                "callback": task["callback"],
                "result": result,
            }
        task["callback"](result)
        with self._order_lock:
            self._start_timer()

    def _cancel_order(self, order_id):
        """Cancel a known order; status-only ACK does not describe execution.

        Confirm the canceled remainder and cumulative fills via /info/order_detail.
        """
        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "order_id": order_id,
        }
        return self.bithumb_api_call("/trade/cancel", query)

    def _update_order_result(self, task):
        del task
        with self._order_lock:
            orders = list(self.order_map.items())
        try:
            for request_id, order in orders:
                response = self._query_order(order["order_id"])
                self._complete_order(request_id, order, response)
        finally:
            with self._order_lock:
                self._stop_timer()
                if self.order_map:
                    self._start_timer()

    @staticmethod
    def _settlement_number(value):
        """Reject unusable numbers, including nonzero decimals lost as float zero."""
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("invalid settlement number")
        number = Decimal(str(value))
        converted = float(number)
        if (not number.is_finite() or number < 0 or not math.isfinite(converted)
                or (number != 0 and converted == 0)):
            raise ValueError("unusable settlement number")
        return number

    def _settlement_time(self, value):
        timestamp = self._settlement_number(value)
        if timestamp <= 0 or timestamp != timestamp.to_integral_value():
            raise ValueError("invalid settlement timestamp")
        return self._convert_timestamp(int(timestamp))

    def _terminal_result(self, order, response):
        """Validate legacy /info/order_detail without mutating the pending result.

        The documented single-order response has no echoed order_id. Its identity
        comes from the captured order-scoped query, currency/side checks, and the
        exact-entry claim below. Accept legacy object data or one documented item;
        never select an arbitrary item from an ambiguous multi-order response.
        """
        if not isinstance(response, dict) or response.get("status") != "0000":
            return None
        data = response.get("data")
        if isinstance(data, list):
            if len(data) != 1:
                return None
            data = data[0]
        if not isinstance(data, dict):
            return None
        if "order_id" in data and data["order_id"] != order["order_id"]:
            return None
        if (data.get("order_currency") != self.market
                or data.get("payment_currency") != self.market_currency):
            return None
        result_type = order["result"].get("type")
        if result_type not in ("buy", "sell"):
            return None
        if data.get("type") != ("bid" if result_type == "buy" else "ask"):
            return None
        state = data.get("order_status")
        if state not in ("Completed", "Cancel"):
            return None
        contracts = data.get("contract")
        if not isinstance(contracts, list):
            return None
        try:
            requested = self._settlement_number(data["order_qty"])
            if requested <= 0:
                return None
            amount, execution_value = Decimal(0), Decimal(0)
            date_time = None
            # Never accept a quantity bound after silently rounding away a fill.
            # Unusually precise totals remain unresolved rather than being guessed.
            with localcontext() as context:
                context.traps[Inexact] = True
                context.traps[Rounded] = True
                for contract in contracts:
                    if not isinstance(contract, dict):
                        return None
                    units = self._settlement_number(contract["units"])
                    price = self._settlement_number(contract["price"])
                    if units <= 0 or price <= 0:
                        return None
                    fill_time = self._settlement_time(contract["transaction_date"])
                    if date_time is None:
                        date_time = fill_time  # Preserve the first-contract convention.
                    amount += units
                    execution_value += units * price
            if amount > requested or (state == "Completed" and amount != requested):
                return None
            if state == "Cancel" and data.get("cancel_date") not in (None, ""):
                date_time = self._settlement_time(data["cancel_date"])
            if date_time is None:
                date_time = self._settlement_time(
                    data.get("transaction_date", data.get("order_date")))

            # Keep the existing positive-price valuation (which may be an
            # estimate), configured fee ratio and rounding. Actual fee/valuation
            # reconciliation is separate. Only absent/zero prices need fallback.
            raw_price = order["result"].get("price")
            price = Decimal(0) if raw_price is None else self._settlement_number(raw_price)
            if price == 0:
                raw_price = data.get("order_price")
                price = Decimal(0) if raw_price is None else self._settlement_number(raw_price)
            if price == 0 and amount > 0:
                price = execution_value / amount
            price, amount = float(price), float(amount)
            value = price * amount
            fee = value * self.commission_ratio
            if not all(math.isfinite(n) for n in (price, amount, value, fee, value + fee)):
                return None
            if contracts and (amount <= 0 or price <= 0 or value <= 0):
                return None
        except (KeyError, TypeError, ValueError, OverflowError, OSError, DecimalException):
            return None
        return {"state": "done", "amount": amount, "price": price, "date_time": date_time}

    def _complete_order(self, request_id, order, response):
        settlement = self._terminal_result(order, response)
        if settlement is None:
            return False
        with self._order_lock:
            if self.order_map.get(request_id) is not order:
                return False
            result = order["result"]
            result.update(settlement)
            del self.order_map[request_id]
        # At-most-once accounting/callback attempt, not durable delivery. Never
        # restore a claimed entry after client code raises, or run it under lock.
        self._call_callback(order["callback"], result)
        return True

    def _call_callback(self, callback, result):
        # Serialize existing BaseExchangeTrader accounting across cancel/poll.
        # A confirmed zero fill must not round or otherwise change held assets.
        with self._order_lock:
            amount = float(result["amount"])
            result_value = float(result["price"]) * amount
            fee = result_value * self.commission_ratio
            if amount and result["state"] == "done" and result["type"] == "buy":
                old_value = self.asset[0] * self.asset[1]
                new_value = old_value + result_value
                new_amount = round(self.asset[1] + amount, 6)
                avr_price = new_value / new_amount if new_amount else 0
                self.asset = (avr_price, new_amount)
                self.balance -= round(result_value + fee)
            elif amount and result["state"] == "done" and result["type"] == "sell":
                old_avr_price = self.asset[0]
                new_amount = round(self.asset[1] - amount, 6)
                if new_amount == 0:
                    old_avr_price = 0
                self.asset = (old_avr_price, new_amount)
                self.balance += round(result_value - fee)
        callback(result)

    def _send_market_order(self, is_buy, volume):
        """시장가 주문 전송 (Bithumb market_buy / market_sell, units 기준)"""
        final_volume = "{0:.4f}".format(round(float(volume), 4))
        endpoint = "/trade/market_buy" if is_buy else "/trade/market_sell"
        self.logger.info(f"MARKET ORDER ##### {'BUY' if is_buy else 'SELL'}")
        self.logger.info(f"{self.market}, units: {final_volume}")
        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "units": final_volume,
        }
        self.logger.debug(f"query :{query}")
        return self.bithumb_api_call(endpoint, query)

    def _send_limit_order(self, is_buy, price=None, volume=0.0001):
        """
        지정 가격 주문 전송

        Send a limit price order
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

        if (is_buy is True and latest_price < price) or (
            is_buy is False and latest_price > price
        ):
            self.logger.info(f"price optimized! ##### {price} -> {latest_price}")
            return latest_price

        return price

    def _query_order(self, order_id=None):
        """Query /info/order_detail for exactly one known exchange order ID.

        Legacy v1.2 data is an object or a singleton list. It carries currencies,
        side, order_status, requested order_qty and contract execution records;
        an echoed order_id is not documented. Cancel's executed quantity is the
        sum of contract.units, not order_qty or the cancellation ACK.
        https://apidocs.bithumb.com/v1.2.0/reference/거래-주문내역-상세-조회
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
        if not self.SERVER_URL:
            self.logger.error("API credentials are not configured")
            return None

        querystring = {"count": "1"}

        return self._request_get(
            f"{self.SERVER_URL}/public/transaction_history/{self.market}_{self.market_currency}",
            params=querystring,
        )

    def bithumb_api_call(self, endpoint, params):
        """빗썸 api wrapper
        nonce: it is an arbitrary number that may only be used once.
        api_sign: API signature information created in various combinations values.
        """
        if not self._validate_credentials():
            return None

        uri_array = dict(
            {"endpoint": endpoint}, **params
        )  # Concatenate the two arrays.

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

        return self._request_post(url, headers=headers, data=str_data)
