import unittest
from smtm import StrategyFactory, StrategyBuyAndHold, StrategyRsi, StrategySma


class StrategyFactoryTests(unittest.TestCase):
    def test_create_returns_correct_strategy_for_each_code(self):
        self.assertIsInstance(StrategyFactory.create("BNH"), StrategyBuyAndHold)
        self.assertIsInstance(StrategyFactory.create("RSI"), StrategyRsi)
        self.assertIsInstance(StrategyFactory.create("SMA"), StrategySma)

    def test_create_returns_none_for_unknown_code(self):
        self.assertIsNone(StrategyFactory.create("NOPE"))

    def test_get_name_returns_name_or_none(self):
        self.assertEqual(StrategyFactory.get_name("BNH"), "Buy and Hold")
        self.assertIsNone(StrategyFactory.get_name("NOPE"))

    def test_get_all_strategy_info_contains_all_codes(self):
        codes = [info["code"] for info in StrategyFactory.get_all_strategy_info()]
        self.assertIn("BNH", codes)
        self.assertIn("RSI", codes)
        self.assertIn("SMA", codes)
