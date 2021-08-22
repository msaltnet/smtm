import unittest
from smtm import BithumbDataProvider
from unittest.mock import *
import requests


class BithumbDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("requests.get")
    def test_get_info_return_data_correctly(self, mock_get):
        dp = BithumbDataProvider("BTC")
        dummy_response = MagicMock()
        dummy_response.json.return_value = {
            "status": "0000",
            "data": [[1619874480000, "68934000", "68933000", "68980000", "68914000", ".69114496"]],
        }
        mock_get.return_value = dummy_response

        info = dp.get_info()

        self.assertEqual(info["market"], "BTC")
        self.assertEqual(info["date_time"], "2021-05-01T22:08:00")
        self.assertEqual(info["opening_price"], 68934000)
        self.assertEqual(info["high_price"], 68980000)
        self.assertEqual(info["low_price"], 68914000)
        self.assertEqual(info["closing_price"], 68933000)
        self.assertEqual(info["acc_price"], 0)
        self.assertEqual(info["acc_volume"], 0.69114496)
        mock_get.assert_called_once_with(dp.url)
        self.assertEqual(dp.url, "https://api.bithumb.com/public/candlestick/BTC_KRW/1m")

    @patch("requests.get")
    def test_get_info_NOT_throw_UserWarning_when_receive_invalid_data(self, mock_get):
        dp = BithumbDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.get_info()

    @patch("requests.get")
    def test_get_info_NOT_throw_UserWarning_when_receive_response_error(self, mock_get):
        dp = BithumbDataProvider()
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
        dp = BithumbDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.get_info()
