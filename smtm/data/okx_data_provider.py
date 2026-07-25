from datetime import datetime, timezone, timedelta
from ..date_converter import DateConverter
from .base_data_provider import BaseDataProvider


class OkxDataProvider(BaseDataProvider):
    """
    OKX 거래소의 실시간 거래 데이터를 제공하는 클래스
    A class that provides real-time trading data from the OKX exchange.

    OKX의 public api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    Uses OKX's public API. No signup, authentication, or tokens required.

    https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks
    """

    URL = "https://www.okx.com/api/v5/market/candles"
    AVAILABLE_CURRENCY = {
        "BTC": "BTC-USDT",
        "ETH": "ETH-USDT",
        "DOGE": "DOGE-USDT",
        "XRP": "XRP-USDT",
    }
    #: OKX bar 값. 10m은 OKX에 존재하지 않으므로 600은 지원하지 않는다.
    AVAILABLE_INTERVAL = {60: "1m", 180: "3m", 300: "5m"}
    NAME = "OKX DP"
    CODE = "OKX"
    KST = timezone(timedelta(hours=9))

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")
        if interval not in self.AVAILABLE_INTERVAL:
            raise UserWarning(f"not supported interval: {interval}")

        super().__init__(logger_name="OkxDataProvider")
        self.market = currency
        self.interval = self.AVAILABLE_INTERVAL[interval]
        self._api_url = self.URL
        self._query_params = {
            "instId": self.AVAILABLE_CURRENCY[currency],
            "bar": self.interval,
            "limit": 1,
        }

    def get_info(self):
        """실시간 거래 정보 전달한다

        Returns: 거래 정보 딕셔너리
        {
            "market": 거래 시장 종류 BTC
            "date_time": 정보의 기준 시간
            "opening_price": 시작 거래 가격
            "high_price": 최고 거래 가격
            "low_price": 최저 거래 가격
            "closing_price": 마지막 거래 가격
            "acc_price": 단위 시간내 누적 거래 금액
            "acc_volume": 단위 시간내 누적 거래 양
        }
        """
        data = self._get_data_from_server()
        return [self._create_candle_info(self._unwrap_candles(data)[0])]

    def _unwrap_candles(self, data):
        """OKX 응답 봉투를 해제해 캔들 배열 리스트를 반환한다.

        OKX는 업무 오류도 HTTP 200으로 반환하므로 code를 직접 확인해야 한다.
        실패는 BaseDataProvider._get_data_from_server와 같은 UserWarning으로 올린다.
        """
        if not isinstance(data, dict) or str(data.get("code")) != "0":
            msg = data.get("msg") if isinstance(data, dict) else data
            self.logger.error(f"OKX error response: {msg}")
            raise UserWarning("Fail get data from sever")
        rows = data.get("data") or []
        if not rows:
            self.logger.error("OKX returned empty candle data")
            raise UserWarning("Fail get data from sever")
        return rows

    def _create_candle_info(self, data):
        """
        sample response:
        {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1597026383085",   // ts, 캔들 시작 시간 (unix ms)
                    "3.721",           // o, 시가
                    "3.743",           // h, 고가
                    "3.677",           // l, 저가
                    "3.708",           // c, 종가
                    "8422410",         // vol, 거래량 (base ccy)
                    "22698348.04",     // volCcy, 거래대금 (quote ccy)
                    "22698348.04",     // volCcyQuote, 현물에서는 volCcy와 동일
                    "1"                // confirm, 0=미완성 1=완성
                ]
            ]
        }
        캔들은 최신순(내림차순)으로 오지만 limit=1이므로 data[0]이 곧 최신 캔들이다.
        """
        try:
            return {
                "type": "primary_candle",
                "market": self.market,
                "date_time": self._get_kst_time_from_unix_time_ms(int(data[0])),
                "opening_price": float(data[1]),
                "high_price": float(data[2]),
                "low_price": float(data[3]),
                "closing_price": float(data[4]),
                "acc_price": float(data[6]),
                "acc_volume": float(data[5]),
            }
        except (IndexError, ValueError) as err:
            self.logger.warning(f"invalid data for candle info: {err}")
            return None

    @staticmethod
    def _get_kst_time_from_unix_time_ms(unix_time_ms):
        return DateConverter.to_iso_string(
            datetime.fromtimestamp(unix_time_ms / 1000, tz=OkxDataProvider.KST)
        )
