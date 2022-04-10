"""시뮬레이션을 위한 DataProvider 구현체"""

import copy
import requests
from .date_converter import DateConverter
from .data_provider import DataProvider
from .log_manager import LogManager


class SimulationDataProvider(DataProvider):
    """
    거래소로부터 과거 데이터를 수집해서 순차적으로 제공하는 클래스

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"
    QUERY_STRING = {"market": "KRW-BTC"}

    def __init__(self):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.is_initialized = False
        self.data = []
        self.index = 0

    def initialize_simulation(self, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""

        self.index = 0
        query_string = copy.deepcopy(self.QUERY_STRING)

        try:
            if end is not None:
                query_string["to"] = DateConverter.from_kst_to_utc_str(end) + "Z"
            query_string["count"] = count

            response = requests.get(self.URL, params=query_string)
            response.raise_for_status()
            self.data = response.json()
            self.data.reverse()
            self.is_initialized = True
            self.logger.info(f"data is updated from server # end: {end}, count: {count}")
        except ValueError as error:
            self.logger.error("Invalid data from server")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error

    def get_info(self):
        """순차적으로 거래 정보 전달한다

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
        now = self.index

        if now >= len(self.data):
            return None

        self.index = now + 1
        self.logger.info(f'[DATA] @ {self.data[now]["candle_date_time_kst"]}')
        return self.__create_candle_info(self.data[now])

    def __create_candle_info(self, data):
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

    def initialize_from_server(self, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다.
        initialize_simulation로 대체되었으니 initialize_simulation를 사용하세요"""
        self.initialize_simulation(end, count)
