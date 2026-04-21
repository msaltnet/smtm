from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class MarketDataTool(Tool):
    """시장 데이터 조회 Tool — DataProvider 래핑"""

    name = "get_market_data"
    description = (
        "현재 시장 정보를 조회합니다. 결과는 서로 다른 `type`을 가진 딕셔너리들의 리스트로 반환됩니다."
        " 주거래 캔들은 `type='primary_candle'`이며 시가·고가·저가·종가·거래량을 포함합니다."
        " 구성된 DataProvider에 따라 보조 거래소 캔들(`type='binance'` 등)이나"
        " 뉴스(`type='news'`, 필드: title/summary/source/url/date_time)처럼"
        " 텍스트형 데이터가 함께 포함될 수 있으니 각 항목의 `type`을 확인하여 해석하세요."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "조회할 암호화폐 (primary_candle 기준)",
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
