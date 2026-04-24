import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class FearGreedDataProvider(DataProvider):
    """
    alternative.me의 공개 Crypto Fear & Greed Index를 가져와
    type='sentiment_index' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches the public Crypto Fear & Greed Index from alternative.me
    (no API key required) and normalizes it into a `type='sentiment_index'`
    dict so it can be mixed into the DataProvider typed-list contract.

    - 0~100 스케일의 sentiment 지표(낮을수록 공포, 높을수록 탐욕)를 한 건 또는 N건 반환.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "FEAR & GREED INDEX DP"
    CODE = "FGI"

    DEFAULT_URL = "https://api.alternative.me/fng/"
    DEFAULT_LIMIT = 1
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, limit=None):
        self.logger = LogManager.get_logger("FearGreedDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._limit = limit or self.DEFAULT_LIMIT

    def get_info(self):
        """Fear & Greed 지수를 type='sentiment_index' 딕셔너리 리스트로 반환.

        Returns 예시:
        [
            {
                "type": "sentiment_index",
                "source": "alternative.me/fng",
                "index_name": "crypto_fear_and_greed",
                "value": 54,
                "classification": "Neutral",
                "date_time": "1713628800"
            }
        ]
        """
        payload = self._fetch()
        if payload is None:
            return []
        return self._to_items(payload)

    def _fetch(self):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={"limit": self._limit},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch fear & greed index: {err}")
            return None

    def _to_items(self, payload):
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return []

        results = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            raw_value = entry.get("value")
            try:
                value = int(raw_value) if raw_value is not None else None
            except (TypeError, ValueError):
                value = None
            results.append(
                {
                    "type": "sentiment_index",
                    "source": "alternative.me/fng",
                    "index_name": "crypto_fear_and_greed",
                    "value": value,
                    "classification": entry.get("value_classification", ""),
                    "date_time": entry.get("timestamp", ""),
                }
            )
        return results
