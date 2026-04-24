import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class BinanceLongShortRatioDataProvider(DataProvider):
    """
    Binance 선물 글로벌 롱/숏 계정 비율을
    type='long_short_ratio' 한 건으로 반환하는 DataProvider.

    Fetches the latest ratio of long vs. short retail accounts from
    https://fapi.binance.com/futures/data/globalLongShortAccountRatio
    (optionally topLongShortAccountRatio) and normalizes it into a
    single `type='long_short_ratio'` dict.

    - 키 불필요.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "BINANCE L/S RATIO DP"
    CODE = "BLS"

    BASE_URL = "https://fapi.binance.com/futures/data"
    DEFAULT_SCOPE = "global"  # or "top"
    DEFAULT_PERIOD = "5m"
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, symbol=None, period=None, scope=None):
        self.logger = LogManager.get_logger("BinanceLongShortRatioDataProvider")
        self.market = currency
        self.interval = interval
        self._symbol = symbol or f"{currency.upper()}USDT"
        self._period = period or self.DEFAULT_PERIOD
        self._scope = (scope or self.DEFAULT_SCOPE).lower()
        self._url = url or self._build_url(self._scope)

    def _build_url(self, scope):
        path = (
            "topLongShortAccountRatio"
            if scope == "top"
            else "globalLongShortAccountRatio"
        )
        return f"{self.BASE_URL}/{path}"

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, list) or not payload:
            return []
        latest = payload[-1] if isinstance(payload[-1], dict) else None
        if latest is None:
            return []

        ratio = self._to_float(latest.get("longShortRatio"))
        return [
            {
                "type": "long_short_ratio",
                "source": "binance_futures",
                "symbol": latest.get("symbol") or self._symbol,
                "period": self._period,
                "scope": self._scope,
                "long_short_ratio": ratio,
                "long_account_pct": self._to_pct(latest.get("longAccount")),
                "short_account_pct": self._to_pct(latest.get("shortAccount")),
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

    @classmethod
    def _to_pct(cls, value):
        parsed = cls._to_float(value)
        if parsed is None:
            return None
        return parsed * 100 if parsed <= 1 else parsed

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
            self.logger.warning(f"Failed to fetch long/short ratio: {err}")
            return None
