"""시뮬레이션을 위한 DataProvider 구현체"""

import json
from .data_provider import DataProvider
from .log_manager import LogManager


class SimulationDataProvider(DataProvider):
    """
    거래소로부터 과거 데이터를 수집해서 순차적으로 제공하는 클래스

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """

    url = "https://api.upbit.com/v1/candles/minutes/1"
    query_string = {"market": "KRW-BTC"}

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.is_initialized = False
        self.end = "2020-01-19 20:00:00"
        self.http = None
        self.data = []
        self.count = 50
        self.index = 0

    def get_info(self):
        """순차적으로 거래 정보 전달한다"""
        now = self.index

        if now >= len(self.data):
            return None

        self.index = now + 1
        self.logger.info(f'[DATA] @ {self.data[now]["candle_date_time_utc"]}')
        return self.__create_candle_info(self.data[now])

    def __initialize(self, end=None, count=100):
        self.index = 0
        if end is not None:
            self.end = end
        if count is not None:
            self.count = count

    def initialize(self, http):
        """데이터를 가져와서 초기화한다"""
        self.initialize_from_server(http)

    def initialize_with_file(self, filepath, end=None, count=100):
        """파일로부터 데이터를 가져와서 초기화한다"""
        if self.is_initialized:
            return

        self.__initialize(end, count)
        self.__get_data_from_file(filepath)
        self.logger.info(
            f"data is updated from file # file: {filepath}, end: {end}, count: {count}"
        )

    def initialize_from_server(self, http, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""
        if self.is_initialized:
            return

        self.__initialize(end, count)
        self.http = http
        self.__get_data_from_server()
        self.logger.info(f"data is updated from server # end: {end}, count: {count}")

    def __get_data_from_file(self, filepath):
        try:
            with open(filepath, "r") as data_file:
                self.data = json.loads(data_file.read())
                self.is_initialized = True
        except FileNotFoundError:
            self.logger.error("Invalid filepath")
        except ValueError:
            self.logger.error("Invalid JSON data")

    def __create_candle_info(self, data):
        try:
            return {
                "market": data["market"],
                "date_time": data["candle_date_time_utc"],
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

    def __get_data_from_server(self):
        if self.http is None:
            return

        self.query_string["to"] = self.end
        self.query_string["count"] = self.count
        try:
            response = self.http.request("GET", self.url, params=self.query_string)
            response.raise_for_status()
            self.data = json.loads(response.text)
            self.data.reverse()
            self.is_initialized = True
        except ValueError:
            self.logger.error("Invalid data from server")
        except self.http.exceptions.HTTPError as msg:
            self.logger.error(msg)
        except self.http.exceptions.RequestException as msg:
            self.logger.error(msg)
