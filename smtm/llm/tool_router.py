from typing import Dict
from ..log_manager import LogManager
from .tool import Tool, ToolResult
from .llm_client import ToolCall
from .system_monitor import SystemMonitor


class ToolRouter:
    """Tool 등록, 라우팅, 실행"""

    def __init__(self, system_monitor: SystemMonitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.tools: Dict[str, Tool] = {}
        self.system_monitor = system_monitor

    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        self.logger.info(f"Tool registered: {tool.name}")

    def get_tool_schemas(self) -> list:
        return [tool.get_schema() for tool in self.tools.values()]

    def execute(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.name not in self.tools:
            error = f"Tool not found: {tool_call.name}"
            self.logger.error(error)
            return ToolResult(success=False, error=error)

        tool = self.tools[tool_call.name]
        try:
            result = tool.execute(tool_call.arguments)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_call.name} - {e}")
            result = ToolResult(success=False, error=str(e))

        self.system_monitor.log_tool_call(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            result=result.to_dict(),
        )
        return result
