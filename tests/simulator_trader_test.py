import unittest
from smtm import SimulatorTrader
from unittest.mock import *
import requests

class SimulatorTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_request_call_callback_with_trading_result_of_same_id_and_type(self):
        trader = SimulatorTrader()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "orange"
        def callback_func(result):
            self.assertEqual(result.request_id, "mango")
            self.assertEqual(result.type, "orange")
        result = trader.handle_request(dummy_request, callback_func)
