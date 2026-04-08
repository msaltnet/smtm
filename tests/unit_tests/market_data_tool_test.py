import unittest
from unittest.mock import *
from smtm.llm.tools.market_data_tool import MarketDataTool


class MarketDataToolTests(unittest.TestCase):
    def test_name_and_schema_are_set(self):
        tool = MarketDataTool(MagicMock())
        self.assertEqual(tool.name, "get_market_data")
        self.assertIn("currency", tool.input_schema["properties"])

    def test_execute_returns_data_from_data_provider(self):
        dp_mock = MagicMock()
        dp_mock.get_info.return_value = [{"type": "primary_candle", "market": "BTC", "closing_price": 50000}]
        tool = MarketDataTool(dp_mock)
        result = tool.execute({"currency": "BTC"})
        self.assertTrue(result.success)
        self.assertEqual(result.data[0]["closing_price"], 50000)

    def test_execute_returns_error_on_exception(self):
        dp_mock = MagicMock()
        dp_mock.get_info.side_effect = Exception("API error")
        tool = MarketDataTool(dp_mock)
        result = tool.execute({"currency": "BTC"})
        self.assertFalse(result.success)
        self.assertIn("API error", result.error)

    def test_get_schema_returns_valid_schema(self):
        tool = MarketDataTool(MagicMock())
        schema = tool.get_schema()
        self.assertEqual(schema["name"], "get_market_data")
        self.assertIn("description", schema)
