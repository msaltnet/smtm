import unittest
from unittest.mock import *
from smtm.llm.tools.performance_tool import PerformanceTool


class PerformanceToolTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.manager.get_performance.return_value = {
            "session": "default", "return_ratio": -0.1, "total_trades": 1,
        }
        self.tool = PerformanceTool(self.manager)

    def test_default_session_used_when_omitted(self):
        result = self.tool.execute({})
        self.manager.get_performance.assert_called_with("default")
        self.assertTrue(result.success)
        self.assertEqual(result.data["return_ratio"], -0.1)

    def test_explicit_session_routed(self):
        self.tool.execute({"session": "s2"})
        self.manager.get_performance.assert_called_with("s2")

    def test_unknown_session_returns_error(self):
        self.manager.get_performance.side_effect = ValueError("세션을 찾을 수 없습니다: x")
        result = self.tool.execute({"session": "x"})
        self.assertFalse(result.success)

    def test_execute_returns_error_on_exception(self):
        self.manager.get_performance.side_effect = Exception("boom")
        result = self.tool.execute({})
        self.assertFalse(result.success)
