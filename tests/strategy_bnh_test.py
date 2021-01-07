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
        class DummyResult():
            pass
        dummy_result = DummyResult()
        dummy_result.type = "orange"
        dummy_result.request_id = "banana"
        dummy_result.price = "apple"
        dummy_result.amount = "kiwi"
        dummy_result.msg = "melon"
        dummy_result.balance = 500

        bnh.update_result(dummy_result)
        self.assertEqual(bnh.result.pop(), dummy_result)

    def test_update_result_update_balance(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)
        self.assertEqual(bnh.balance, 100)
        class DummyResult():
            pass
        dummy_result = DummyResult()
        dummy_result.type = "buy"
        dummy_result.request_id = "orange"
        dummy_result.price = 10
        dummy_result.amount = 5
        dummy_result.msg = "melon"
        dummy_result.balance = 100
        bnh.update_result(dummy_result)
        self.assertEqual(bnh.balance, 100)
        self.assertEqual(bnh.result.pop(), dummy_result)

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
        bnh.update_trading_info("mango")
        request = bnh.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_turn_over_when_last_data_is_None(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 100)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.closing_price = 20000000
        bnh.update_trading_info(dummy_info)
        request = bnh.get_request()
        self.assertEqual(request.price, 20000000)
        self.assertEqual(request.amount, 100 / 20000000)
        self.assertEqual(request.type, 'buy')
        bnh.update_trading_info(None)
        print(bnh.data[-1])
        request = bnh.get_request()
        self.assertEqual(request.price, 0)
        self.assertEqual(request.amount, 0)

    def test_get_request_return_turn_over_when_target_budget_is_too_small(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 100)
        bnh.update_trading_info("banana")
        request = bnh.get_request()
        self.assertEqual(request.price, 0)
        self.assertEqual(request.amount, 0)

    def test_get_request_return_turn_over_when_balance_is_smaller_than_target_budget(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 10)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.closing_price = 20000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 10
        request = bnh.get_request()
        self.assertEqual(request.price, 0)
        self.assertEqual(request.amount, 0)

    def test_get_request_return_turn_over_when_balance_is_smaller_than_min_price(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(900, 10)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.closing_price = 20000
        bnh.update_trading_info(dummy_info)
        bnh.balance = 9.5
        request = bnh.get_request()
        self.assertEqual(request.price, 0)
        self.assertEqual(request.amount, 0)

    def test_get_request_return_correct_request(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 100)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.closing_price = 20000000
        bnh.update_trading_info(dummy_info)
        request = bnh.get_request()
        self.assertEqual(request.price, 20000000)
        self.assertEqual(request.amount, 100 / 20000000)
        self.assertEqual(request.type, 'buy')
