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
        self.assertEqual(bnh.isIntialized, False)
        bnh.initialize(50000, 50)
        self.assertEqual(bnh.budget, 50000)
        self.assertEqual(bnh.balance, 50000)
        self.assertEqual(bnh.min_price, 50)
        self.assertEqual(bnh.isIntialized, True)
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
        bnh.update_result("orange")
        self.assertEqual(bnh.result.pop(), "orange")

    def test_update_result_update_balance(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 10)
        self.assertEqual(bnh.balance, 100)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.type = "buy"
        dummy_info.price = 10
        dummy_info.amount = 5
        bnh.update_result(dummy_info)
        self.assertEqual(bnh.balance, 50)
        self.assertEqual(bnh.result.pop(), dummy_info)

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

    def test_get_request_return_None_when_target_budget_is_too_small(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(100, 100)
        bnh.update_trading_info("banana")
        request = bnh.get_request()
        self.assertEqual(request, None)

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

    def test_get_request_return_None_when_balance_is_too_small(self):
        bnh = StrategyBuyAndHold()
        bnh.initialize(1000, 100)
        class DummyInfo():
            pass
        dummy_info = DummyInfo()
        dummy_info.type = "buy"
        dummy_info.price = 900.00000000001
        dummy_info.amount = 1
        bnh.update_result(dummy_info)
        bnh.update_trading_info("banana")
        request = bnh.get_request()
        self.assertEqual(request, None)
