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
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")

        operator.initialize("apple", "kiwi", dpMock, "banana", "orange")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.threading, "kiwi")
        self.assertEqual(operator.dp, dpMock)
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
        timerMock = Mock()
        threadingMock = Mock()
        threadingMock.Timer = MagicMock(return_value=timerMock)

        operator = Operator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")
        dpMock.get_info = MagicMock(return_value="mango")
        strategyMock = Mock()
        strategyMock.update_trading_info = MagicMock(return_value="orange")
        strategyMock.get_request = MagicMock(return_value="papaya")
        operator.initialize("apple", threadingMock, dpMock, strategyMock, "orange")
        operator.setup(27)

        self.assertEqual(operator.start(), True)
        threadingMock.Timer.assert_called_once_with(27, ANY)
        timerMock.start.assert_called_once()
        self.assertEqual(operator.start(), False)
        dpMock.get_info.assert_called_once()

    def test_stop_should_cancel_timer_and_set_false_isRunning(self):
        timerMock = Mock()
        threadingMock = Mock()
        threadingMock.Timer = MagicMock(return_value=timerMock)

        operator = Operator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")
        dpMock.get_info = MagicMock(return_value="mango")
        strategyMock = Mock()
        strategyMock.update_trading_info = MagicMock(return_value="orange")
        strategyMock.get_request = MagicMock(return_value="papaya")

        self.assertFalse(operator.isTimerRunning)
        operator.initialize("apple", threadingMock, dpMock, strategyMock, "orange")
        operator.start()
        self.assertTrue(operator.isTimerRunning)
        operator.stop()
        self.assertFalse(operator.isTimerRunning)
        timerMock.cancel.assert_called_once()

    # def test_real(self):
    #     operator = Operator()
    #     dpMock = Mock()
    #     dpMock.initialize = MagicMock(return_value="")
    #     dpMock.get_info = lambda x : print("test")

    #     operator.initialize("apple", dpMock, "banana", "orange")
    #     operator.setup(27)
    #     operator.start(threading)

    #     self.assertEqual(operator.start(threading), True)
