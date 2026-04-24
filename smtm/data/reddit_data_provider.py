import xml.etree.ElementTree as ET
import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class RedditDataProvider(DataProvider):
    """
    Reddit 서브레딧의 최신 게시물을 가져와 type='reddit' 딕셔너리 리스트로 반환하는
    소셜 텍스트형 DataProvider.

    Fetches a subreddit's public Atom feed (`/r/{sub}/.rss`) and normalizes
    each entry into a `type='reddit'` dict so it can be mixed into the
    DataProvider typed-list contract alongside candles and news.

    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
      복합 DataProvider(예: UpbitSocialDataProvider)의 빌딩 블록으로 사용한다.
    - User-Agent가 없으면 Reddit이 429를 돌려보내기 때문에 항상 명시한다.
    - 네트워크·파싱 실패 시 빈 리스트를 반환하여 매매 루프를 막지 않는다.
    """

    NAME = "REDDIT DP"
    CODE = "RDT"

    DEFAULT_SUBREDDIT = "CryptoCurrency"
    DEFAULT_COUNT = 5
    DEFAULT_USER_AGENT = "smtm/1.7 (+https://github.com/msaltnet/smtm)"
    TIMEOUT = 5

    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    def __init__(
        self,
        currency="BTC",
        interval=60,
        subreddit=None,
        count=None,
        user_agent=None,
    ):
        self.logger = LogManager.get_logger("RedditDataProvider")
        self.market = currency
        self.interval = interval
        self._subreddit = subreddit or self.DEFAULT_SUBREDDIT
        self._count = count or self.DEFAULT_COUNT
        self._user_agent = user_agent or self.DEFAULT_USER_AGENT

    @property
    def feed_url(self):
        return f"https://www.reddit.com/r/{self._subreddit}/.rss"

    def get_info(self):
        """최신 게시물을 type='reddit' 딕셔너리 리스트로 반환.

        Returns 예시:
        [
            {
                "type": "reddit",
                "date_time": "2026-04-20T10:00:00+00:00",
                "source": "reddit/CryptoCurrency",
                "title": "...",
                "summary": "...",
                "url": "https://www.reddit.com/...",
                "author": "u/..."
            }
        ]
        """
        xml_text = self._fetch_feed()
        if xml_text is None:
            return []
        return self._parse_feed(xml_text)

    def _fetch_feed(self):
        try:
            response = request_with_retry(
                requests.get,
                self.feed_url,
                headers={"User-Agent": self._user_agent},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as err:
            self.logger.warning(f"Failed to fetch reddit feed: {err}")
            return None

    def _parse_feed(self, xml_text):
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            self.logger.warning(f"Invalid reddit feed: {err}")
            return []

        entries = root.findall("atom:entry", self.ATOM_NS)
        results = []
        for entry in entries[: self._count]:
            results.append(
                {
                    "type": "reddit",
                    "date_time": self._findtext(entry, "atom:updated"),
                    "source": f"reddit/{self._subreddit}",
                    "title": self._findtext(entry, "atom:title"),
                    "summary": self._findtext(entry, "atom:content"),
                    "url": self._find_link(entry),
                    "author": self._findtext(entry, "atom:author/atom:name"),
                }
            )
        return results

    def _findtext(self, element, path):
        value = element.findtext(path, namespaces=self.ATOM_NS)
        return (value or "").strip()

    def _find_link(self, entry):
        link = entry.find("atom:link", self.ATOM_NS)
        if link is None:
            return ""
        return link.get("href", "")


class CryptoCurrencyRedditDataProvider(RedditDataProvider):
    """r/CryptoCurrency 프리셋."""

    NAME = "R/CRYPTOCURRENCY DP"
    CODE = "RCC"
    DEFAULT_SUBREDDIT = "CryptoCurrency"


class BitcoinRedditDataProvider(RedditDataProvider):
    """r/Bitcoin 프리셋."""

    NAME = "R/BITCOIN DP"
    CODE = "RBT"
    DEFAULT_SUBREDDIT = "Bitcoin"
