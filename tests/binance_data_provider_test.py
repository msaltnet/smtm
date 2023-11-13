import unittest
from smtm import BinanceDataProvider
from unittest.mock import *


class BinanceDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_kst_time_from_unix_time_ms_should_return_correct_string(self):
        self.assertEqual(
            BinanceDataProvider._get_kst_time_from_unix_time_ms(1622563200000),
            "2021-06-02T01:00:00",
        )
        self.assertEqual(
            BinanceDataProvider._get_kst_time_from_unix_time_ms(1698062700000),
            "2023-10-23T21:05:00",
        )
        self.assertEqual(
            BinanceDataProvider._get_kst_time_from_unix_time_ms(1499040000000),
            "2017-07-03T09:00:00",
        )

    @patch("requests.get")
    def test_get_info_should_call_get_with_correct_params(self, mock_get):
        data_provider = BinanceDataProvider("BTC", 60)
        data_provider.get_info()
        self.assertEqual(
            mock_get.call_args_list[0][0][0], "https://api.binance.com/api/v3/klines"
        )
        self.assertEqual(
            mock_get.call_args_list[0][1]["params"],
            {"symbol": "BTCUSDT", "limit": 1, "interval": "1m"},
        )

        data_provider = BinanceDataProvider("ETH", 180)
        data_provider.get_info()
        self.assertEqual(
            mock_get.call_args_list[1][0][0], "https://api.binance.com/api/v3/klines"
        )
        self.assertEqual(
            mock_get.call_args_list[1][1]["params"],
            {"symbol": "ETHUSDT", "limit": 1, "interval": "3m"},
        )

        data_provider = BinanceDataProvider("XRP", 600)
        data_provider.get_info()
        self.assertEqual(
            mock_get.call_args_list[2][0][0], "https://api.binance.com/api/v3/klines"
        )
        self.assertEqual(
            mock_get.call_args_list[2][1]["params"],
            {"symbol": "XRPUSDT", "limit": 1, "interval": "10m"},
        )

        with self.assertRaises(UserWarning):
            data_provider = BinanceDataProvider("USD", 600)

    @patch("requests.get")
    def test_get_info_should_return_correct_data(self, mock_get):
        mock_get.return_value.json.return_value = [
            [
                1499040000000,  # Kline open time
                "0.01634790",  # Open price
                "0.80000000",  # High price
                "0.01575800",  # Low price
                "0.01577100",  # Close price
                "148976.11427815",  # Volume
                1499644799999,  # Kline Close time
                "2434.19055334",  # Quote asset volume
                308,  # Number of trades
                "1756.87402397",  # Taker buy base asset volume
                "28.46694368",  # Taker buy quote asset volume
                "0",  # Unused field, ignore.
            ]
        ]
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
        data_provider = BinanceDataProvider("BTC", 60)
        data = data_provider.get_info()
        self.assertEqual(data[0], expected)
