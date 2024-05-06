import unittest
from smtm import BinanceDataProvider
from unittest.mock import *


class BinanceDataProviderIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_get_info_return_correct_data(self):
        dp = BinanceDataProvider()
        info = dp.get_info()[0]
        self.assertEqual(info["type"], "primary_candle")
        self.assertEqual("market" in info, True)
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)

    def test_ITG_get_info_return_correct_data_when_currency_is_BTC(self):
        dp = BinanceDataProvider("BTC")
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

    def test_ITG_get_info_return_correct_data_when_currency_is_ETH(self):
        dp = BinanceDataProvider("ETH")
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

    def test_ITG_get_info_return_correct_data_when_currency_is_DOGE(self):
        dp = BinanceDataProvider("DOGE")
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

    def test_ITG_get_info_return_correct_data_when_currency_is_XRP(self):
        dp = BinanceDataProvider("XRP")
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
