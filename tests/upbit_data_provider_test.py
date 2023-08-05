import unittest
from smtm import UpbitDataProvider
from unittest.mock import *
import requests


class UpbitDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("requests.get")
    def test_get_info_return_data_correctly(self, mock_get):
        dp = UpbitDataProvider("BTC")
        dummy_response = MagicMock()
        dummy_response.json.return_value = [
            {
                "market": "BTC_KRW",
                "candle_date_time_utc": "2020-03-10T13:52:00",
                "candle_date_time_kst": "2020-03-10T22:52:00",
                "opening_price": 9777000.00000000,
                "high_price": 9778000.00000000,
                "low_price": 9763000.00000000,
                "trade_price": 9778000.00000000,
                "timestamp": 1583848334534,
                "candle_acc_trade_price": 11277224.71063000,
                "candle_acc_trade_volume": 1.15377852,
                "unit": 1,
            }
        ]
        mock_get.return_value = dummy_response

        info = dp.get_info()

        self.assertEqual(info["market"], "BTC")
        self.assertEqual(info["date_time"], "2020-03-10T22:52:00")
        self.assertEqual(info["opening_price"], 9777000)
        self.assertEqual(info["high_price"], 9778000)
        self.assertEqual(info["low_price"], 9763000)
        self.assertEqual(info["closing_price"], 9778000)
        self.assertEqual(info["acc_price"], 11277224.71063000)
        self.assertEqual(info["acc_volume"], 1.15377852)
        mock_get.assert_called_once_with(dp.URL, params={"market": "KRW-BTC", "count": 1})

    @patch("requests.get")
    def test_get_info_NOT_throw_UserWarning_when_receive_invalid_data(self, mock_get):
        dp = UpbitDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.get_info()

    @patch("requests.get")
    def test_get_info_NOT_throw_UserWarning_when_receive_response_error(self, mock_get):
        dp = UpbitDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.get_info()

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_when_connection_fail(self, mock_get):
        dp = UpbitDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.get_info()

    def test_initialize_should_set_correct_url_with_interval(self):
        dp = UpbitDataProvider("BTC", 60)
        self.assertEqual(dp.URL, "https://api.upbit.com/v1/candles/minutes/1")
        dp = UpbitDataProvider("BTC", 180)
        self.assertEqual(dp.URL, "https://api.upbit.com/v1/candles/minutes/3")
        dp = UpbitDataProvider("BTC", 300)
        self.assertEqual(dp.URL, "https://api.upbit.com/v1/candles/minutes/5")
        self.assertEqual(UpbitDataProvider.URL, "https://api.upbit.com/v1/candles/minutes/1")
        dp = UpbitDataProvider("BTC", 600)
        self.assertEqual(dp.URL, "https://api.upbit.com/v1/candles/minutes/10")

        with self.assertRaises(UserWarning):
            dp = UpbitDataProvider("BTC", 1)

    @patch("requests.get")
    def test_get_info_should_call_correct_url_with_different_interval(self, mock_get):
        dp = UpbitDataProvider("BTC", 60)
        dp.get_info()
        expected_url = "https://api.upbit.com/v1/candles/minutes/1"
        mock_get.assert_called_once_with(expected_url, params={"market": "KRW-BTC", "count": 1})

        dp = UpbitDataProvider("BTC", 180)
        dp.get_info()
        expected_url = "https://api.upbit.com/v1/candles/minutes/3"
        mock_get.assert_called_with(expected_url, params={"market": "KRW-BTC", "count": 1})

        dp = UpbitDataProvider("BTC", 300)
        dp.get_info()
        expected_url = "https://api.upbit.com/v1/candles/minutes/5"
        mock_get.assert_called_with(expected_url, params={"market": "KRW-BTC", "count": 1})

        dp = UpbitDataProvider("BTC", 600)
        dp.get_info()
        expected_url = "https://api.upbit.com/v1/candles/minutes/10"
        mock_get.assert_called_with(expected_url, params={"market": "KRW-BTC", "count": 1})
