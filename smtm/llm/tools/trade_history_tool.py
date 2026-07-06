from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class TradeHistoryTool(Tool):
    """거래 내역 조회 Tool — SystemMonitor 거래 기록 조회"""
    name = "get_trade_history"
    description = "과거 거래 내역(매수/매도)을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "description": "조회할 최근 거래 수 (기본 20)", "default": 20},
            "session": {"type": "string",
                       "description": "세션 이름 (생략 시 전체 세션)"},
        },
    }

    def __init__(self, system_monitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor

    def execute(self, arguments: dict) -> ToolResult:
        try:
            count = arguments.get("count", 20)
            log = self.system_monitor.get_trade_log(session=arguments.get("session"))
            return ToolResult(success=True, data=log[-count:])
        except Exception as e:
            self.logger.error(f"TradeHistoryTool error: {e}")
            return ToolResult(success=False, error=str(e))
