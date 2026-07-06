import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class BinanceFundingRateDataProvider(DataProvider):
    """
    Binance 선물(premium index)에서 심볼별 펀딩비와 마크 가격을 가져와
    type='funding_rate' 딕셔너리 한 건으로 반환하는 DataProvider.

    Fetches the latest perpetual funding rate for `{currency}USDT` from
    Binance Futures and returns it as a `type='funding_rate'` dict.

    - 양(+) 펀딩은 롱 포지션이 숏에게 지급(시장이 과열됐을 수 있다는 신호),
      음(−) 펀딩은 숏이 롱에게 지급(공포 신호).
    - 실패·심볼 미존재 시 빈 리스트를 반환한다.
    """

    NAME = "BINANCE FUNDING RATE DP"
    CODE = "BFR"

    DEFAULT_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, symbol=None):
        self.logger = LogManager.get_logger("BinanceFundingRateDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._symbol = symbol or f"{currency.upper()}USDT"

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []

        funding_rate = self._to_float(payload.get("lastFundingRate"))
        mark_price = self._to_float(payload.get("markPrice"))
        index_price = self._to_float(payload.get("indexPrice"))

        return [
            {
                "type": "funding_rate",
                "source": "binance_futures",
                "symbol": payload.get("symbol", self._symbol),
                "funding_rate": funding_rate,
                "funding_rate_pct": funding_rate * 100 if funding_rate is not None else None,
                "mark_price": mark_price,
                "index_price": index_price,
                "next_funding_time": payload.get("nextFundingTime"),
                "time": payload.get("time"),
            }
        ]

    def _fetch(self):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={"symbol": self._symbol},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch binance funding rate: {err}")
            return None

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
