import time
import unittest
from smtm import UpbitBinanceDataProvider
from unittest.mock import *


class UpbitBinanceDataProviderIntegrationTests(unittest.TestCase):
    def test_ITG_get_info_return_correct_data(self):
        dp = UpbitBinanceDataProvider()
        upbit_info = dp.get_info()[0]
        self.assertEqual(upbit_info["type"], "primary_candle")
        self.assertEqual("market" in upbit_info, True)
        self.assertEqual("date_time" in upbit_info, True)
        self.assertEqual("opening_price" in upbit_info, True)
        self.assertEqual("high_price" in upbit_info, True)
        self.assertEqual("low_price" in upbit_info, True)
        self.assertEqual("closing_price" in upbit_info, True)
        self.assertEqual("acc_price" in upbit_info, True)
        self.assertEqual("acc_volume" in upbit_info, True)

        binance_info = dp.get_info()[1]
        self.assertEqual(binance_info["type"], "binance")
        self.assertEqual("market" in binance_info, True)
        self.assertEqual("date_time" in binance_info, True)
        self.assertEqual("opening_price" in binance_info, True)
        self.assertEqual("high_price" in binance_info, True)
        self.assertEqual("low_price" in binance_info, True)
        self.assertEqual("closing_price" in binance_info, True)
        self.assertEqual("acc_price" in binance_info, True)
        self.assertEqual("acc_volume" in binance_info, True)
        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_BTC(self):
        dp = UpbitBinanceDataProvider("BTC")
        info = dp.get_info()[0]
        self.assertEqual(info["type"], "primary_candle")
        self.assertEqual(info["market"], "BTC")
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)

        binance_info = dp.get_info()[1]
        self.assertEqual(binance_info["type"], "binance")
        self.assertEqual(binance_info["market"], "BTC")
        self.assertEqual("date_time" in binance_info, True)
        self.assertEqual("opening_price" in binance_info, True)
        self.assertEqual("high_price" in binance_info, True)
        self.assertEqual("low_price" in binance_info, True)
        self.assertEqual("closing_price" in binance_info, True)
        self.assertEqual("acc_price" in binance_info, True)
        self.assertEqual("acc_volume" in binance_info, True)

        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_ETH(self):
        dp = UpbitBinanceDataProvider("ETH")
        info = dp.get_info()[0]
        self.assertEqual(info["type"], "primary_candle")
        self.assertEqual(info["market"], "ETH")
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)

        binance_info = dp.get_info()[1]
        self.assertEqual(binance_info["type"], "binance")
        self.assertEqual(binance_info["market"], "ETH")
        self.assertEqual("date_time" in binance_info, True)
        self.assertEqual("opening_price" in binance_info, True)
        self.assertEqual("high_price" in binance_info, True)
        self.assertEqual("low_price" in binance_info, True)
        self.assertEqual("closing_price" in binance_info, True)
        self.assertEqual("acc_price" in binance_info, True)
        self.assertEqual("acc_volume" in binance_info, True)

        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_DOGE(self):
        dp = UpbitBinanceDataProvider("DOGE")
        info = dp.get_info()[0]
        self.assertEqual(info["type"], "primary_candle")
        self.assertEqual(info["market"], "DOGE")
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)

        binance_info = dp.get_info()[1]
        self.assertEqual(binance_info["type"], "binance")
        self.assertEqual(binance_info["market"], "DOGE")
        self.assertEqual("date_time" in binance_info, True)
        self.assertEqual("opening_price" in binance_info, True)
        self.assertEqual("high_price" in binance_info, True)
        self.assertEqual("low_price" in binance_info, True)
        self.assertEqual("closing_price" in binance_info, True)
        self.assertEqual("acc_price" in binance_info, True)
        self.assertEqual("acc_volume" in binance_info, True)

        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_XRP(self):
        dp = UpbitBinanceDataProvider("XRP")
        info = dp.get_info()[0]
        self.assertEqual(info["type"], "primary_candle")
        self.assertEqual(info["market"], "XRP")
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)

        binance_info = dp.get_info()[1]
        self.assertEqual(binance_info["type"], "binance")
        self.assertEqual(binance_info["market"], "XRP")
        self.assertEqual("date_time" in binance_info, True)
        self.assertEqual("opening_price" in binance_info, True)
        self.assertEqual("high_price" in binance_info, True)
        self.assertEqual("low_price" in binance_info, True)
        self.assertEqual("closing_price" in binance_info, True)
        self.assertEqual("acc_price" in binance_info, True)
        self.assertEqual("acc_volume" in binance_info, True)

        # avoid throttling
        time.sleep(0.5)
