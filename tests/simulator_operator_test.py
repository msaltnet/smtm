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
        operator.initialize("apple", "mango", "banana", "orange")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.dp, "mango")
        self.assertEqual(operator.algorithm, "banana")
        self.assertEqual(operator.trader, "orange")
