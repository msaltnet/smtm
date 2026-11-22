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
    - provider=None: 기존 open.er-api.com API와 출력 결과를 그대로 유지한다.
    - provider="allratestoday": ECB 일일 기준환율(실시간 시세 아님)을
      https://allratestoday.com/api/open/latest/{BASE} 에서 선택적으로 조회한다.
      제공 통화가 적고 주말에는 마지막 영업일 데이터가 반환될 수 있다.
      공개된 페이지에 환율을 표시하면 https://allratestoday.com 출처 링크가
      필요하며, 백엔드 내부 처리에는 필요하지 않다.
      이 무료 API의 IP별 제한은 분당 1회이므로 호출 주기에 주의해야 한다.
    - 기존 url 재정의는 기본 provider에서만 유지한다. 선택적 provider와
      임의의 URL을 조합하면 잘못된 출처가 붙을 수 있어 거부한다.
    """

    NAME = "EXCHANGE RATE DP"
    CODE = "FXR"

    DEFAULT_BASE = "USD"
    DEFAULT_QUOTES = ("KRW", "JPY", "EUR", "CNY")
    TIMEOUT = 5
    DEFAULT_PROVIDER = "open.er-api.com"
    PROVIDER_ENDPOINTS = {
        DEFAULT_PROVIDER: "https://open.er-api.com/v6/latest",
        "allratestoday": "https://allratestoday.com/api/open/latest",
    }

    def __init__(
        self, currency="BTC", interval=60, base=None, quotes=None, url=None,
        provider=None,
    ):
        chosen_provider = self.DEFAULT_PROVIDER if provider is None else provider
        if (not isinstance(chosen_provider, str)
                or chosen_provider not in self.PROVIDER_ENDPOINTS):
            raise ValueError(f"Unsupported exchange rate provider: {chosen_provider!r}")
        if url is not None and chosen_provider != self.DEFAULT_PROVIDER:
            raise ValueError("Custom url cannot be combined with an alternate provider")

        self.logger = LogManager.get_logger("ExchangeRateDataProvider")
        self.market = currency
        self.interval = interval
        self._base = (base or self.DEFAULT_BASE).upper()
        self._quotes = tuple(q.upper() for q in (quotes or self.DEFAULT_QUOTES))
        self._source = chosen_provider
        self._url = url or f"{self.PROVIDER_ENDPOINTS[chosen_provider]}/{self._base}"

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
                "source": self._source,
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
