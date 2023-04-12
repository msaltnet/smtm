import unittest
from smtm import StrategySmaMl
from unittest.mock import *


class StrategySmaMlTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_update_initial_balance(self):
        sma = StrategySmaMl()
        self.assertEqual(sma.is_intialized, False)
        sma.initialize(50000, 50)
        self.assertEqual(sma.budget, 50000)
        self.assertEqual(sma.balance, 50000)
        self.assertEqual(sma.min_price, 50)
        self.assertEqual(sma.is_intialized, True)
        sma.initialize(100, 10)
        self.assertEqual(sma.budget, 50000)
        self.assertEqual(sma.balance, 50000)
        self.assertEqual(sma.min_price, 50)

    def test_update_trading_info_append_info_to_data(self):
        sma = StrategySmaMl()
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.data.pop(), dummy_info)

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sma = StrategySmaMl()
        sma.update_trading_info("mango")
        self.assertEqual(len(sma.data), 0)

    def test_update_result_remove_from_waiting_requests(self):
        sma = StrategySmaMl()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "buy",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.01234567",
            "msg": "success",
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "buy")
        self.assertEqual(sma.result[-1]["request"]["id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "777000")
        self.assertEqual(sma.result[-1]["amount"], "0.01234567")
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertFalse("banana" in sma.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        sma = StrategySmaMl()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "buy",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "success",
            "balance": 500,
            "state": "requested",
        }
        sma.update_result(dummy_result)
        self.assertEqual(len(sma.result), 0)
        self.assertTrue("banana" in sma.waiting_requests)
        self.assertEqual(sma.asset_amount, 0)
        self.assertEqual(sma.balance, 100)

    def test_update_result_update_balance_and_asset_amount_correctly(self):
        sma = StrategySmaMl()
        sma.initialize(100000, 10)
        self.assertEqual(sma.balance, 100000)
        sma.asset_amount = 50

        dummy_result = {
            "type": "buy",
            "request": {"id": "orange"},
            "price": 1000,
            "amount": 5,
            "msg": "success",
            "balance": 100,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 94998)
        self.assertEqual(sma.asset_amount, 55)
        self.assertEqual(sma.result[-1]["type"], "buy")
        self.assertEqual(sma.result[-1]["request"]["id"], "orange")
        self.assertEqual(sma.result[-1]["price"], 1000)
        self.assertEqual(sma.result[-1]["amount"], 5)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 100)

        dummy_result = {
            "type": "sell",
            "request": {"id": "apple"},
            "price": 1000,
            "amount": 53,
            "msg": "success",
            "balance": 1000,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 147972)
        self.assertEqual(sma.asset_amount, 2)
        self.assertEqual(sma.result[-1]["type"], "sell")
        self.assertEqual(sma.result[-1]["request"]["id"], "apple")
        self.assertEqual(sma.result[-1]["price"], 1000)
        self.assertEqual(sma.result[-1]["amount"], 53)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 1000)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        sma = StrategySmaMl()
        sma.update_result("orange")
        self.assertEqual(len(sma.result), 0)

    def test_get_request_return_None_when_not_yet_initialized(self):
        sma = StrategySmaMl()
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_data_is_empty(self):
        sma = StrategySmaMl()
        sma.initialize(100, 10)
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_data_is_invaild(self):
        sma = StrategySmaMl()
        sma.initialize(100, 10)
        dummy_info = {}
        sma.update_trading_info(dummy_info)
        requests = sma.get_request()
        self.assertEqual(requests, None)
