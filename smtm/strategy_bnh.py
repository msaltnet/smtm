from .strategy import Strategy

class StrategyBuyAndHold(Strategy):
    '''
    분할 매수 후 홀딩 하는 간단한 전략

    isInitialized: 최초 잔고는 초기화 할 때만 갱신 된다
    data: 거래 데이터 리스트, OHLCV 데이터
    budget: 시작 잔고
    balance: 현재 잔고
    '''

    def __init__(self):
        self.isIntialized = False
        self.data = []
        self.budget = 0
        self.balance = 0

    def update_trading_info(self, info):
        '''새로운 거래 정보를 업데이트'''
        self.data.append(info)
        pass

    def update_result(self):
        '''요청한 거래의 결과를 업데이트'''
        pass

    def get_request(self):
        '''거래 요청 정보를 가져온다'''
        pass

    def initialize(self, budget):
        if self.isIntialized:
            return

        self.isIntialized = True
        self.budget = budget
        self.balance = budget
        pass