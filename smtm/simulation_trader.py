"""시뮬레이션을 위한 가상 거래를 처리"""

from .log_manager import LogManager
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
        self.logger = LogManager.get_logger(__class__.__name__)
        self.market = VirtualMarket()
        self.is_initialized = False
        self.name = "Simulation"
        self.MARKET = "VirtualMarket"

    def initialize_simulation(self, end, count, budget):
        """시뮬레이션기간, 횟수, 예산을 초기화 한다"""
        self.market.initialize(end, count)
        self.market.deposit(budget)
        self.is_initialized = True

    def send_request(self, request, callback):
        """거래 요청을 처리한다"""

        if self.is_initialized is not True:
            raise UserWarning("Not initialzed")

        try:
            result = self.market.send_request(request)
            callback(result)
        except (TypeError, AttributeError) as msg:
            self.logger.error(f"invalid state {msg}")
            raise UserWarning("invalid state") from msg

    def get_account_info(self):
        """계좌 요청 정보를 요청한다
        현금을 포함한 모든 자산 정보를 제공한다

        returns:
        {
            balance: 계좌 현금 잔고
            asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
            quote: 종목별 현재 가격 딕셔너리
        }
        """

        if self.is_initialized is not True:
            raise UserWarning("Not initialzed")

        try:
            return self.market.get_balance()
        except (TypeError, AttributeError) as msg:
            self.logger.error(f"invalid state {msg}")
            raise UserWarning("invalid state") from msg

    def cancel_request(self, request_id):
        pass
