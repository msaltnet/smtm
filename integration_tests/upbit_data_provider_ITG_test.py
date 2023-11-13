import time
import unittest
from smtm import UpbitDataProvider
from unittest.mock import *


class UpbitDataProviderIntegrationTests(unittest.TestCase):
    def test_ITG_get_info_return_correct_data(self):
        dp = UpbitDataProvider()
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
        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_BTC(self):
        dp = UpbitDataProvider("BTC")
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
        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_ETH(self):
        dp = UpbitDataProvider("ETH")
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
        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_DOGE(self):
        dp = UpbitDataProvider("DOGE")
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
        # avoid throttling
        time.sleep(0.5)

    def test_ITG_get_info_return_correct_data_when_currency_is_XRP(self):
        dp = UpbitDataProvider("XRP")
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
        # avoid throttling
        time.sleep(0.5)
