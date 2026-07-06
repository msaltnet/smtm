import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class BinanceOpenInterestDataProvider(DataProvider):
    """
    Binance 선물(USDT-M)의 누적 미결제약정(Open Interest)을
    type='open_interest' 한 건으로 반환하는 DataProvider.

    Fetches the latest aggregated open interest in contracts and notional
    value from https://fapi.binance.com/futures/data/openInterestHist and
    normalizes it into a single `type='open_interest'` dict.

    - 키 불필요.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "BINANCE OPEN INTEREST DP"
    CODE = "BOI"

    DEFAULT_URL = "https://fapi.binance.com/futures/data/openInterestHist"
    DEFAULT_PERIOD = "5m"
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, symbol=None, period=None):
        self.logger = LogManager.get_logger("BinanceOpenInterestDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._symbol = symbol or f"{currency.upper()}USDT"
        self._period = period or self.DEFAULT_PERIOD

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, list) or not payload:
            return []
        latest = payload[-1] if isinstance(payload[-1], dict) else None
        if latest is None:
            return []

        oi_contracts = self._to_float(latest.get("sumOpenInterest"))
        oi_notional = self._to_float(latest.get("sumOpenInterestValue"))
        return [
            {
                "type": "open_interest",
                "source": "binance_futures",
                "symbol": latest.get("symbol") or self._symbol,
                "period": self._period,
                "open_interest_contracts": oi_contracts,
                "open_interest_notional_usd": oi_notional,
                "timestamp": latest.get("timestamp"),
            }
        ]

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fetch(self):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={"symbol": self._symbol, "period": self._period, "limit": 1},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch open interest: {err}")
            return None
