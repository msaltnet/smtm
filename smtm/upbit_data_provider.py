"""업비트 거래소의 실시간 거래 데이터를 제공하는 DataProvider"""

import json
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
        self.logger = LogManager.get_logger(__name__)
        self.query_string = {"market": "KRW-BTC", "count": 1}

    def get_info(self):
        """실시간 거래 정보 전달한다"""
        data = self._get_data_from_server()
        return self.__create_candle_info(data[0])

    def initialize(self, http):
        """데이터를 가져와서 초기화한다"""
        self.query_string = {"market": "KRW-BTC"}

    def _create_candle_info(self, data):
        try:
            return {
                "market": data["market"],
                "date_time": data["candle_date_time_kst"],
                "opening_price": data["opening_price"],
                "high_price": data["high_price"],
                "low_price": data["low_price"],
                "closing_price": data["trade_price"],
                "acc_price": data["candle_acc_trade_price"],
                "acc_volume": data["candle_acc_trade_volume"],
            }
        except KeyError:
            self.logger.warning("invalid data for candle info")
            return None

    def _get_data_from_server(self):
        try:
            response = requests.get(self.URL, params=self.query_string)
            response.raise_for_status()
            return response.json()
        except ValueError:
            self.logger.error("Invalid data from server")
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
