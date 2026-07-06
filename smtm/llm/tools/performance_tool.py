from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PerformanceTool(Tool):
    """수익률 분석 Tool"""
    name = "get_performance"
    description = "현재까지의 수익률, 거래 통계, 성과 분석을 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, system_monitor, trader, initial_budget: float):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor
        self.trader = trader
        self.initial_budget = initial_budget

    def execute(self, arguments: dict) -> ToolResult:
        try:
            account = self.trader.get_account_info()
            trade_log = self.system_monitor.get_trade_log()

            total_value = account.get("balance", 0)
            for asset_key, asset_info in account.get("asset", {}).items():
                avg_price, amount = asset_info
                quote_price = account.get("quote", {}).get(asset_key, avg_price)
                total_value += quote_price * amount

            return_ratio = (total_value - self.initial_budget) / self.initial_budget if self.initial_budget > 0 else 0

            return ToolResult(success=True, data={
                "initial_budget": self.initial_budget,
                "total_value": total_value,
                "balance": account.get("balance", 0),
                "return_ratio": round(return_ratio, 4),
                "total_trades": len(trade_log),
                "asset": account.get("asset", {}),
                "quote": account.get("quote", {}),
            })
        except Exception as e:
            self.logger.error(f"PerformanceTool error: {e}")
            return ToolResult(success=False, error=str(e))
