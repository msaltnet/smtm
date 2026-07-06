import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import UpbitNoticeDataProvider


SAMPLE = {
    "success": True,
    "data": {
        "list": [
            {
                "id": 12345,
                "title": "[상장] ABC(ABC) 원화 마켓 추가",
                "body": "ABC가 추가됩니다.",
                "listed_at": "2026-04-20T10:00:00+09:00",
                "category": "trade",
            },
            {
                "id": 12346,
                "title": "점검 안내",
                "body": "22:00~23:00 점검.",
                "listed_at": "2026-04-20T09:00:00+09:00",
                "category": "maintenance",
            },
        ]
    },
}


class UpbitNoticeDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_notice_items(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = UpbitNoticeDataProvider(count=5)
        info = dp.get_info()

        self.assertEqual(len(info), 2)
        first = info[0]
        self.assertEqual(first["type"], "notice")
        self.assertEqual(first["source"], "upbit")
        self.assertEqual(first["title"], "[상장] ABC(ABC) 원화 마켓 추가")
        self.assertEqual(first["body"], "ABC가 추가됩니다.")
        self.assertEqual(first["category"], "trade")
        self.assertIn("id=12345", first["url"])

    @patch("requests.get")
    def test_count_limit(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = UpbitNoticeDataProvider(count=1)
        info = dp.get_info()

        self.assertEqual(len(info), 1)

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(UpbitNoticeDataProvider().get_info(), [])

    @patch("requests.get")
    def test_data_as_plain_list(self, mock_get):
        """Upbit API가 data 를 list로 돌려주는 스키마 변형에도 동작해야 한다."""
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [{"id": 7, "title": "T", "body": "B", "listed_at": "x"}]
        }
        mock_get.return_value = response

        info = UpbitNoticeDataProvider().get_info()

        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["title"], "T")
