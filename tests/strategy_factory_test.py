import unittest
from smtm import StrategyFactory, StrategyBuyAndHold, StrategySma0, StrategyRsi, StrategySmaMl
from unittest.mock import *


class StrategyFactoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_return_None_when_called_with_invalid_code(self):
        strategy = StrategyFactory.create("")
        self.assertEqual(strategy, None)

    def test_create_return_correct_strategy(self):
        self.assertTrue(isinstance(StrategyFactory.create("BNH"), StrategyBuyAndHold))
        self.assertTrue(isinstance(StrategyFactory.create("SMA"), StrategySma0))
        self.assertTrue(isinstance(StrategyFactory.create("RSI"), StrategyRsi))
        self.assertTrue(isinstance(StrategyFactory.create("SML"), StrategySmaMl))

    def test_get_name_return_None_when_called_with_invalid_code(self):
        strategy = StrategyFactory.get_name("")
        self.assertEqual(strategy, None)

    def test_get_name_return_correct_strategy(self):
        self.assertTrue(StrategyFactory.get_name("BNH"), StrategyBuyAndHold.NAME)
        self.assertTrue(StrategyFactory.get_name("SMA"), StrategySma0.NAME)
        self.assertTrue(StrategyFactory.get_name("RSI"), StrategyRsi.NAME)
        self.assertTrue(StrategyFactory.get_name("SML"), StrategySmaMl.NAME)

    def test_get_all_strategy_info_return_correct_info(self):
        all = StrategyFactory.get_all_strategy_info()
        self.assertTrue(all[0]["name"], StrategyBuyAndHold.NAME)
        self.assertTrue(all[0]["code"], StrategyBuyAndHold.CODE)
        self.assertTrue(all[0]["class"], StrategyBuyAndHold)
        self.assertTrue(all[1]["name"], StrategySma0.NAME)
        self.assertTrue(all[1]["code"], StrategySma0.CODE)
        self.assertTrue(all[1]["class"], StrategySma0)
        self.assertTrue(all[2]["name"], StrategyRsi.NAME)
        self.assertTrue(all[2]["code"], StrategyRsi.CODE)
        self.assertTrue(all[2]["class"], StrategyRsi)
        self.assertTrue(all[3]["name"], StrategySmaMl.NAME)
        self.assertTrue(all[3]["code"], StrategySmaMl.CODE)
        self.assertTrue(all[3]["class"], StrategySmaMl)
