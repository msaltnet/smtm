import unittest
from unittest.mock import *
from smtm.llm.tools.market_data_tool import MarketDataTool


class MarketDataToolTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.session = MagicMock()
        self.session.operator.data_provider.get_info.return_value = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50000}
        ]
        self.manager.get_session.return_value = self.session
        self.tool = MarketDataTool(self.manager)

    def test_name_and_schema_are_set(self):
        self.assertEqual(self.tool.name, "get_market_data")
        self.assertIn("session", self.tool.input_schema["properties"])
        self.assertNotIn("currency", self.tool.input_schema["properties"])

    def test_default_session_used_when_omitted(self):
        result = self.tool.execute({})
        self.manager.get_session.assert_called_with("default")
        self.assertTrue(result.success)
        self.assertEqual(result.data[0]["closing_price"], 50000)

    def test_explicit_session_routed(self):
        self.tool.execute({"session": "s2"})
        self.manager.get_session.assert_called_with("s2")

    def test_unknown_session_returns_error(self):
        self.manager.get_session.side_effect = ValueError("세션을 찾을 수 없습니다: x")
        result = self.tool.execute({"session": "x"})
        self.assertFalse(result.success)

    def test_execute_returns_error_on_exception(self):
        self.session.operator.data_provider.get_info.side_effect = Exception("API error")
        result = self.tool.execute({})
        self.assertFalse(result.success)
        self.assertIn("API error", result.error)

    def test_get_schema_returns_valid_schema(self):
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "get_market_data")
        self.assertIn("description", schema)
