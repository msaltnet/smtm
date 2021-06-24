import unittest
from smtm import UpbitDataProvider
from unittest.mock import *
import requests


class UpbitDataProviderIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_get_info_return_correct_data(self):
        dp = UpbitDataProvider()
        info = dp.get_info()
        self.assertEqual("market" in info, True)
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)
