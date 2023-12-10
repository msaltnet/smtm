import unittest
from smtm import UpbitBinanceDataProvider
from unittest.mock import *
import requests


class UpbitBinanceDataProviderTests(unittest.TestCase):
    def test_get_info_return_result_from_upbit_binance_data_provider(self):
        dp = UpbitBinanceDataProvider("BTC")
        dp.upbit_dp = MagicMock()
        dp.upbit_dp.get_info.return_value = [
            {
                "market": "BTC-KRW",
                "date_time": "2020-03-10T22:52:00",
                "opening_price": 9777000,
                "high_price": 9778000,
                "low_price": 9763000,
                "closing_price": 9778000,
                "acc_price": 11277224.71063000,
                "acc_volume": 1.15377852,
            }
        ]
        dp.binance_dp = MagicMock()
        dp.binance_dp.get_info.return_value = [
            {
                "market": "BTC-USDT",
                "date_time": "2020-03-10T22:52:00",
                "opening_price": 0.0163479,
                "high_price": 0.8,
                "low_price": 0.015758,
                "closing_price": 0.015771,
                "acc_price": 2434.19055334,
                "acc_volume": 148976.11427815,
            }
        ]

        info = dp.get_info()

        self.assertEqual(info[0]["type"], "primary_candle")
        self.assertEqual(info[0]["market"], "BTC-KRW")
        self.assertEqual(info[0]["date_time"], "2020-03-10T22:52:00")
        self.assertEqual(info[0]["opening_price"], 9777000)
        self.assertEqual(info[0]["high_price"], 9778000)
        self.assertEqual(info[0]["low_price"], 9763000)
        self.assertEqual(info[0]["closing_price"], 9778000)
        self.assertEqual(info[0]["acc_price"], 11277224.71063000)
        self.assertEqual(info[0]["acc_volume"], 1.15377852)

        self.assertEqual(info[1]["type"], "binance")
        self.assertEqual(info[1]["market"], "BTC-USDT")
        self.assertEqual(info[1]["date_time"], "2020-03-10T22:52:00")
        self.assertEqual(info[1]["opening_price"], 0.0163479)
        self.assertEqual(info[1]["high_price"], 0.8)
        self.assertEqual(info[1]["low_price"], 0.015758)
        self.assertEqual(info[1]["closing_price"], 0.015771)
        self.assertEqual(info[1]["acc_price"], 2434.19055334)
        self.assertEqual(info[1]["acc_volume"], 148976.11427815)
