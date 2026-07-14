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

    def cancel_request(self, request_id):
        """거래 요청을 취소한다 (추후 작업에서 구현 예정)"""
        raise NotImplementedError(
            "BinanceTrader.cancel_request will be implemented in a later task"
        )

    def get_account_info(self):
        """계좌 정보를 요청한다 (추후 작업에서 구현 예정)"""
        raise NotImplementedError(
            "BinanceTrader.get_account_info will be implemented in a later task"
        )
