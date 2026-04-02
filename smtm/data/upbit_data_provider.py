from .base_data_provider import BaseDataProvider


class UpbitDataProvider(BaseDataProvider):
    """
    업비트 거래소의 실시간 거래 데이터를 제공하는 클래스
    Classes that provide real-time trading data from the Upbit exchange

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    Use Upbit's OPEN API. No signup, authentication, or token required.
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"
    AVAILABLE_CURRENCY = {
        "BTC": "KRW-BTC",
        "ETH": "KRW-ETH",
        "DOGE": "KRW-DOGE",
        "XRP": "KRW-XRP",
    }
    NAME = "UPBIT DP"
    CODE = "UPB"

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(logger_name="UpbitDataProvider")
        self.market = currency
        self.interval = interval
        if self.interval == 60:
            self.URL = "https://api.upbit.com/v1/candles/minutes/1"
        elif self.interval == 180:
            self.URL = "https://api.upbit.com/v1/candles/minutes/3"
        elif self.interval == 300:
            self.URL = "https://api.upbit.com/v1/candles/minutes/5"
        elif self.interval == 600:
            self.URL = "https://api.upbit.com/v1/candles/minutes/10"
        else:
            raise UserWarning(f"not supported interval: {interval}")
        self._api_url = self.URL
        self._query_params = {"market": self.AVAILABLE_CURRENCY[currency], "count": 1}

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
        return [self._create_candle_info(data[0])]

    def _create_candle_info(self, data):
        try:
            return {
                "type": "primary_candle",
                "market": self.market,
                "date_time": data["candle_date_time_kst"],
                "opening_price": float(data["opening_price"]),
                "high_price": float(data["high_price"]),
                "low_price": float(data["low_price"]),
                "closing_price": float(data["trade_price"]),
                "acc_price": float(data["candle_acc_trade_price"]),
                "acc_volume": float(data["candle_acc_trade_volume"]),
            }
        except KeyError as err:
            self.logger.warning(f"invalid data for candle info: {err}")
            return None
