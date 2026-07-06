from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PerformanceTool(Tool):
    """수익률 분석 Tool — 세션의 성과 조회"""
    name = "get_performance"
    description = "세션의 수익률, 거래 통계, 성과 분석을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"session": {"type": "string",
                                   "description": "세션 이름 (기본 default)"}},
    }

    def __init__(self, session_manager):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        try:
            data = self.session_manager.get_performance(
                arguments.get("session") or "default")
            return ToolResult(success=True, data=data)
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        except Exception as e:
            self.logger.error(f"PerformanceTool error: {e}")
            return ToolResult(success=False, error=str(e))
