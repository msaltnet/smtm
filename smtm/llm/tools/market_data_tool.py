from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class MarketDataTool(Tool):
    """시장 데이터 조회 Tool — DataProvider 래핑"""

    name = "get_market_data"
    description = "현재 시장의 OHLCV 캔들 데이터를 조회합니다. 시가, 고가, 저가, 종가, 거래량을 포함합니다."
    input_schema = {
        "type": "object",
        "properties": {
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "조회할 암호화폐",
            },
        },
        "required": ["currency"],
    }

    def __init__(self, data_provider):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.data_provider = data_provider

    def execute(self, arguments: dict) -> ToolResult:
        try:
            data = self.data_provider.get_info()
            return ToolResult(success=True, data=data)
        except Exception as e:
            self.logger.error(f"MarketDataTool error: {e}")
            return ToolResult(success=False, error=str(e))
