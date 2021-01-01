from . import DataProvider
from .candle_info import CandleInfo
from . import LogManager
import json

class SimulationDataProvider(DataProvider):
    """
    거래소로부터 과거 데이터를 수집해서 순차적으로 제공하는 클래스

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """
    url = "https://api.upbit.com/v1/candles/minutes/1"
    query_string = {"market":"KRW-BTC"}

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.is_initialized = False
        self.end = None #"2020-01-19 20:34:42"
        self.http = None
        self.data = []
        self.count = 0
        self.index = 0

    def get_info(self):
        """순차적으로 거래 정보 전달한다"""
        now = self.index
        self.index = now + 1
        if now >= len(self.data):
            return None

        self.logger.info(f'trading data at {self.data[now]["candle_date_time_utc"]}')
        return self.__create_candle_info(self.data[now])

    def __initialize(self, end=None, count=100):
        self.index = 0
        self.is_initialized = True
        self.end = end
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
        self.logger.info(f'data is updated from file # file: {filepath}, end: {end}, count: {count}')

    def initialize_from_server(self, http, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""
        if self.is_initialized:
            return

        self.__initialize(end, count)
        self.http = http
        self.__get_data_from_server()
        self.logger.info(f'data is updated from server # end: {end}, count: {count}')

    def __get_data_from_file(self, filepath):
        try :
            with open(filepath, 'r') as data_file:
                self.data = json.loads(data_file.read())
                self.is_initialized = True
        except FileNotFoundError as msg:
            self.logger.warning(msg)

    def __create_candle_info(self, data):
        candle = CandleInfo()
        try:
            candle.market = data["market"]
            candle.date_time = data["candle_date_time_utc"]
            candle.opening_price = data["opening_price"]
            candle.high_price = data["high_price"]
            candle.low_price = data["low_price"]
            candle.closing_price = data["trade_price"]
            candle.acc_price = data["candle_acc_trade_price"]
            candle.acc_volume = data["candle_acc_trade_volume"]
        except KeyError:
            self.logger.warning("invalid data for candle info")
            return None

        return candle

    def __get_data_from_server(self):
        if self.http is None or self.is_initialized != True:
            return False

        if self.end is not None :
            self.query_string["to"] = self.end
        else :
            self.query_string["to"] = "2020-11-11 00:00:00"

        if self.count is not None :
            self.query_string["count"] = self.count
        else :
            self.query_string["count"] = 100

        response = self.http.request("GET", self.url, params=self.query_string)
        self.data = json.loads(response.text)

# response info format
# {
#     "market":"KRW-BTC",
#     "candle_date_time_utc":"2020-02-25T06:41:00",
#     "candle_date_time_kst":"2020-02-25T15:41:00",
#     "opening_price":11436000.00000000,
#     "high_price":11443000.00000000,
#     "low_price":11428000.00000000,
#     "trade_price":11443000.00000000,
#     "timestamp":1582612901489,
#     "candle_acc_trade_price":17001839.06758000,
#     "candle_acc_trade_volume":1.48642105,
#     "unit":1
# }

# market
# 마켓명
# String

# candle_date_time_utc
# 캔들 기준 시각(UTC 기준)
# String

# candle_date_time_kst
# 캔들 기준 시각(KST 기준)
# String

# opening_price
# 시가
# Double

# high_price
# 고가
# Double

# low_price
# 저가
# Double

# trade_price
# 종가
# Double

# timestamp
# 해당 캔들에서 마지막 틱이 저장된 시각
# Long

# candle_acc_trade_price
# 누적 거래 금액
# Double

# candle_acc_trade_volume
# 누적 거래량
# Double

# unit
# 분 단위(유닛)
# Integer