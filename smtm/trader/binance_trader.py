import time
import hmac
import hashlib
from urllib.parse import urlencode
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

    def cancel_request(self, request_id):
        """거래 요청을 취소한다 (추후 작업에서 구현 예정)"""
        raise NotImplementedError(
            "BinanceTrader.cancel_request will be implemented in a later task"
        )

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
