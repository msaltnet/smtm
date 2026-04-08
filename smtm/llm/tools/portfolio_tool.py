from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PortfolioTool(Tool):
    """포트폴리오 조회 Tool — Trader.get_account_info 래핑"""
    name = "get_portfolio"
    description = "현재 보유 자산, 현금 잔고, 종목별 시세를 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, trader):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.trader = trader

    def execute(self, arguments: dict) -> ToolResult:
        try:
            info = self.trader.get_account_info()
            return ToolResult(success=True, data=info)
        except Exception as e:
            self.logger.error(f"PortfolioTool error: {e}")
            return ToolResult(success=False, error=str(e))
