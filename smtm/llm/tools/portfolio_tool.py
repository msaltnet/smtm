from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PortfolioTool(Tool):
    """포트폴리오 조회 Tool — 세션 Trader.get_account_info 래핑"""
    name = "get_portfolio"
    description = "세션의 포트폴리오(잔고/자산/시세)를 조회합니다"
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
            session = self.session_manager.get_session(
                arguments.get("session") or "default")
            return ToolResult(success=True, data=session.trader.get_account_info())
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        except Exception as e:
            self.logger.error(f"PortfolioTool error: {e}")
            return ToolResult(success=False, error=str(e))
