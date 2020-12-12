from abc import *

class Strategy(metaclass=ABCMeta):
    '''
    데이터를 받아서 매매 판단을 하고 결과를 받아서 다음 판단에 반영하는 전략 클래스
    '''

    @abstractmethod
    def update_trading_info(self):
        '''새로운 거래 정보를 업데이트'''
        pass

    @abstractmethod
    def update_result(self):
        '''요청한 거래의 결과를 업데이트'''
        pass

    @abstractmethod
    def get_request(self):
        '''거래 요청 정보를 가져온다'''
        pass

    @abstractmethod
    def initialize(self, balance):
        pass