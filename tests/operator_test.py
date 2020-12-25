import unittest
from smtm import Operator
from unittest.mock import *
import requests
import threading

class OperatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_keep_object_correctly(self):
        operator = Operator()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")

        operator.initialize("apple", "kiwi", dp_mock, "banana", "orange")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.threading, "kiwi")
        self.assertEqual(operator.dp, dp_mock)
        self.assertEqual(operator.strategy, "banana")
        self.assertEqual(operator.trader, "orange")

    def test_setup_set_interval_correctly(self):
        operator = Operator()
        operator.setup(10)

        self.assertEqual(operator.interval, 10)

        operator.setup(39)
        self.assertEqual(operator.interval, 39)

    def test_start_return_false_without_initialization(self):
        operator = Operator()
        self.assertEqual(operator.start(), False)

    def test_start_return_false_without_threading_dataProvider(self):
        operator = Operator()
        operator.initialize("apple", None, None, "banana", "orange")

        self.assertEqual(operator.start(), False)

    def test_start_should_call_get_info_and_set_timer_after_initialization(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)

        operator = Operator()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value="papaya")
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()
        operator.initialize("apple", threading_mock, dp_mock, strategy_mock, trader_mock)
        operator.setup(27)

        self.assertEqual(operator.start(), True)
        threading_mock.Timer.assert_called_once_with(27, ANY)
        timer_mock.start.assert_called_once()
        self.assertEqual(operator.start(), False)
        dp_mock.get_info.assert_called_once()

    def test_stop_should_cancel_timer_and_set_false_isRunning(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)

        operator = Operator()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value="papaya")
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()

        self.assertFalse(operator.is_timer_running)
        operator.initialize("apple", threading_mock, dp_mock, strategy_mock, trader_mock)
        operator.start()
        self.assertTrue(operator.is_timer_running)
        operator.stop()
        self.assertFalse(operator.is_timer_running)
        timer_mock.cancel.assert_called_once()

    # def test_real(self):
    #     operator = Operator()
    #     dp_mock = Mock()
    #     dp_mock.initialize = MagicMock(return_value="")
    #     dp_mock.get_info = lambda x : print("test")

    #     operator.initialize("apple", dp_mock, "banana", "orange")
    #     operator.setup(27)
    #     operator.start(threading)

    #     self.assertEqual(operator.start(threading), True)
