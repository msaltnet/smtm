import unittest
from smtm import Trader
from unittest.mock import *
import requests

class TraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_request_return_trading_result_with_same_id_and_type(self):
        trader = Trader()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.request_id = "mango"
        dummy_request.type = "orange"
        result = trader.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "orange")
