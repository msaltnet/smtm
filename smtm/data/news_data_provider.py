import xml.etree.ElementTree as ET
import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class NewsDataProvider(DataProvider):
    """
    공용 RSS 피드를 가져와 type='news' 형식의 딕셔너리 리스트로 변환해 주는 텍스트형 DataProvider.

    Fetches a public RSS feed and normalizes each item into a type='news' dict
    so it can be mixed into the existing DataProvider typed-list contract.

    - primary_candle을 생성하지 않으므로 단독으로 매매에 사용하지 않는다.
      복합 DataProvider(예: UpbitNewsDataProvider)의 빌딩 블록으로 사용한다.
    - 네트워크 실패·파싱 오류 시 빈 리스트를 반환하여 매매 루프를 막지 않는다.
    """

    NAME = "CRYPTO NEWS DP"
    CODE = "NWS"

    DEFAULT_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"
    DEFAULT_SOURCE = "coindesk"
    DEFAULT_COUNT = 5
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, source=None, count=None):
        self.logger = LogManager.get_logger("NewsDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._source = source or self.DEFAULT_SOURCE
        self._count = count or self.DEFAULT_COUNT

    def get_info(self):
        """최신 뉴스 항목을 type='news' 딕셔너리 리스트로 반환.

        Returns 예시:
        [
            {
                "type": "news",
                "date_time": "Mon, 15 Apr 2026 12:34:00 +0000",
                "source": "coindesk",
                "title": "...",
                "summary": "...",
                "url": "..."
            }
        ]
        """
        xml_text = self._fetch_feed()
        if xml_text is None:
            return []
        return self._parse_feed(xml_text)

    def _fetch_feed(self):
        try:
            response = request_with_retry(requests.get, self._url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as err:
            self.logger.warning(f"Failed to fetch news feed: {err}")
            return None

    def _parse_feed(self, xml_text):
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            self.logger.warning(f"Invalid RSS feed: {err}")
            return []

        items = root.findall(".//channel/item")
        results = []
        for item in items[: self._count]:
            results.append(
                {
                    "type": "news",
                    "date_time": (item.findtext("pubDate") or "").strip(),
                    "source": self._source,
                    "title": (item.findtext("title") or "").strip(),
                    "summary": (item.findtext("description") or "").strip(),
                    "url": (item.findtext("link") or "").strip(),
                }
            )
        return results
