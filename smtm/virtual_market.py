from .log_manager import LogManager
from .trading_result import TradingResult
from .trading_request import TradingRequest
from .asset_info import AssetInfo
import json

class VirtualMarket():
    """
    거래 요청 정보를 받아서 처리하여 가상의 거래 결과 정보를 생성한다

    http: http client 모듈(requests)
    end: 거래기간의 끝
    count: 거래기간까지 가져올 데이터의 갯수
    data: 사용될 거래 정보, CandleInfo 목록
    turn_count: 현재까지 진행된 턴수
    balance: 잔고
    commission_ratio: 수수료율
    asset: 자산 목록
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
        self.commission_ratio = 0.05
        self.asset = []

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
        self.__update_data()

    def deposit(self, balance):
        """자산 입출금을 할 수 있다"""
        self.balance += balance
        self.logger.info(f"Balance update {balance} to {self.balance}")

    def set_commission_ratio(self, ratio):
        """수수료 비율 설정한다"""
        self.commission_ratio = ratio

    def get_balance(self):
        """현금을 포함한 모든 자산 정보를 제공한다"""
        asset_info = AssetInfo(balance=self.balance)
        total_value = 0
        total_amount = 0
        avr_price = 0
        # 현재는 단일 마켓만 지원
        quote = {self.data[self.turn_count]["market"]: self.data[self.turn_count]["opening_price"]}
        asset = []
        name = None
        self.logger.info(f'asset list length {len(self.asset)} =====================')
        for item in self.asset:
            total_value += item["price"] * item["amount"]
            total_amount += item["amount"]
            self.logger.info(f'item price: {item["price"]}, amount: {item["amount"]} total_value: {total_value}')
            if name != None and item["name"] != name:
                self.logger.warning(f"multiple item name is NOT supported now. {name} : {item['name']}")
            name = item["name"]
            if total_value > 0 and total_amount > 0:
                avr_price = round(total_value / total_amount)

        self.logger.info(f"asset len: {len(self.asset)}, total amount: {total_amount}, avr price {avr_price}")

        if len(self.asset) > 0:
            asset.append((name, avr_price, total_amount))
        asset_info.asset = asset
        asset_info.quote = quote
        return asset_info

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
                print(data_file.read())
                self.is_initialized = True
        except FileNotFoundError as msg:
            self.logger.warning(msg)

    def __update_data(self):
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
            self.data = json.loads(response.text)
        except AttributeError as msg:
            self.logger.warning(msg)
            return

        self.is_initialized = True

    def send_request(self, request):
        """
        거래 요청을 처리해서 결과를 반환

        request: 거래 요청 정보
        """
        if self.is_initialized == False:
            self.logger.warning("virtual market is NOT initialized")
            return TradingResult(None, None, None, None)
        next = self.turn_count + 1
        result = None

        if next >= len(self.data):
            return TradingResult(request.id, request.type, -1, -1, "game-over", self.balance)

        if request.price == 0 or request.amount == 0:
            return TradingResult(request.id, request.type, 0, 0, "turn over", self.balance)

        if request.type == 'buy':
            result = self.__handle_buy_request(request, next)
        elif request.type == 'sell':
            result = self.__handle_sell_request(request, next)
        else:
            result = TradingResult(request.id, request.type, -1, -1, "invalid type", self.balance)

        self.turn_count = next
        return result

    def __handle_buy_request(self, request, next):
        buy_asset_value = request.price * request.amount

        if buy_asset_value * (1 + self.commission_ratio) > self.balance:
            return TradingResult(request.id, request.type, 0, 0, "no money", self.balance)

        if request.price >= self.data[next]["low_price"]:
            self.asset.append({"name": self.data[next]["market"], "price": request.price, "amount": request.amount})
            self.logger.warning(f"[balance] from {self.balance}")
            self.logger.warning(f"[balance] - buy_asset_value {buy_asset_value}")
            self.logger.warning(f"[balance] - commission {buy_asset_value * self.commission_ratio}")
            self.balance -= buy_asset_value * (1 + self.commission_ratio)
            self.logger.warning(f"[balance] to {self.balance}")
            self.balance = round(self.balance)
            return TradingResult(request.id, request.type, request.price, request.amount, "success", self.balance)

        return TradingResult(request.id, request.type, 0, 0, "not matched", self.balance)

    def __handle_sell_request(self, request, next):
        asset_total_amount = 0
        for item in self.asset:
            asset_total_amount += item["amount"]

        if request.price < self.data[next]["high_price"]:
            sell_amount = request.amount
            if request.amount > asset_total_amount:
                sell_amount = asset_total_amount
                self.logger.warning(f'sell request is bigger than asset amount! {request.amount} -> {sell_amount}')

            rest_amount = sell_amount
            new_asset = []
            self.logger.info(f'asset list len: {len(self.asset)} ==========')
            for item in self.asset:
                self.logger.info(f'item amount: {item["amount"]} - rest amount: {rest_amount}')
                if rest_amount == 0:
                    new_asset.append(item)
                elif item["amount"] > rest_amount:
                    item["amount"] -= rest_amount
                    rest_amount = 0
                    new_asset.append(item)
                else:
                    rest_amount -= item["amount"]

            self.asset = new_asset
            sell_asset_value = sell_amount * request.price
            self.logger.warning(f"[balance] from {self.balance}")
            self.logger.warning(f"[balance] + sell_asset_value {sell_asset_value}")
            self.logger.warning(f"[balance] - commission {sell_asset_value * self.commission_ratio}")
            self.balance += sell_amount * request.price * (1 - self.commission_ratio)
            self.logger.warning(f"[balance] to {self.balance}")
            self.balance = round(self.balance)
            return TradingResult(request.id, request.type, request.price, sell_amount, "success", self.balance)

        return TradingResult(request.id, request.type, 0, 0, "not matched", self.balance)
