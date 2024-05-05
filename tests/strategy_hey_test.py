import unittest
from smtm import StrategyHey
from unittest.mock import *


class StrategyHeyTests(unittest.TestCase):
    def test_initialize_update_initial_balance(self):
        sas = StrategyHey()
        self.assertEqual(sas.is_intialized, False)
        sas.initialize(50000, 50)
        self.assertEqual(sas.budget, 50000)
        self.assertEqual(sas.balance, 50000)
        self.assertEqual(sas.min_price, 50)
        self.assertEqual(sas.is_intialized, True)
        sas.initialize(100, 10)
        self.assertEqual(sas.budget, 50000)
        self.assertEqual(sas.balance, 50000)
        self.assertEqual(sas.min_price, 50)

    def test_update_trading_info_append_info_to_data(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        dummy_info = [
            {
                "type": "primary_candle",
                "market": "orange",
                "date_time": "2020-02-25T15:41:09",
                "closing_price": 500,
            }
        ]
        sas.update_trading_info(dummy_info)
        self.assertEqual(sas.data.pop(), dummy_info[0])

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sas = StrategyHey()
        sas.update_trading_info("mango")
        self.assertEqual(len(sas.data), 0)

    def test_update_result_append_result(self):
        sas = StrategyHey()
        sas.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.result[-1]["type"], "orange")
        self.assertEqual(sas.result[-1]["request"]["id"], "banana")
        self.assertEqual(sas.result[-1]["price"], "777000")
        self.assertEqual(sas.result[-1]["amount"], "0.0001234")
        self.assertEqual(sas.result[-1]["msg"], "melon")
        self.assertEqual(sas.result[-1]["balance"], 500)

    def test_update_result_remove_from_waiting_requests(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        sas.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.result[-1]["type"], "orange")
        self.assertEqual(sas.result[-1]["request"]["id"], "banana")
        self.assertEqual(sas.result[-1]["price"], "777000")
        self.assertEqual(sas.result[-1]["amount"], "0.0001234")
        self.assertEqual(sas.result[-1]["msg"], "melon")
        self.assertEqual(sas.result[-1]["balance"], 500)
        self.assertFalse("banana" in sas.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        sas.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "requested",
        }
        sas.update_result(dummy_result)
        self.assertEqual(len(sas.result), 0)
        self.assertTrue("banana" in sas.waiting_requests)

    def test_update_result_update_balance_and_asset_amount(self):
        sas = StrategyHey()
        sas.initialize(100000, 10)
        self.assertEqual(sas.balance, 100000)
        sas.asset_amount = 50

        dummy_result = {
            "type": "buy",
            "request": {"id": "orange"},
            "price": 1000,
            "amount": 5,
            "msg": "success",
            "balance": 100,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.balance, 94998)
        self.assertEqual(sas.asset_amount, 55)
        self.assertEqual(sas.result[-1]["type"], "buy")
        self.assertEqual(sas.result[-1]["request"]["id"], "orange")
        self.assertEqual(sas.result[-1]["price"], 1000)
        self.assertEqual(sas.result[-1]["amount"], 5)
        self.assertEqual(sas.result[-1]["msg"], "success")
        self.assertEqual(sas.result[-1]["balance"], 100)

        dummy_result = {
            "type": "sell",
            "request": {"id": "apple"},
            "price": 1000,
            "amount": 53,
            "msg": "success",
            "balance": 1000,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.balance, 147972)
        self.assertEqual(sas.asset_amount, 2)
        self.assertEqual(sas.result[-1]["type"], "sell")
        self.assertEqual(sas.result[-1]["request"]["id"], "apple")
        self.assertEqual(sas.result[-1]["price"], 1000)
        self.assertEqual(sas.result[-1]["amount"], 53)
        self.assertEqual(sas.result[-1]["msg"], "success")
        self.assertEqual(sas.result[-1]["balance"], 1000)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        sas = StrategyHey()
        sas.update_result("orange")
        self.assertEqual(len(sas.result), 0)

    def test_get_request_return_None(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        requests = sas.get_request()
        self.assertEqual(requests, None)
