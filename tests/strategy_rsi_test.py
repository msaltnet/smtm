import unittest
from smtm import StrategyRsi
from unittest.mock import *


class StrategyRsiTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_update_initial_balance(self):
        sma = StrategyRsi()
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
        sma = StrategyRsi()
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.data.pop(), dummy_info)

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sma = StrategyRsi()
        sma.update_trading_info("mango")
        self.assertEqual(len(sma.data), 0)

    def test_update_result_append_result(self):
        sma = StrategyRsi()
        sma.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "orange")
        self.assertEqual(sma.result[-1]["request"]["id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "777000")
        self.assertEqual(sma.result[-1]["amount"], "0.0001234")
        self.assertEqual(sma.result[-1]["msg"], "melon")
        self.assertEqual(sma.result[-1]["balance"], 500)

    def test_update_result_remove_from_waiting_requests(self):
        sma = StrategyRsi()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "orange")
        self.assertEqual(sma.result[-1]["request"]["id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "777000")
        self.assertEqual(sma.result[-1]["amount"], "0.0001234")
        self.assertEqual(sma.result[-1]["msg"], "melon")
        self.assertEqual(sma.result[-1]["balance"], 500)
        self.assertFalse("banana" in sma.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        sma = StrategyRsi()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "requested",
        }
        sma.update_result(dummy_result)
        self.assertEqual(len(sma.result), 0)
        self.assertTrue("banana" in sma.waiting_requests)

    def test_update_result_update_balance_and_asset_amount(self):
        sma = StrategyRsi()
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
        sma = StrategyRsi()
        sma.update_result("orange")
        self.assertEqual(len(sma.result), 0)

    def test_get_request_return_None_when_not_yet_initialized(self):
        sma = StrategyRsi()
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_data_is_empty(self):
        sma = StrategyRsi()
        sma.initialize(100, 10)
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_correct_request_at_buy_position(self):
        sma = StrategyRsi()
        sma.initialize(10000, 100)
        dummy_info = {"closing_price": 20000000}
        sma.update_trading_info(dummy_info)
        sma.position = "buy"
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0004)
        self.assertEqual(requests[0]["type"], "buy")

    def test_get_request_return_correct_request_at_sell_position(self):
        sma = StrategyRsi()
        sma.initialize(10000, 100)
        dummy_info = {"closing_price": 12345678}
        sma.update_trading_info(dummy_info)
        sma.position = "sell"
        sma.asset_amount = 0.001
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 12345678)
        self.assertEqual(requests[0]["amount"], 0.001)
        self.assertEqual(requests[0]["type"], "sell")

    def test_get_request_return_request_with_cancel_requests(self):
        sma = StrategyRsi()
        sma.initialize(10000, 100)
        sma.waiting_requests["mango_id"] = {"request": {"id": "mango_id"}}
        sma.waiting_requests["orange_id"] = {"request": {"id": "orange_id"}}
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.position = "sell"
        sma.asset_amount = 60
        requests = sma.get_request()
        self.assertEqual(requests[0]["id"], "mango_id")
        self.assertEqual(requests[0]["type"], "cancel")
        self.assertEqual(requests[1]["id"], "orange_id")
        self.assertEqual(requests[1]["type"], "cancel")
        self.assertEqual(requests[2]["price"], 20000000)
        self.assertEqual(requests[2]["amount"], 60)
        self.assertEqual(requests[2]["type"], "sell")
