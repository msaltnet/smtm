import os
import unittest
from smtm import BithumbTrader
from unittest.mock import *


class BithumbTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch.dict(os.environ, {"BITHUMB_API_ACCESS_KEY": "mango"})
    @patch.dict(os.environ, {"BITHUMB_API_SECRET_KEY": "orange"})
    @patch.dict(os.environ, {"BITHUMB_API_SERVER_URL": "apple"})
    def test_init_update_os_environ_value(self):
        trader = BithumbTrader()
        self.assertEqual(trader.ACCESS_KEY, "mango")
        self.assertEqual(trader.SECRET_KEY, "orange")
        self.assertEqual(trader.SERVER_URL, "apple")
