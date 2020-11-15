import unittest
from smtm import SimulatorOperator
from unittest.mock import *
import requests

class SimulatorOperatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_string(self):
        operator = SimulatorOperator()
        dpMock = Mock()
        dpMock.initialize = MagicMock(return_value="")

        operator.initialize("apple", dpMock, "banana", "orange")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.dp, dpMock)
        self.assertEqual(operator.algorithm, "banana")
        self.assertEqual(operator.trader, "orange")
