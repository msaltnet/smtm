import unittest
from smtm import BithumbDataProvider
from unittest.mock import *
import requests


class BithumbDataProviderIntegrationTests(unittest.TestCase):
    def test_ITG_get_info_return_correct_data(self):
        dp = BithumbDataProvider()
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
