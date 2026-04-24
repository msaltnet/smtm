import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class CryptoGlobalDataProvider(DataProvider):
    """
    CoinGecko Global 엔드포인트로 전체 크립토 시장 거시 지표를
    type='crypto_global' 한 건으로 반환하는 DataProvider.

    Fetches total market cap, 24h volume, BTC/ETH/stablecoin dominance, and
    market-cap change from https://api.coingecko.com/api/v3/global and
    normalizes the result into a single `type='crypto_global'` entry.

    - 키 불필요(무료 티어).
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "CRYPTO GLOBAL DP"
    CODE = "CGL"

    DEFAULT_URL = "https://api.coingecko.com/api/v3/global"
    STABLECOIN_SYMBOLS = ("usdt", "usdc", "dai", "busd", "fdusd", "tusd")
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None):
        self.logger = LogManager.get_logger("CryptoGlobalDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        total_mcap = data.get("total_market_cap") or {}
        total_vol = data.get("total_volume") or {}
        dominance = data.get("market_cap_percentage") or {}
        if not isinstance(dominance, dict):
            dominance = {}

        stablecoin_dominance = sum(
            v for k, v in dominance.items()
            if k in self.STABLECOIN_SYMBOLS and isinstance(v, (int, float))
        )

        return [
            {
                "type": "crypto_global",
                "source": "coingecko",
                "total_market_cap_usd": total_mcap.get("usd") if isinstance(total_mcap, dict) else None,
                "total_volume_24h_usd": total_vol.get("usd") if isinstance(total_vol, dict) else None,
                "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
                "btc_dominance_pct": dominance.get("btc"),
                "eth_dominance_pct": dominance.get("eth"),
                "stablecoin_dominance_pct": stablecoin_dominance or None,
                "dominance": dominance,
                "active_cryptocurrencies": data.get("active_cryptocurrencies"),
                "markets": data.get("markets"),
                "updated_at": data.get("updated_at"),
            }
        ]

    def _fetch(self):
        try:
            response = request_with_retry(requests.get, self._url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch crypto global data: {err}")
            return None
