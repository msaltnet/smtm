import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class CoinGeckoDataProvider(DataProvider):
    """
    CoinGecko의 공개 Simple Price 엔드포인트를 사용해
    type='price_snapshot' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches price, market cap, 24h volume, and 24h change from CoinGecko
    (no API key required for the free tier) and normalizes the result
    into a `type='price_snapshot'` dict.

    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "COINGECKO DP"
    CODE = "CGK"

    DEFAULT_URL = "https://api.coingecko.com/api/v3/simple/price"
    DEFAULT_VS_CURRENCIES = "usd,krw"
    TIMEOUT = 5

    CURRENCY_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "DOGE": "dogecoin",
        "XRP": "ripple",
    }

    def __init__(self, currency="BTC", interval=60, url=None, vs_currencies=None):
        self.logger = LogManager.get_logger("CoinGeckoDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._vs_currencies = vs_currencies or self.DEFAULT_VS_CURRENCIES

    def get_info(self):
        """가격/시총/거래량/변동률을 type='price_snapshot' 한 건으로 반환."""
        coin_id = self.CURRENCY_TO_ID.get(self.market.upper())
        if not coin_id:
            self.logger.warning(f"Unsupported currency: {self.market}")
            return []

        payload = self._fetch(coin_id)
        if payload is None:
            return []
        entry = payload.get(coin_id) if isinstance(payload, dict) else None
        if not isinstance(entry, dict):
            return []

        return [
            {
                "type": "price_snapshot",
                "source": "coingecko",
                "coin_id": coin_id,
                "currency": self.market.upper(),
                "prices": {
                    code: entry.get(code)
                    for code in self._vs_currencies.split(",")
                    if entry.get(code) is not None
                },
                "market_cap_usd": entry.get("usd_market_cap"),
                "volume_24h_usd": entry.get("usd_24h_vol"),
                "change_24h_pct": entry.get("usd_24h_change"),
            }
        ]

    def _fetch(self, coin_id):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={
                    "ids": coin_id,
                    "vs_currencies": self._vs_currencies,
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                },
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch coingecko data: {err}")
            return None
