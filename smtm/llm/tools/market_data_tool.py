from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class MarketDataTool(Tool):
    """시장 데이터 조회 Tool — DataProvider 래핑"""

    name = "get_market_data"
    description = (
        "현재 시장 정보를 조회합니다. 결과는 서로 다른 `type`을 가진 딕셔너리들의 리스트로 반환됩니다."
        " 주거래 캔들은 `type='primary_candle'`이며 시가·고가·저가·종가·거래량을 포함합니다."
        " 구성된 DataProvider에 따라 다음 타입들이 함께 포함될 수 있으니"
        " 각 항목의 `type`을 확인하여 해석하세요."
        " - `binance`: 보조 거래소 캔들"
        " - `price_snapshot`: 종합 가격/시총/24h거래량/변동률(예: coingecko)"
        " - `onchain_stats`: 온체인 네트워크 지표(해시레이트·난이도·블록수 등)"
        " - `mempool_fees`: BTC 네트워크 수수료 권장값(sat/vB)"
        " - `funding_rate`: 선물 펀딩비(양: 과열, 음: 공포 신호)"
        " - `open_interest`: 선물 누적 미결제약정(계약수·USD 환산액)"
        " - `long_short_ratio`: 선물 롱/숏 계정 비율(>1 롱 우세, <1 숏 우세)"
        " - `eth_gas`: 이더리움 가스 가격 권장값(safe/propose/fast, gwei)"
        " - `exchange_rate`: 기축통화(USD) 대비 환율"
        " - `macro_market`: 전통시장/매크로 지표(DXY·S&P500·VIX·Gold·US10Y·Nasdaq 등)"
        " - `crypto_global`: 전체 크립토 거시 지표(총시총·거래량·BTC/ETH/스테이블 도미넌스)"
        " - `sentiment_index`: 감정 지수(0~100)"
        " - `news`: 기사(title/summary/source/url/date_time)"
        " - `reddit`: 서브레딧 게시물(title/summary/source/url/author/date_time)"
        " - `hackernews`: HN 스토리(title/url/points/num_comments/date_time)"
        " - `notice`: 거래소 공지(title/body/url/date_time)"
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
