import unittest
from smtm import StrategyBuyAndHold
from unittest.mock import *


class StrategyBuyAndHoldTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_update_initial_balance(self):
        bnh = StrategyBuyAndHold()
        self.assertEqual(bnh.is_intialized, False)
        bnh.initialize(50000, 50)
        self.assertEqual(bnh.budget, 50000)
        self.assertEqual(bnh.balance, 50000)
        self.assertEqual(bnh.min_price, 50)
        self.assertEqual(bnh.is_intialized, True)
        bnh.initialize(100, 10)
        self.assertEqual(bnh.budget, 50000)
        self.assertEqual(bnh.balance, 50000)
        self.assertEqual(bnh.min_price, 50)

    def test_update_trading_info_append_info_to_data(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)
        bnh.update_trading_info("mango")
        self.assertEqual(bnh.data.pop(), "mango")

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        bnh = StrategyBuyAndHold()
        bnh.update_trading_info("mango")
        self.assertEqual(len(bnh.data), 0)

    def test_update_result_append_result(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": 500,
            "amount": 0.001,
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.result[-1]["type"], "orange")
        self.assertEqual(bnh.result[-1]["request"]["id"], "banana")
        self.assertEqual(bnh.result[-1]["price"], 500)
        self.assertEqual(bnh.result[-1]["amount"], 0.001)
        self.assertEqual(bnh.result[-1]["msg"], "melon")
        self.assertEqual(bnh.result[-1]["balance"], 500)

    def test_update_result_update_balance_at_buy(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100000, 10)
        self.assertEqual(bnh.balance, 100000)

        dummy_result = {
            "type": "buy",
            "request": {"id": "orange"},
            "price": 10000,
            "amount": 5,
            "msg": "melon",
            "balance": 9500,
            "state": "done",
        }
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.balance, 49975)
        self.assertEqual(bnh.result[-1]["type"], "buy")
        self.assertEqual(bnh.result[-1]["request"]["id"], "orange")
        self.assertEqual(bnh.result[-1]["price"], 10000)
        self.assertEqual(bnh.result[-1]["amount"], 5)
        self.assertEqual(bnh.result[-1]["msg"], "melon")
        self.assertEqual(bnh.result[-1]["balance"], 9500)

    def test_update_result_update_balance_at_sell(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100000, 10)
        self.assertEqual(bnh.balance, 100000)

        dummy_result = {
            "type": "sell",
            "request": {"id": "orange"},
            "price": 10000,
            "amount": 5,
            "msg": "melon",
            "balance": 9500,
            "state": "done",
        }
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.balance, 149975)
        self.assertEqual(bnh.result[-1]["type"], "sell")
        self.assertEqual(bnh.result[-1]["request"]["id"], "orange")
        self.assertEqual(bnh.result[-1]["price"], 10000)
        self.assertEqual(bnh.result[-1]["amount"], 5)
        self.assertEqual(bnh.result[-1]["msg"], "melon")
        self.assertEqual(bnh.result[-1]["balance"], 9500)

    def test_update_result_remove_from_waiting_requests(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100000, 10)
        self.assertEqual(bnh.balance, 100000)
        bnh.waiting_requests["orange"] = "orage_request"

        dummy_result = {
            "type": "sell",
            "request": {"id": "orange"},
            "price": 10000,
            "amount": 5,
            "msg": "melon",
            "balance": 9500,
            "state": "done",
        }
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.balance, 149975)
        self.assertEqual(bnh.result[-1]["type"], "sell")
        self.assertEqual(bnh.result[-1]["request"]["id"], "orange")
        self.assertEqual(bnh.result[-1]["price"], 10000)
        self.assertEqual(bnh.result[-1]["amount"], 5)
        self.assertEqual(bnh.result[-1]["msg"], "melon")
        self.assertEqual(bnh.result[-1]["balance"], 9500)
        self.assertFalse("orange" in bnh.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100000, 10)
        self.assertEqual(bnh.balance, 100000)

        dummy_result = {
            "type": "sell",
            "request": {"id": "orange"},
            "price": 10000,
            "amount": 5,
            "msg": "melon",
            "balance": 9500,
            "state": "requested",
        }
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.balance, 100000)
        self.assertEqual(len(bnh.result), 0)
        self.assertTrue("orange" in bnh.waiting_requests)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        bnh = StrategyBuyAndHold()
        bnh.update_result("orange")
        self.assertEqual(len(bnh.result), 0)

    def test_get_request_return_None_when_not_yet_initialized(self):
        bnh = StrategyBuyAndHold()
        request = bnh.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_None_when_data_is_empty(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)
        request = bnh.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_None_when_data_is_invaild(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)
        dummy_info = {}
        bnh.update_trading_info(dummy_info)
        request = bnh.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_turn_over_when_last_data_is_None(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(50000, 100)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0005)
        self.assertEqual(requests[0]["type"], "buy")
        bnh.update_trading_info(None)
        requests = bnh.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_turn_over_when_target_budget_is_too_small_at_simulation(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 100)
        bnh.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)

    def test_get_request_use_balance_when_balance_is_smaller_than_target_budget(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 10)
        dummy_info = {}
        dummy_info["closing_price"] = 20000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 100
        requests = bnh.get_request()
        self.assertEqual(requests[0]["price"], 20000)
        self.assertEqual(requests[0]["amount"], 0.005)

    def test_get_request_return_None_when_balance_is_smaller_than_total_value(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(5000, 10)
        dummy_info = {}
        dummy_info["closing_price"] = 62000000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 10000
        requests = bnh.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_turn_over_when_balance_is_smaller_than_min_price_at_simulation(
        self,
    ):
        bnh = StrategyBuyAndHold()
        bnh.initialize(900, 10)
        bnh.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 9.5
        requests = bnh.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)

    def test_get_request_return_None_when_balance_is_smaller_than_min_price(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(900, 10)
        bnh.is_simulation = False
        dummy_info = {}
        dummy_info["closing_price"] = 20000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 9.5
        requests = bnh.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_correct_request(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(50000, 100)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0005)
        self.assertEqual(requests[0]["type"], "buy")

    def test_get_request_return_correct_request_with_cancel_requests(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(50000, 100)
        bnh.waiting_requests["mango_id"] = {"request": {"id": "mango_id"}}
        bnh.waiting_requests["orange_id"] = {"request": {"id": "orange_id"}}
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()

        self.assertEqual(requests[0]["id"], "mango_id")
        self.assertEqual(requests[0]["type"], "cancel")

        self.assertEqual(requests[1]["id"], "orange_id")
        self.assertEqual(requests[1]["type"], "cancel")

        self.assertEqual(requests[2]["price"], 20000000)
        self.assertEqual(requests[2]["amount"], 0.0005)
        self.assertEqual(requests[2]["type"], "buy")

    def test_get_request_return_same_datetime_at_simulation(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 100)
        bnh.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()
        self.assertEqual(requests[0]["date_time"], "2020-02-25T15:41:09")

        dummy_info["date_time"] = "2020-02-25T23:59:59"
        dummy_info["closing_price"] = 20000000
        bnh.update_trading_info(dummy_info)
        requests = bnh.get_request()
        self.assertEqual(requests[0]["date_time"], "2020-02-25T23:59:59")
