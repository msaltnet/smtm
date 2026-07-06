import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class HackerNewsDataProvider(DataProvider):
    """
    HackerNews Algolia 공개 API에서 암호화폐 관련 최근 스토리를 가져와
    type='hackernews' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches recent stories matching a query (default: crypto/bitcoin)
    from `hn.algolia.com` and normalizes each into a `type='hackernews'`
    dict — useful as a tech/developer-community signal.

    - 무료 공개 API이며 키가 필요 없다.
    - 실패 시 빈 리스트를 반환한다.
    """

    NAME = "HACKERNEWS DP"
    CODE = "HNS"

    DEFAULT_URL = "https://hn.algolia.com/api/v1/search_by_date"
    DEFAULT_QUERY = "bitcoin OR crypto OR ethereum"
    DEFAULT_COUNT = 5
    TIMEOUT = 5

    def __init__(
        self, currency="BTC", interval=60, url=None, query=None, count=None
    ):
        self.logger = LogManager.get_logger("HackerNewsDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._query = query or self.DEFAULT_QUERY
        self._count = count or self.DEFAULT_COUNT

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        hits = payload.get("hits")
        if not isinstance(hits, list):
            return []

        results = []
        for hit in hits[: self._count]:
            if not isinstance(hit, dict):
                continue
            results.append(
                {
                    "type": "hackernews",
                    "source": "hackernews",
                    "title": hit.get("title") or hit.get("story_title") or "",
                    "url": hit.get("url") or self._story_url(hit.get("objectID")),
                    "author": hit.get("author", ""),
                    "points": hit.get("points"),
                    "num_comments": hit.get("num_comments"),
                    "date_time": hit.get("created_at", ""),
                }
            )
        return results

    def _fetch(self):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={"query": self._query, "tags": "story", "hitsPerPage": self._count},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch hackernews data: {err}")
            return None

    @staticmethod
    def _story_url(object_id):
        if not object_id:
            return ""
        return f"https://news.ycombinator.com/item?id={object_id}"
