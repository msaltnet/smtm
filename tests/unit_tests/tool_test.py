import unittest
from smtm.llm.tool import Tool, ToolResult


class ToolResultTests(unittest.TestCase):
    def test_success_result_stores_data(self):
        result = ToolResult(success=True, data={"balance": 50000})
        self.assertTrue(result.success)
        self.assertEqual(result.data["balance"], 50000)
        self.assertIsNone(result.error)

    def test_failure_result_stores_error(self):
        result = ToolResult(success=False, data=None, error="거래 실패")
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error, "거래 실패")

    def test_to_dict_returns_data_on_success(self):
        result = ToolResult(success=True, data={"price": 50000})
        d = result.to_dict()
        self.assertEqual(d["price"], 50000)

    def test_to_dict_returns_error_on_failure(self):
        result = ToolResult(success=False, data=None, error="에러 발생")
        d = result.to_dict()
        self.assertEqual(d["error"], "에러 발생")

    def test_Tool_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Tool()
