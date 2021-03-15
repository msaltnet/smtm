import os
import unittest
from smtm import UpbitTrader
from unittest.mock import *


class SimulationTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch.dict(os.environ, {"UPBIT_OPEN_API_ACCESS_KEY": "mango"})
    @patch.dict(os.environ, {"UPBIT_OPEN_API_SECRET_KEY": "orange"})
    @patch.dict(os.environ, {"UPBIT_OPEN_API_SERVER_URL": "apple"})
    def test_init_update_os_environ_value(self):
        trader = UpbitTrader()
        self.assertEqual(trader.ACCESS_KEY, "mango")
        self.assertEqual(trader.SECRET_KEY, "orange")
        self.assertEqual(trader.SERVER_URL, "apple")
