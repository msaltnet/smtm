from .log_manager import LogManager
from .trading_result import TradingResult
from .trading_request import TradingRequest
import json

class VirtualMarket():
    """
    거래 요청 정보를 받아서 처리하여 가상의 거래 결과 정보를 생성한다

    http: http client 모듈(requests)
    end: 거래기간의 끝
    count: 거래기간까지 가져올 데이터의 갯수
    data: 사용될 거래 정보 목록
    turn_count: 현재까지 진행된 턴수
    balance: 잔고
    commission_ratio: 수수료율
    asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
    """
    url = "https://api.upbit.com/v1/candles/minutes/1"
    query_string = {"market":"KRW-BTC", "count":"1"}

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.is_initialized = False
        self.http = None
        self.end = None
        self.count = None
        self.data = None
        self.turn_count = 0
        self.balance = 0
        self.commission_ratio = 0.0005
        self.asset = {}

    def initialize(self, http, end, count):
        """
        실제 거래소에서 거래 데이터를 가져와서 초기화한다

        http: http client 인스턴스
        end: 언제까지의 거래기간 정보를 사용할 것인지에 대한 날짜 시간 정보
        count: 거래기간까지 가져올 데이터의 갯수
        """
        if self.is_initialized == True:
            return

        self.http = http
        self.end = end
        self.count = count
        self.__update_data_from_server()

    def initialize_from_file(self, filepath, end, count):
        """
        파일로부터 거래 데이터를 가져와서 초기화한다

        filepath: 거래 데이터 파일
        end: 거래기간의 끝
        count: 거래기간까지 가져올 데이터의 갯수
        """
        if self.is_initialized == True:
            return

        self.end = end
        self.count = count
        try :
            with open(filepath, 'r') as data_file:
                self.data = json.loads(data_file.read())
                self.is_initialized = True
        except FileNotFoundError as msg:
            self.logger.error(msg)

    def __update_data_from_server(self):
        if self.end is not None:
            self.query_string["to"] = self.end
        else:
            self.query_string["to"] = "2020-11-11 00:00:00"

        if self.count is not None:
            self.query_string["count"] = self.count
        else:
            self.query_string["count"] = 100

        try:
            response = self.http.request("GET", self.url, params=self.query_string)
            response.raise_for_status()
            self.data = json.loads(response.text)
            self.data.reverse()
            self.is_initialized = True
        except AttributeError as msg:
            self.logger.error(msg)
        except ValueError:
            self.logger.error('Invalid data from server')
        except self.http.exceptions.HTTPError as err:
            self.logger.error(err)
        except self.http.exceptions.RequestException as err:
            self.logger.error(err)

    def deposit(self, balance):
        """자산 입출금을 할 수 있다"""
        self.balance += balance
        self.logger.info(f"Balance update {balance} to {self.balance}")

    def set_commission_ratio(self, ratio):
        """수수료 비율 설정한다"""
        self.commission_ratio = ratio / 100

    def get_balance(self):
        """
        현금을 포함한 모든 자산 정보를 제공한다

        balance: 계좌 현금 잔고
        asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
        quote: 종목별 현재 가격 딕셔너리
        """
        asset_info = {"balance": self.balance}
        quote = None
        try:
            quote = {self.data[self.turn_count]["market"]: self.data[self.turn_count]["opening_price"]}
            name = None
            self.logger.info(f'asset list length {len(self.asset)} =====================')
            for name, item in self.asset.items():
                self.logger.info(f'item: {name}, item price: {item[0]}, amount: {item[1]}')
        except (KeyError, IndexError) as msg:
            self.logger.error(f'invalid trading data {msg}')
            return

        asset_info['asset'] = self.asset
        asset_info['quote'] = quote
        return asset_info

    def send_request(self, request):
        """
        거래 요청을 처리해서 결과를 반환

        request: 거래 요청 정보
        """
        if self.is_initialized == False:
            self.logger.warning("virtual market is NOT initialized")
            return TradingResult(None, None, None, None)
        next_index = self.turn_count + 1
        result = None

        if next_index >= len(self.data)-1:
            self.turn_count = next_index
            return TradingResult(request.id, request.type, -1, -1, "game-over", self.balance)

        if request.price == 0 or request.amount == 0:
            self.turn_count = next_index
            return TradingResult(request.id, request.type, 0, 0, "turn over", self.balance)

        if request.type == 'buy':
            result = self.__handle_buy_request(request, next_index)
        elif request.type == 'sell':
            result = self.__handle_sell_request(request, next_index)
        else:
            result = TradingResult(request.id, request.type, -1, -1, "invalid type", self.balance)

        self.turn_count = next_index
        return result

    def __handle_buy_request(self, request, next_index):
        buy_asset_value = request.price * request.amount
        old_balance = self.balance
        if buy_asset_value * (1 + self.commission_ratio) > self.balance:
            return TradingResult(request.id, request.type, 0, 0, "no money", self.balance)

        try:
            if request.price < self.data[next_index]["low_price"]:
                return TradingResult(request.id, request.type, 0, 0, "not matched", self.balance)
            name = self.data[next_index]["market"]
            if name in self.asset:
                old = self.asset[name]
                final_amount = old[1] + request.amount
                total_value = (request.amount * request.price) + (old[0] * old[1])
                self.asset[name] = (round(total_value/final_amount), final_amount)
            else:
                self.asset[name] = (request.price, request.amount)

            self.balance -= buy_asset_value * (1 + self.commission_ratio)
            self.balance = round(self.balance)
            self.__print_balance_info("buy", old_balance, self.balance, buy_asset_value)
            return TradingResult(request.id, request.type, request.price, request.amount, "success", self.balance)
        except KeyError as msg:
            self.logger.error(f'invalid trading data {msg}')
            return TradingResult(request.id, request.type, -1, -1, "internal error", self.balance)

    def __handle_sell_request(self, request, next_index):
        asset_total_amount = 0
        old_balance = self.balance
        try:
            name = self.data[next_index]["market"]
            if name not in self.asset:
                return TradingResult(request.id, request.type, 0, 0, "asset empty", self.balance)

            if request.price >= self.data[next_index]["high_price"]:
                return TradingResult(request.id, request.type, 0, 0, "not matched", self.balance)

            sell_amount = request.amount
            if request.amount > self.asset[name][1]:
                sell_amount = self.asset[name][1]
                self.logger.warning(f'sell request is bigger than asset amount! {request.amount} -> {sell_amount}')
                del self.asset[name]
            else:
                self.asset[name] = (self.asset[name][0], self.asset[name][1] - sell_amount)

            sell_asset_value = sell_amount * request.price
            self.balance += sell_amount * request.price * (1 - self.commission_ratio)
            self.balance = round(self.balance)
            self.__print_balance_info("sell", old_balance, self.balance, sell_asset_value)
            return TradingResult(request.id, request.type, request.price, sell_amount, "success", self.balance)
        except KeyError as msg:
            self.logger.error(f'invalid trading data {msg}')
            return TradingResult(request.id, request.type, -1, -1, "internal error", self.balance)

    def __print_balance_info(self, type, old, new, total_asset_value):
        self.logger.debug(f"[Balance] from {old}")
        if type == "buy":
            self.logger.debug(f"[Balance] - {type}_asset_value {total_asset_value}")
        elif type == "sell":
            self.logger.debug(f"[Balance] + {type}_asset_value {total_asset_value}")
        self.logger.debug(f"[Balance] - commission {total_asset_value * self.commission_ratio}")
        self.logger.debug(f"[Balance] to {self.balance}")
