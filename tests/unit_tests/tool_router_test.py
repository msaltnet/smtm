import unittest
from unittest.mock import *
from smtm.llm.tool_router import ToolRouter
from smtm.llm.tool import Tool, ToolResult
from smtm.llm.llm_client import ToolCall
from smtm.llm.system_monitor import SystemMonitor


class DummyTool(Tool):
    name = "dummy_tool"
    description = "A dummy tool"
    input_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}

    def execute(self, arguments):
        return ToolResult(success=True, data={"x": arguments["x"]})


class ToolRouterTests(unittest.TestCase):
    def setUp(self):
        self.monitor = SystemMonitor()
        self.router = ToolRouter(self.monitor)

    def test_register_adds_tool(self):
        tool = DummyTool()
        self.router.register(tool)
        self.assertIn("dummy_tool", self.router.tools)

    def test_execute_calls_tool_and_returns_result(self):
        self.router.register(DummyTool())
        tool_call = ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 42})
        result = self.router.execute(tool_call)
        self.assertTrue(result.success)
        self.assertEqual(result.data["x"], 42)

    def test_execute_returns_error_for_unknown_tool(self):
        tool_call = ToolCall(id="tc_1", name="unknown", arguments={})
        result = self.router.execute(tool_call)
        self.assertFalse(result.success)
        self.assertIn("unknown", result.error)

    def test_execute_logs_to_system_monitor(self):
        self.router.register(DummyTool())
        tool_call = ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 1})
        self.router.execute(tool_call)
        self.assertEqual(len(self.monitor.tool_call_log), 1)

    def test_get_tool_schemas_returns_all_schemas(self):
        self.router.register(DummyTool())
        schemas = self.router.get_tool_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["name"], "dummy_tool")
