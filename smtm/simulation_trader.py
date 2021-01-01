from .log_manager import LogManager
from .trading_result import TradingResult
from .trading_request import TradingRequest
from .trader import Trader
from .virtual_market import VirtualMarket

class SimulationTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    """

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.market = VirtualMarket()
        self.is_initialized = False

    def initialize(self, http, end, count, budget):
        try:
            self.market.initialize(http, end, count)
            self.market.deposit(budget)
            self.is_initialized = True
        except AttributeError:
            self.logger.error('initialize fail')

    def send_request(self, request, callback):
        """거래 요청을 처리한다"""

        if self.is_initialized != True:
            raise SystemError('Not initialzed')

        try:
            result = self.market.send_request(request)
            callback(result)
        except (TypeError, AttributeError):
            raise SystemError('Not initialzed')
