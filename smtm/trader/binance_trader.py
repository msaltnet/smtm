import time
import hmac
import hashlib
from urllib.parse import urlencode
import requests
from ..http_session import request_with_retry
from .base_exchange_trader import BaseExchangeTrader
from . import order_spec


class BinanceTrader(BaseExchangeTrader):
    """
    바이낸스 현물(spot) 거래소를 통한 거래 요청 및 계좌 조회를 처리하는 Trader

    BinanceTrader processes spot trading requests and account inquiries via Binance.

    id: 요청 정보 id
    type: 거래 유형 buy, sell, cancel
    price: 거래 가격 (USDT)
    amount: 거래 수량 (코인)
    """

    AVAILABLE_CURRENCY = {
        "BTC": ("BTCUSDT", "BTC"),
        "ETH": ("ETHUSDT", "ETH"),
        "DOGE": ("DOGEUSDT", "DOGE"),
        "XRP": ("XRPUSDT", "XRP"),
    }
    NAME = "Binance"
    CODE = "BNC"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})

    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True,
        access_key_env=None, secret_key_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="BinanceTrader",
            worker_name="BinanceTrader-Worker",
            env_key_names=(
                access_key_env or "BINANCE_API_ACCESS_KEY",
                secret_key_env or "BINANCE_API_SECRET_KEY",
                "BINANCE_API_SERVER_URL",
            ),
        )
        if not self.SERVER_URL:
            self.SERVER_URL = "https://api.binance.com"
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    def _create_signature(self, query_string):
        return hmac.new(
            self.SECRET_KEY.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()

    def _signed_query(self, params):
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = self._create_signature(query_string)
        return f"{query_string}&signature={signature}"

    def _auth_headers(self):
        return {"X-MBX-APIKEY": self.ACCESS_KEY}

    def get_trade_tick(self):
        """최근 체결가(현재가) 조회 — public 엔드포인트"""
        return self._request_get(
            self.SERVER_URL + "/api/v3/ticker/price",
            params={"symbol": self.market},
        )

    def get_account_info(self):
        """계좌 정보를 요청한다 (로컬 잔고/자산 + 실시간 시세)

        Returns:
            {
                balance: 계좌 현금 잔고 (USDT)
                asset: {코인: (평균 매입가, 수량)}
                quote: {코인: 현재가}
                date_time: 현재 시간
            }
        """
        from datetime import datetime

        result = {
            "balance": self.balance,
            "asset": {self.market_currency: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        trade_info = self.get_trade_tick()
        if trade_info is not None and "price" in trade_info:
            result["quote"][self.market_currency] = float(trade_info["price"])
        else:
            self.logger.error("fail query quote")
        self.logger.debug(f"account info {result}")
        return result

    def _query_order(self, order_id):
        """주문 상태 조회 (signed GET /api/v3/order)"""
        if not self._validate_credentials():
            return None
        query_string = self._signed_query(
            {"symbol": self.market, "orderId": order_id}).encode()
        return self._request_get(
            self.SERVER_URL + "/api/v3/order",
            params=query_string,
            headers=self._auth_headers(),
        )

    def _update_order_result(self, task):
        del task
        waiting_request = {}
        self.logger.debug(f"waiting order count {len(self.order_map)}")
        for request_id, order in self.order_map.items():
            response = self._query_order(order["order_id"])
            if response is None:
                waiting_request[request_id] = order
                continue
            if response.get("status") == "FILLED":
                from datetime import datetime

                result = order["result"]
                result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
                result["price"] = self._fill_price(response)
                result["amount"] = float(response.get("executedQty", 0))
                result["state"] = "done"
                self._call_callback(order["callback"], result)
            else:
                waiting_request[request_id] = order

        self.order_map = waiting_request
        self.logger.debug(f"After update, waiting order count {len(self.order_map)}")
        self._stop_timer()
        if len(self.order_map) > 0:
            self._start_timer()

    @staticmethod
    def _fill_price(response):
        """체결 단가. 시장가 주문은 price가 0으로 오므로
        체결총액(cummulativeQuoteQty)/체결수량(executedQty)으로 평단을 산출한다."""
        price = float(response["price"]) if response.get("price") else 0
        if price > 0:
            return price
        executed = float(response.get("executedQty", 0))
        quote = float(response.get("cummulativeQuoteQty", 0))
        return quote / executed if executed else 0

    def cancel_request(self, request_id):
        """거래 요청을 취소한다"""
        if request_id not in self.order_map:
            self.logger.debug(f"already canceled or unknown: {request_id}")
            return

        order = self.order_map[request_id]
        del self.order_map[request_id]
        result = order["result"]
        response = self._cancel_order(order["order_id"])

        if response is None:
            # 이미 체결됐을 수 있으므로 조회로 확정
            response = self._query_order(order["order_id"])
            if response is None:
                return

        from datetime import datetime

        result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
        result["price"] = self._fill_price(response)
        result["amount"] = float(response.get("executedQty", 0))
        result["state"] = "done"
        self._call_callback(order["callback"], result)

    def _cancel_order(self, order_id):
        """주문 취소 (signed DELETE /api/v3/order)"""
        if not self._validate_credentials():
            return None
        query_string = self._signed_query(
            {"symbol": self.market, "orderId": order_id}).encode()
        try:
            response = request_with_retry(
                requests.delete,
                self.SERVER_URL + "/api/v3/order",
                params=query_string,
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            return response.json()
        except (ValueError, requests.exceptions.RequestException) as err:
            self.logger.error(f"cancel order fail: {err}")
            return None

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
            # price==0 은 기존 no-op(hold) 신호 — 지정가에서는 무시
            self.logger.warning("[REJECT] limit order requires price")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning(
                f"[REJECT] balance is too small! "
                f"{float(request['price']) * float(request['amount'])} > {self.balance}"
            )
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        side = "BUY" if is_buy else "SELL"
        response = self._send_order(
            side, ord_type, request["price"], request["amount"])
        if response is None or "orderId" not in response:
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["orderId"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()

    def _send_order(self, side, ord_type, price, amount):
        """Binance 현물 주문 전송 (signed POST /api/v3/order)

        - 지정가:      type=LIMIT, timeInForce=GTC, quantity, price
        - 시장가 매도:  type=MARKET, quantity
        - 시장가 매수:  type=MARKET, quoteOrderQty(=price*amount, USDT 총액)
        """
        if not self._validate_credentials():
            return None

        params = {"symbol": self.market, "side": side}
        if ord_type == order_spec.MARKET and side == "BUY":
            params["type"] = "MARKET"
            params["quoteOrderQty"] = float(price) * float(amount)
        elif ord_type == order_spec.MARKET:
            params["type"] = "MARKET"
            params["quantity"] = float(amount)
        else:
            params["type"] = "LIMIT"
            params["timeInForce"] = "GTC"
            params["quantity"] = float(amount)
            params["price"] = float(price)

        self.logger.info(f"ORDER ##### {side} {params['type']}")
        self.logger.info(f"{self.market}, params: {params}")

        query_string = self._signed_query(params).encode()
        return self._request_post(
            self.SERVER_URL + "/api/v3/order",
            params=query_string,
            headers=self._auth_headers(),
        )
