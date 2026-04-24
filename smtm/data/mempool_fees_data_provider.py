import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class MempoolFeesDataProvider(DataProvider):
    """
    mempool.space의 공개 /api/v1/fees/recommended 엔드포인트를 사용해
    BTC 네트워크 수수료 권장값을 type='mempool_fees' 한 건으로 반환.

    Returns BTC fee recommendations in sat/vB as a single
    `type='mempool_fees'` dict.

    - BTC 전용. 다른 통화에서는 빈 리스트를 반환한다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "MEMPOOL FEES DP"
    CODE = "MPF"

    DEFAULT_URL = "https://mempool.space/api/v1/fees/recommended"
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None):
        self.logger = LogManager.get_logger("MempoolFeesDataProvider")
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
                "type": "mempool_fees",
                "source": "mempool.space",
                "chain": "bitcoin",
                "unit": "sat/vB",
                "fastest_fee": payload.get("fastestFee"),
                "half_hour_fee": payload.get("halfHourFee"),
                "hour_fee": payload.get("hourFee"),
                "economy_fee": payload.get("economyFee"),
                "minimum_fee": payload.get("minimumFee"),
            }
        ]

    def _fetch(self):
        try:
            response = request_with_retry(requests.get, self._url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch mempool fees: {err}")
            return None
