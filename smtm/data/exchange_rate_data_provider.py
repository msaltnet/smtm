import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class ExchangeRateDataProvider(DataProvider):
    """
    open.er-api.com의 공개 환율 API를 사용해 base 통화 대비 여러 통화 환율을
    type='exchange_rate' 딕셔너리 한 건으로 반환하는 DataProvider.

    Fetches exchange rates from a base currency (default: USD) to a
    configurable set of quote currencies and returns them as a single
    `type='exchange_rate'` dict — useful for price normalization and
    macro context (e.g., USD/KRW for Upbit KRW pairs).

    - 무료 공개 API로 키가 필요 없다.
    - 실패 시 빈 리스트를 반환한다.
    """

    NAME = "EXCHANGE RATE DP"
    CODE = "FXR"

    DEFAULT_BASE = "USD"
    DEFAULT_QUOTES = ("KRW", "JPY", "EUR", "CNY")
    TIMEOUT = 5

    def __init__(
        self, currency="BTC", interval=60, base=None, quotes=None, url=None
    ):
        self.logger = LogManager.get_logger("ExchangeRateDataProvider")
        self.market = currency
        self.interval = interval
        self._base = (base or self.DEFAULT_BASE).upper()
        self._quotes = tuple(q.upper() for q in (quotes or self.DEFAULT_QUOTES))
        self._url = url or f"https://open.er-api.com/v6/latest/{self._base}"

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        if payload.get("result") != "success":
            return []
        rates = payload.get("rates")
        if not isinstance(rates, dict):
            return []

        filtered = {q: rates.get(q) for q in self._quotes if rates.get(q) is not None}
        if not filtered:
            return []

        return [
            {
                "type": "exchange_rate",
                "source": "open.er-api.com",
                "base": self._base,
                "rates": filtered,
                "date_time": payload.get("time_last_update_utc", ""),
            }
        ]

    def _fetch(self):
        try:
            response = request_with_retry(requests.get, self._url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch exchange rates: {err}")
            return None
