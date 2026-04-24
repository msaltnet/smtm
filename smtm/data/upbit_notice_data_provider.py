import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class UpbitNoticeDataProvider(DataProvider):
    """
    Upbit의 공개 공지사항(api-manager 노출 엔드포인트)을
    type='notice' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches recent Upbit notices and normalizes each into a
    `type='notice'` dict so exchange announcements (상장·점검·이벤트 등)
    can flow into the LLM alongside candles.

    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    - Upbit 공지 API는 비공식으로 분류되므로 응답 스키마가 바뀔 수 있다.
      방어적 파싱으로 누락 필드는 빈 문자열로 채운다.
    """

    NAME = "UPBIT NOTICE DP"
    CODE = "UPT"

    DEFAULT_URL = "https://api-manager.upbit.com/api/v1/notices"
    DEFAULT_COUNT = 5
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, count=None):
        self.logger = LogManager.get_logger("UpbitNoticeDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._count = count or self.DEFAULT_COUNT

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, dict):
            items = data.get("list") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []

        results = []
        for item in items[: self._count]:
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "type": "notice",
                    "source": "upbit",
                    "title": (item.get("title") or "").strip(),
                    "body": (item.get("body") or "").strip(),
                    "url": self._build_url(item.get("id")),
                    "date_time": item.get("listed_at") or item.get("created_at") or "",
                    "category": item.get("category") or "",
                }
            )
        return results

    def _fetch(self):
        try:
            response = request_with_retry(
                requests.get,
                self._url,
                params={"page": 1, "per_page": self._count, "thread_name": "general"},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch upbit notices: {err}")
            return None

    @staticmethod
    def _build_url(notice_id):
        if notice_id is None:
            return ""
        return f"https://upbit.com/service_center/notice?id={notice_id}"
