from .log_manager import LogManager
from .trading_result import TradingResult
from .trading_request import TradingRequest
import json

class VirtualMarket():
    '''
    거래 요청 정보를 받아서 처리하여 가상의 거래 결과 정보를 생성한다

    id: 요청 정보 id "1607862457.560075" request_id로 저장됨
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    '''

    url = "https://api.upbit.com/v1/candles/minutes/1"
    querystring = {"market":"KRW-BTC", "count":"1"}

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.is_initialized = False
        self.http = None
        self.end = None
        self.count = None
        self.data = None

    def initialize(self, http, end, count):
        if self.is_initialized == True:
            return

        self.http = http
        self.end = end
        self.count = count
        self.__update_data()

    def initialize_from_file(self, filepath, end, count):
        if self.is_initialized == True:
            return

        self.end = end
        self.count = count
        try :
            with open(filepath, 'r') as data_file:
                self.data = json.loads(data_file.read())
                print(data_file.read())
                self.is_initialized = True
        except FileNotFoundError as msg:
            self.logger.warning(msg)

    def __update_data(self):
        if self.end is not None :
            self.querystring["to"] = self.end
        else :
            self.querystring["to"] = "2020-11-11 00:00:00"

        if self.count is not None :
            self.querystring["count"] = self.count
        else :
            self.querystring["count"] = 100

        try :
            response = self.http.request("GET", self.url, params=self.querystring)
            self.data = json.loads(response.text)
        except AttributeError as msg:
            self.logger.warning(msg)
            return

        self.is_initialized = True

    def handle_request(self, request):
        if self.is_initialized == False:
            return TradingResult(None, None, None, None)

        return TradingResult(request.id, request.type, None, None)