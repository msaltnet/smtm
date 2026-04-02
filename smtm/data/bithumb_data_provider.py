from datetime import datetime, timezone, timedelta
from .base_data_provider import BaseDataProvider


class BithumbDataProvider(BaseDataProvider):
    """
    빗썸 거래소의 실시간 거래 데이터를 제공하는 클래스
    Classes that provide real-time trading data from the Bithumb exchange

    빗썸의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    Use Bithumb's OPEN API. No signup, authentication, or token required.

    https://api.bithumb.com/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}
    https://api.bithumb.com/public/candlestick/BTC_KRW/1m
    https://apidocs.bithumb.com/docs/candlestick
    """

    KST = timezone(timedelta(hours=9))
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    AVAILABLE_CURRENCY = {"BTC": "BTC_KRW", "ETH": "ETH_KRW"}
    NAME = "BITTHUMB DP"
    CODE = "BTH"

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        if interval != 60:
            raise UserWarning(f"not supported interval: {interval}")

        super().__init__(logger_name="BithumbDataProvider")
        self.url = f"https://api.bithumb.com/public/candlestick/{self.AVAILABLE_CURRENCY[currency]}/1m"
        self._api_url = self.url
        self._query_params = None
        self.market = currency

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
        if data["status"] != "0000":
            raise UserWarning("Fail get data from sever")

        return [self._create_candle_info(data["data"][-1])]

    def _create_candle_info(self, data):
        try:
            return {
                "type": "primary_candle",
                "market": self.market,
                "date_time": datetime.fromtimestamp(
                    data[0] / 1000.0, tz=self.KST
                ).strftime(self.ISO_DATEFORMAT),
                "opening_price": float(data[1]),
                "high_price": float(data[3]),
                "low_price": float(data[4]),
                "closing_price": float(data[2]),
                "acc_price": 0,  # not supported
                "acc_volume": float(data[5]),
            }
        except KeyError as err:
            self.logger.warning(f"invalid data for candle info: {err}")
            return None
