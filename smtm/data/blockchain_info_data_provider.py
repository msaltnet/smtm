import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class BlockchainInfoDataProvider(DataProvider):
    """
    blockchain.info의 공개 /stats 엔드포인트를 사용해 BTC 네트워크 통계를
    type='onchain_stats' 딕셔너리 한 건으로 반환하는 DataProvider.

    Returns BTC network stats (hashrate, difficulty, miners revenue,
    block count, mempool size, ...) in a single `type='onchain_stats'` dict.

    - BTC 전용. 다른 통화에서는 빈 리스트를 반환한다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "BLOCKCHAIN.INFO ONCHAIN DP"
    CODE = "BCI"

    DEFAULT_URL = "https://api.blockchain.info/stats"
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None):
        self.logger = LogManager.get_logger("BlockchainInfoDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL

    def get_info(self):
        if self.market.upper() != "BTC":
            return []
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        return [
            {
                "type": "onchain_stats",
                "source": "blockchain.info",
                "chain": "bitcoin",
                "hash_rate_ghs": payload.get("hash_rate"),
                "difficulty": payload.get("difficulty"),
                "total_btc": payload.get("totalbc"),
                "n_blocks_total": payload.get("n_blocks_total"),
                "n_tx_24h": payload.get("n_tx"),
                "minutes_between_blocks": payload.get("minutes_between_blocks"),
                "miners_revenue_usd": payload.get("miners_revenue_usd"),
                "market_price_usd": payload.get("market_price_usd"),
                "timestamp": payload.get("timestamp"),
            }
        ]

    def _fetch(self):
        try:
            response = request_with_retry(requests.get, self._url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch blockchain.info stats: {err}")
            return None
