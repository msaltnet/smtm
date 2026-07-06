import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class CoinCapDataProvider(DataProvider):
    """
    CoinCap v2 assets 엔드포인트로 가격/시총/거래량을
    type='price_snapshot' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches price(USD), market cap, 24h volume/change, supply, and rank from
    https://api.coincap.io/v2/assets/{id} and normalizes the result into a
    `type='price_snapshot'` dict. CoinGecko보다 rate limit이 관대하므로 백업·
    교차검증용으로 사용한다.

    - 키 불필요.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "COINCAP DP"
    CODE = "CCP"

    DEFAULT_URL = "https://api.coincap.io/v2/assets"
    TIMEOUT = 5

    CURRENCY_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "DOGE": "dogecoin",
        "XRP": "xrp",
    }

    def __init__(self, currency="BTC", interval=60, url=None):
        self.logger = LogManager.get_logger("CoinCapDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL

    def get_info(self):
        asset_id = self.CURRENCY_TO_ID.get(self.market.upper())
        if not asset_id:
            self.logger.warning(f"Unsupported currency: {self.market}")
            return []

        payload = self._fetch(asset_id)
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        return [
            {
                "type": "price_snapshot",
                "source": "coincap",
                "coin_id": asset_id,
                "currency": self.market.upper(),
                "prices": {"usd": self._to_float(data.get("priceUsd"))},
                "market_cap_usd": self._to_float(data.get("marketCapUsd")),
                "volume_24h_usd": self._to_float(data.get("volumeUsd24Hr")),
                "change_24h_pct": self._to_float(data.get("changePercent24Hr")),
                "supply": self._to_float(data.get("supply")),
                "max_supply": self._to_float(data.get("maxSupply")),
                "rank": data.get("rank"),
                "vwap_24h_usd": self._to_float(data.get("vwap24Hr")),
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

    def _fetch(self, asset_id):
        try:
            response = request_with_retry(
                requests.get,
                f"{self._url}/{asset_id}",
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch coincap data: {err}")
            return None
