import unittest
from smtm import SimulatorOperator
from unittest.mock import *
import requests
import threading

class SimulatorOperatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize(self):
        operator = SimulatorOperator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")

        operator.initialize("apple", dpMock, "banana", "orange")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.dp, dpMock)
        self.assertEqual(operator.algorithm, "banana")
        self.assertEqual(operator.trader, "orange")

    def test_setup(self):
        operator = SimulatorOperator()
        operator.setup(10)

        self.assertEqual(operator.interval, 10)

        operator.setup(39)
        self.assertEqual(operator.interval, 39)

    def test_start_without_initialization(self):
        operator = SimulatorOperator()
        self.assertEqual(operator.start(threading), False)

    def test_start_after_initialization(self):
        threadingMock = Mock()
        threadingMock.Timer = MagicMock(return_value="TestTimer")

        operator = SimulatorOperator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")
        dpMock.get_info = MagicMock(return_value="mango")

        operator.initialize("apple", dpMock, "banana", "orange")
        operator.setup(27)
        operator.start(threadingMock)

        self.assertEqual(operator.start(threading), True)
        threadingMock.Timer.assert_called_once_with(27, operator.process)

    def test_process_without_initialization(self):
        operator = SimulatorOperator()
        self.assertEqual(operator.process(), False)

    def test_process_after_initialization(self):
        operator = SimulatorOperator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")
        dpMock.get_info = MagicMock(return_value="mango")

        operator.initialize("apple", dpMock, "banana", "orange")
        operator.process()
        dpMock.get_info.assert_called_once()
