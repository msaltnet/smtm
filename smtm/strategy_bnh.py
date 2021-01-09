from .strategy import Strategy
from .trading_request import TradingRequest
from .log_manager import LogManager

class StrategyBuyAndHold(Strategy):
    """
    분할 매수 후 홀딩 하는 간단한 전략

    isInitialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    result: 거래 요청 결과 리스트
    request: 마지막 거래 요청
    budget: 시작 잔고
    balance: 현재 잔고
    min_price: 최소 주문 금액
    """

    def __init__(self):
        self.is_intialized = False
        self.data = []
        self.budget = 0
        self.balance = 0
        self.min_price = 0
        self.result = []
        self.request = None
        self.logger = LogManager.get_logger(__name__)

    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트"""
        if self.is_intialized == False:
            return
        self.data.append(info)

    def update_result(self, result):
        """요청한 거래의 결과를 업데이트"""
        if self.is_intialized == False:
            return

        try:
            self.balance = result.balance
            self.logger.info(f"[RESULT] id: {result.request_id} ================")
            self.logger.info(f"type: {result.type}, msg: {result.msg}")
            self.logger.info(f"price: {result.price}, amount: {result.amount}")
            self.logger.info(f'balance: {self.balance}')
            self.logger.info(f"================================================")
            self.result.append(result)
        except AttributeError as msg:
            self.logger.warning(msg)

    def get_request(self):
        """
        데이터 분석 결과에 따라 거래 요청 정보를 생성한다

        10번에 걸쳐 분할 매수 후 홀딩하는 전략
        마지막 종가로 처음 예산의 1/10에 해당하는 양 만큼 매수시도
        """
        if self.is_intialized == False:
            return

        try:
            last_data = self.data[-1]
            target_budget = self.budget / 10
            if last_data is None:
                return TradingRequest('buy', 0, 0)

            if self.min_price > target_budget:
                self.logger.info('target_budget is too small')
                return TradingRequest('buy', 0, 0)

            if target_budget > self.balance:
                self.logger.info('blance is too small')
                return TradingRequest('buy', 0, 0)

            target_amount = target_budget / last_data['closing_price']
            trading_request = TradingRequest('buy', last_data['closing_price'], target_amount)
            self.logger.info(f"[REQ] id: {trading_request.id} =====================")
            self.logger.info(f"type: {trading_request.type}")
            self.logger.info(f"price: {trading_request.price}, amount: {trading_request.amount}")
            self.logger.info(f"================================================")
            return trading_request
        except KeyError:
            self.logger.error('invalid data')
        except IndexError:
            self.logger.error('empty data')
        except AttributeError as msg:
            self.logger.error(msg)

    def initialize(self, budget, min_price=100):
        """
        예산과 최소 거래 가능 금액을 설정한다
        """
        if self.is_intialized:
            return

        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
