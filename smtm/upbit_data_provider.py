"""업비트 거래소의 실시간 거래 데이터를 제공하는 DataProvider"""

import requests
from .data_provider import DataProvider
from .log_manager import LogManager


class UpbitDataProvider(DataProvider):
    """
    업비트 거래소의 실시간 거래 데이터를 제공하는 클래스

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"

    def __init__(self):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.query_string = {"market": "KRW-BTC", "count": 1}

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
        return self.__create_candle_info(data[0])

    def set_market(self, market="KRW-BTC"):
        """마켓을 설정한다"""
        self.query_string["market"] = market

    def __create_candle_info(self, data):
        try:
            return {
                "market": data["market"],
                "date_time": data["candle_date_time_kst"],
                "opening_price": float(data["opening_price"]),
                "high_price": float(data["high_price"]),
                "low_price": float(data["low_price"]),
                "closing_price": float(data["trade_price"]),
                "acc_price": float(data["candle_acc_trade_price"]),
                "acc_volume": float(data["candle_acc_trade_volume"]),
            }
        except KeyError:
            self.logger.warning("invalid data for candle info")
            return None

    def __get_data_from_server(self):
        try:
            response = requests.get(self.URL, params=self.query_string)
            response.raise_for_status()
            return response.json()
        except ValueError as error:
            self.logger.error("Invalid data from server")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
