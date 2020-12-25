import unittest
from smtm import SimulationTrader
from unittest.mock import *
import requests

class SimulationTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_request_call_callback_with_result_of_market_handle_quest(self):
        trader = SimulationTrader()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "orange"
        callback = MagicMock()
        trader.market.handle_request = MagicMock(return_value="banana")
        trader.handle_request(dummy_request, callback)
        trader.market.handle_request.assert_called_once_with(dummy_request)
        callback.assert_called_once_with("banana")
    def test_initialize_initialize_virtual_market(self):
        trader = SimulationTrader()
        class DummyHttp():
            pass
        http = DummyHttp()
        trader.market.initialize = MagicMock()
        trader.market.deposit = MagicMock()
        trader.initialize(http, "mango", 500, 5000)
        trader.market.initialize.assert_called_once_with(http, "mango", 500)
        trader.market.deposit.assert_called_once_with(5000)