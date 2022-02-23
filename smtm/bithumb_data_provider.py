"""빗썸 거래소의 실시간 거래 데이터를 제공하는 BithumbDataProvider 클래스"""

from datetime import datetime, timezone, timedelta
import requests
from .data_provider import DataProvider
from .log_manager import LogManager


class BithumbDataProvider(DataProvider):
    """
    빗썸 거래소의 실시간 거래 데이터를 제공하는 클래스

    빗썸의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://api.bithumb.com/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}
    https://api.bithumb.com/public/candlestick/BTC_KRW/1m
    https://apidocs.bithumb.com/docs/candlestick
    """

    KST = timezone(timedelta(hours=9))
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    AVAILABLE_CURRENCY = {"BTC": "BTC_KRW", "ETH": "ETH_KRW"}

    def __init__(self, currency="BTC"):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        self.url = (
            f"https://api.bithumb.com/public/candlestick/{self.AVAILABLE_CURRENCY[currency]}/1m"
        )
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
        data = self.__get_data_from_server()
        if data["status"] != "0000":
            raise UserWarning("Fail get data from sever")

        return self.__create_candle_info(data["data"][-1])

    def __create_candle_info(self, data):
        try:
            return {
                "market": self.market,
                "date_time": datetime.fromtimestamp(data[0] / 1000.0, tz=self.KST).strftime(
                    self.ISO_DATEFORMAT
                ),
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

    def __get_data_from_server(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.json()
        except ValueError as error:
            self.logger.error(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
