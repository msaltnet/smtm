import os
import unittest
from smtm import VirtualMarket
from unittest.mock import *
import requests

class VirtualMarketTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_intialize_should_download_from_real_market(self):
        market = VirtualMarket()
        http = Mock()
        class DummyResponse():
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "test"}]'
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        http.request.assert_called_once_with("GET", market.url, params=market.querystring)

    def test_intialize_should_not_download_again_after_initialized(self):
        market = VirtualMarket()
        http = Mock()
        class DummyResponse():
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "test"}]'
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(None, None, None)
        market.initialize(http, None, None)
        market.initialize(http, None, None)
        http.request.assert_called_once_with("GET", market.url, params=market.querystring)

    def test_intialize_update_trading_data(self):
        market = VirtualMarket()
        http = Mock()
        class DummyResponse():
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "mango"}]'
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        self.assertEqual(market.data[0]['market'], "mango")

    def test_intialize_from_file_update_trading_data(self):
        market = VirtualMarket()
        market.initialize_from_file("banana_data", None, None)
        self.assertEqual(market.data, None)
        market.initialize_from_file("./tests/mango_data.json", None, None)
        self.assertEqual(market.data[0]['market'], "mango")

    def test_intialize_from_file_ignore_after_initialized(self):
        market = VirtualMarket()
        http = Mock()
        class DummyResponse():
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "banana"}]'
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        self.assertEqual(market.data[0]['market'], "banana")

        market.initialize_from_file("./tests/mango_data.json", None, None)
        self.assertEqual(market.data[0]['market'], "banana")

    def test_handle_request_return_emtpy_result_when_NOT_initialized(self):
        market = VirtualMarket()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "orange"
        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, None)
        self.assertEqual(result.type, None)
        self.assertEqual(result.price, None)
        self.assertEqual(result.amount, None)

    def test_handle_request_return_trading_result_with_same_id_and_type(self):
        market = VirtualMarket()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "orange"
        market.initialize_from_file("./tests/mango_data.json", None, None)
        self.assertEqual(market.data[0]['market'], "mango")

        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "orange")

    # def test_handle_request_return_result_corresponding_next_data(self):
    #     trader = VirtualMarket()
    #     class DummyRequest():
    #         pass
    #     dummy_request = DummyRequest()
    #     dummy_request.id = "mango"
    #     dummy_request.type = "orange"
    #     dummy_request.price = 2000
    #     dummy_request.amount = 150
    #     result = trader.handle_request(dummy_request)
    #     self.assertEqual(result.request_id, "mango")
    #     self.assertEqual(result.type, "orange")
