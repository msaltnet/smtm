from . import strategy

class StrategyBuyAndHold(Strategy):
    '''
    분할 매수 후 홀딩 하는 간단한 전략
    '''

    def update_trading_info(self):
        '''새로운 거래 정보를 업데이트'''
        pass

    def update_result(self):
        '''요청한 거래의 결과를 업데이트'''
        pass

    def get_request(self):
        '''거래 요청 정보를 가져온다'''
        pass

    def initialize(self, balance):
        pass