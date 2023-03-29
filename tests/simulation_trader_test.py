import unittest
from smtm import SimulationTrader
from unittest.mock import *


class SimulationTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_simulation_initialize_virtual_market(self):
        trader = SimulationTrader()
        trader.market.initialize = MagicMock()
        trader.market.deposit = MagicMock()

        trader.initialize_simulation("mango", 500, 5000)

        trader.market.initialize.assert_called_once_with("mango", 500, 5000)
        self.assertEqual(trader.is_initialized, True)

    def test_initialize_simulation_set_is_initialized_False_when_invalid_market(self):
        trader = SimulationTrader()
        trader.market = "make exception"
        with self.assertRaises(AttributeError):
            trader.initialize_simulation("mango", 500, 5000)

        self.assertEqual(trader.is_initialized, False)

    def test_send_request_call_callback_with_result_of_market_handle_quest(self):
        trader = SimulationTrader()
        trader.is_initialized = True

        dummy_requests = [{"id": "mango", "type": "orange", "price": 500, "amount": 10}]
        callback = MagicMock()
        trader.market.handle_request = MagicMock(return_value="banana")
        trader.send_request(dummy_requests, callback)
        trader.market.handle_request.assert_called_once_with(dummy_requests[0])
        callback.assert_called_once_with("banana")

    def test_send_request_call_raise_exception_UserWarning_when_is_initialized_False(self):
        trader = SimulationTrader()
        trader.is_initialized = False

        with self.assertRaises(UserWarning):
            trader.send_request(None, None)

    def test_send_request_call_raise_exception_UserWarning_when_market_is_invalid(self):
        trader = SimulationTrader()
        trader.is_initialized = True
        trader.market = "make exception"

        with self.assertRaises(UserWarning):
            trader.send_request(None, None)

    def test_send_request_call_raise_exception_UserWarning_when_callback_make_TypeError(self):
        trader = SimulationTrader()
        trader.is_initialized = True

        with self.assertRaises(UserWarning):
            trader.send_request(None, None)

    def test_get_account_info_call_callback_with_virtual_market_get_balance_result(self):
        trader = SimulationTrader()
        trader.is_initialized = True
        trader.market.get_balance = MagicMock(return_value="banana")
        self.assertEqual(trader.get_account_info(), "banana")
        trader.market.get_balance.assert_called_once()

    def test_get_account_info_call_raise_exception_UserWarning_when_is_initialized_False(
        self,
    ):
        trader = SimulationTrader()
        trader.is_initialized = False

        with self.assertRaises(UserWarning):
            trader.get_account_info()

    def test_get_account_info_call_raise_exception_UserWarning_when_market_is_invalid(
        self,
    ):
        trader = SimulationTrader()
        trader.is_initialized = True
        trader.market = "make exception"

        with self.assertRaises(UserWarning):
            trader.get_account_info()

    def test_get_account_info_call_raise_exception_UserWarning_when_callback_make_TypeError(
        self,
    ):
        trader = SimulationTrader()
        trader.is_initialized = True

        with self.assertRaises(UserWarning):
            trader.get_account_info()
