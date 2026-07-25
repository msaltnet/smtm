import unittest
from unittest.mock import patch
from smtm import OkxDataProvider


class OkxDataProviderTests(unittest.TestCase):
    def test_get_kst_time_from_unix_time_ms_should_return_correct_string(self):
        self.assertEqual(
            OkxDataProvider._get_kst_time_from_unix_time_ms(1622563200000),
            "2021-06-02T01:00:00",
        )
        self.assertEqual(
            OkxDataProvider._get_kst_time_from_unix_time_ms(1499040000000),
            "2017-07-03T09:00:00",
        )

    def test_unsupported_currency_raises(self):
        with self.assertRaises(UserWarning):
            OkxDataProvider("USD", 60)

    def test_unsupported_interval_raises(self):
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 900)

    def test_interval_600_raises_because_okx_has_no_10m_bar(self):
        # OKX bar 목록에 10m이 없다 — 15m으로 조용히 바꾸지 않고 거부한다
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 600)

    @patch("requests.get")
    def test_get_info_should_call_get_with_correct_params(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [[
                "1499040000000", "0.01634790", "0.80000000", "0.01575800",
                "0.01577100", "148976.11427815", "2434.19055334",
                "2434.19055334", "1",
            ]],
        }
        OkxDataProvider("BTC", 60).get_info()
        self.assertEqual(
            mock_get.call_args_list[0][0][0],
            "https://www.okx.com/api/v5/market/candles",
        )
        self.assertEqual(
            mock_get.call_args_list[0][1]["params"],
            {"instId": "BTC-USDT", "bar": "1m", "limit": 1},
        )

        OkxDataProvider("ETH", 180).get_info()
        self.assertEqual(
            mock_get.call_args_list[1][1]["params"],
            {"instId": "ETH-USDT", "bar": "3m", "limit": 1},
        )

        OkxDataProvider("XRP", 300).get_info()
        self.assertEqual(
            mock_get.call_args_list[2][1]["params"],
            {"instId": "XRP-USDT", "bar": "5m", "limit": 1},
        )

    @patch("requests.get")
    def test_get_info_should_return_correct_data(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [[
                "1499040000000",     # ts
                "0.01634790",        # o
                "0.80000000",        # h
                "0.01575800",        # l
                "0.01577100",        # c
                "148976.11427815",   # vol   (base ccy)
                "2434.19055334",     # volCcy (quote ccy)
                "2434.19055334",     # volCcyQuote
                "1",                 # confirm
            ]],
        }
        expected = {
            "type": "primary_candle",
            "market": "BTC",
            "date_time": "2017-07-03T09:00:00",
            "opening_price": 0.0163479,
            "high_price": 0.8,
            "low_price": 0.015758,
            "closing_price": 0.015771,
            "acc_price": 2434.19055334,
            "acc_volume": 148976.11427815,
        }
        data = OkxDataProvider("BTC", 60).get_info()
        self.assertEqual(data[0], expected)

    @patch("requests.get")
    def test_error_envelope_raises_user_warning(self, mock_get):
        # OKX는 업무 오류도 HTTP 200으로 반환한다
        mock_get.return_value.json.return_value = {
            "code": "51001", "msg": "Instrument ID does not exist", "data": [],
        }
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 60).get_info()

    @patch("requests.get")
    def test_empty_data_raises_user_warning(self, mock_get):
        mock_get.return_value.json.return_value = {"code": "0", "msg": "", "data": []}
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 60).get_info()
