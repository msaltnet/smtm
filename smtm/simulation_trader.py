"""시뮬레이션을 위한 가상 거래를 처리해주는 SimulationTrader 클래스"""

from .log_manager import LogManager
from .trader import Trader
from .virtual_market import VirtualMarket


class SimulationTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy, cancel
    price: 거래 가격
    amount: 거래 수량
    """

    AVAILABLE_CURRENCY = {"BTC": "KRW-BTC", "ETH": "KRW-ETH", "DOGE": "KRW-DOGE", "XRP": "KRW-XRP"}
    NAME = "Simulation"

    def __init__(self, currency="BTC"):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")
        self.logger = LogManager.get_logger(__class__.__name__)
        self.market = VirtualMarket(market=self.AVAILABLE_CURRENCY[currency])
        self.is_initialized = False

    def initialize_simulation(self, end, count, budget):
        """시뮬레이션기간, 횟수, 예산을 초기화 한다"""
        self.market.initialize(end, count, budget)
        self.is_initialized = True

    def send_request(self, request_list, callback):
        """거래 요청을 처리한다

        요청 정보를 기반으로 거래를 요청하고, callback으로 체결 결과를 수신한다.
        request_list: 한 개 이상의 거래 요청 정보 리스트
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간
        }]
        callback(result):
        {
            "request": 요청 정보 전체
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "msg": 거래 결과 메세지 success, internal error
            "balance": 거래 후 계좌 현금 잔고
            "state": 거래 상태 requested, done
            "date_time": 거래 체결 시간, 시뮬레이션 모드에서는 request의 시간
        }
        """

        if self.is_initialized is not True:
            raise UserWarning("Not initialzed")

        try:
            result = self.market.handle_request(request_list[0])
            if result is not None:
                callback(result)
        except (TypeError, AttributeError) as msg:
            self.logger.error(f"invalid state {msg}")
            raise UserWarning("invalid state") from msg

    def get_account_info(self):
        """계좌 정보를 요청한다
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
        """거래 요청을 취소한다. 시뮬레이션에서는 미사용
        request_id: 취소하고자 하는 request의 id
        """

    def cancel_all_requests(self):
        """모든 거래 요청을 취소한다. 시뮬레이션에서는 미사용
        체결되지 않고 대기중인 모든 거래 요청을 취소한다
        """
