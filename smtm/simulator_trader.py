from .log_manager import LogManager
from .trading_result import TradingResult
from .trading_request import TradingRequest
from .trader import Trader
from .virtual_market import VirtualMarket

class SimulatorTrader(Trader):
    '''
    거래 요청 정보를 받아서 거래소에 요청 후 결과를 돌려준다

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    '''

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.market = VirtualMarket()

    def handle_request(self, request, callback):
        result = self.market.handle_request(request)
        callback(result)

    def initialize(self, http, end, count, budget):
        self.market.initialize(http, end, count)
        self.market.deposit(budget)