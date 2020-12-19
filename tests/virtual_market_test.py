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
        dummy_request.price = 2000
        dummy_request.amount = 10
        market.initialize_from_file("./tests/mango_data.json", None, None)
        self.assertEqual(market.data[0]['market'], "mango")

        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "orange")

    def test_handle_request_handle_buy_return_result_corresponding_next_data(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/mango_data.json", None, None)
        market.deposit(2000)

        market.data[0]["opening_price"] = 2000.00000000
        market.data[0]["high_price"] = 2100.00000000
        market.data[0]["low_price"] = 1900.00000000
        market.data[0]["trade_price"] = 2050.00000000

        market.data[1]["opening_price"] = 2000.00000000
        market.data[1]["high_price"] = 2100.00000000
        market.data[1]["low_price"] = 1900.00000000
        market.data[1]["trade_price"] = 2050.00000000

        market.data[2]["opening_price"] = 2000.00000000
        market.data[2]["high_price"] = 2100.00000000
        market.data[2]["low_price"] = 1900.00000000
        market.data[2]["trade_price"] = 2050.00000000

        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "buy"
        dummy_request.price = 2000
        dummy_request.amount = 0.1

        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 2000)
        self.assertEqual(result.amount, 0.1)
        self.assertEqual(result.msg, "success")

        dummy_request2 = DummyRequest()
        dummy_request2.id = "orange"
        dummy_request2.type = "buy"
        dummy_request2.price = 1800
        dummy_request2.amount = 0.1

        result = market.handle_request(dummy_request2)
        self.assertEqual(result.request_id, "orange")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 0)
        self.assertEqual(result.amount, 0)
        self.assertEqual(result.msg, "not matched")

    def test_handle_request_handle_buy_return_no_money_when_balance_is_NOT_enough(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/mango_data.json", None, None)
        market.deposit(200)

        market.data[0]["opening_price"] = 2000.00000000
        market.data[0]["high_price"] = 2100.00000000
        market.data[0]["low_price"] = 1900.00000000
        market.data[0]["trade_price"] = 2050.00000000

        market.data[1]["opening_price"] = 2000.00000000
        market.data[1]["high_price"] = 2100.00000000
        market.data[1]["low_price"] = 1900.00000000
        market.data[1]["trade_price"] = 2050.00000000

        market.data[2]["opening_price"] = 2000.00000000
        market.data[2]["high_price"] = 2100.00000000
        market.data[2]["low_price"] = 1900.00000000
        market.data[2]["trade_price"] = 2050.00000000

        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "buy"
        dummy_request.price = 2000
        dummy_request.amount = 0.1

        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 2000)
        self.assertEqual(result.amount, 0.1)
        self.assertEqual(result.msg, "success")

        dummy_request2 = DummyRequest()
        dummy_request2.id = "orange"
        dummy_request2.type = "buy"
        dummy_request2.price = 1800
        dummy_request2.amount = 0.1

        result = market.handle_request(dummy_request2)
        self.assertEqual(result.request_id, "orange")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 0)
        self.assertEqual(result.amount, 0)
        self.assertEqual(result.msg, "no money")

    def test_handle_request_handle_update_balance(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/mango_data.json", None, None)
        market.deposit(2000)
        self.assertEqual(market.balance, 2000)

        market.data[0]["opening_price"] = 2000.00000000
        market.data[0]["high_price"] = 2100.00000000
        market.data[0]["low_price"] = 1900.00000000
        market.data[0]["trade_price"] = 2050.00000000

        market.data[1]["opening_price"] = 2000.00000000
        market.data[1]["high_price"] = 2100.00000000
        market.data[1]["low_price"] = 1900.00000000
        market.data[1]["trade_price"] = 2050.00000000

        market.data[2]["opening_price"] = 2000.00000000
        market.data[2]["high_price"] = 2100.00000000
        market.data[2]["low_price"] = 1900.00000000
        market.data[2]["trade_price"] = 2050.00000000

        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "buy"
        dummy_request.price = 2000
        dummy_request.amount = 0.1

        result = market.handle_request(dummy_request)
        self.assertEqual(result.request_id, "mango")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 2000)
        self.assertEqual(result.amount, 0.1)
        self.assertEqual(result.msg, "success")
        self.assertEqual(market.balance, 1800)

        dummy_request2 = DummyRequest()
        dummy_request2.id = "orange"
        dummy_request2.type = "buy"
        dummy_request2.price = 1900
        dummy_request2.amount = 0.5

        result = market.handle_request(dummy_request2)
        self.assertEqual(result.request_id, "orange")
        self.assertEqual(result.type, "buy")
        self.assertEqual(result.price, 1900)
        self.assertEqual(result.amount, 0.5)
        self.assertEqual(result.msg, "success")
        self.assertEqual(market.balance, 850)

    def test_handle_request_return_error_result_when_turn_is_overed(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/mango_data.json", None, None)
        market.deposit(2000)

        class DummyRequest():
            pass
        dummy_request = DummyRequest()
        dummy_request.id = "mango"
        dummy_request.type = "buy"
        dummy_request.price = 2000
        dummy_request.amount = 0.1

        for i in market.data:
            result = market.handle_request(dummy_request)
            self.assertEqual(result.request_id, "mango")
            self.assertEqual(result.type, "buy")

        result = market.handle_request(dummy_request)
        self.assertEqual(result.price, -1)
        self.assertEqual(result.amount, -1)
        self.assertEqual(result.msg, "game-over")

    def test_deposit_update_balance_correctly(self):
        market = VirtualMarket()
        self.assertEqual(market.balance, 0)
        market.deposit(1000)
        self.assertEqual(market.balance, 1000)
        market.deposit(-500)
        self.assertEqual(market.balance, 500)
