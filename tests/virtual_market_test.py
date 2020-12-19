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

    def test_handle_request_return_trading_result_with_same_id_and_type(self):
        trader = VirtualMarket()
        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "orange"
        result = trader.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "orange")
