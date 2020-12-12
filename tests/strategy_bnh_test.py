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
        bnh.initialize(50000)
        self.assertEqual(bnh.budget, 50000)
        self.assertEqual(bnh.balance, 50000)
        self.assertEqual(bnh.isIntialized, True)
        bnh.initialize(100)
        self.assertEqual(bnh.budget, 50000)
        self.assertEqual(bnh.balance, 50000)
