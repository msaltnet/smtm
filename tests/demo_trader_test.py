import unittest
from smtm import DemoTrader
from unittest.mock import *


class DemoTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_send_request_call_callback_correctly_when_buy(self):
        request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 500,
            "amount": 5,
            "date_time": "time",
        }
        callback_mock = MagicMock()
        trader = DemoTrader()
        trader.send_request([request], callback_mock)
        self.assertEqual(callback_mock.call_args[0][0]["state"], "done")
        self.assertEqual(callback_mock.call_args[0][0]["request"], request)
        self.assertEqual(callback_mock.call_args[0][0]["type"], "buy")
        self.assertEqual(callback_mock.call_args[0][0]["price"], 500)
        self.assertEqual(callback_mock.call_args[0][0]["amount"], 5)
        self.assertEqual(callback_mock.call_args[0][0]["msg"], "success")
        self.assertEqual(callback_mock.call_args[0][0]["date_time"], "time")

        request_sell = {
            "id": "1607862457.560075",
            "type": "sell",
            "price": 500,
            "amount": 5,
            "date_time": "time",
        }
        callback_mock_sell = MagicMock()
        trader.send_request([request_sell], callback_mock_sell)
        self.assertEqual(callback_mock_sell.call_args[0][0]["state"], "done")
        self.assertEqual(callback_mock_sell.call_args[0][0]["request"], request_sell)
        self.assertEqual(callback_mock_sell.call_args[0][0]["type"], "sell")
        self.assertEqual(callback_mock_sell.call_args[0][0]["price"], 500)
        self.assertEqual(callback_mock_sell.call_args[0][0]["amount"], 5)
        self.assertEqual(callback_mock_sell.call_args[0][0]["msg"], "success")
        self.assertEqual(callback_mock_sell.call_args[0][0]["date_time"], "time")

    def test_send_request_call_callback_with_error_at_invalid_sell(self):
        request = {
            "id": "1607862457.560075",
            "type": "sell",
            "price": 500,
            "amount": 5,
            "date_time": "time",
        }
        callback_mock = MagicMock()
        trader = DemoTrader()
        trader.send_request([request], callback_mock)
        callback_mock.assert_called_once_with("error!")

    def test_send_request_call_callback_with_error_at_invalid_buy(self):
        request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 5000000,
            "amount": 5,
            "date_time": "time",
        }
        callback_mock = MagicMock()
        trader = DemoTrader()
        trader.send_request([request], callback_mock)
        callback_mock.assert_called_once_with("error!")

    def test_get_account_info_return_correct_account_info(self):
        request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 500,
            "amount": 5,
            "date_time": "time",
        }
        callback_mock = MagicMock()
        trader = DemoTrader()

        trader.send_request([request], callback_mock)

        trader.get_trade_tick = MagicMock(return_value=[{"trade_price": 777}])
        info = trader.get_account_info()

        self.assertEqual(info["balance"], 47499)
        self.assertEqual(info["asset"], {"BTC": (500.0, 5.0)})
        self.assertEqual(info["quote"]["BTC"], 777)

        request_sell = {
            "id": "1607862457.560075",
            "type": "sell",
            "price": 503,
            "amount": 2.123,
            "date_time": "time",
        }
        trader.send_request([request_sell], callback_mock)

        trader.get_trade_tick = MagicMock(return_value=[{"trade_price": 751}])
        info = trader.get_account_info()

        self.assertEqual(info["balance"], 48566)
        self.assertEqual(info["asset"], {"BTC": (500.0, 2.877)})
        self.assertEqual(info["quote"]["BTC"], 751)

        request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 510,
            "amount": 5.321,
            "date_time": "time",
        }
        callback_mock = MagicMock()
        trader = DemoTrader()

        trader.send_request([request], callback_mock)

        trader.get_trade_tick = MagicMock(return_value=[{"trade_price": 701}])
        info = trader.get_account_info()

        self.assertEqual(info["balance"], 47285)
        self.assertEqual(info["asset"], {"BTC": (510.0, 5.321)})
        self.assertEqual(info["quote"]["BTC"], 701)
