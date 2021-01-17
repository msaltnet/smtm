"""데이터를 기반으로 매매 결정을 생성하는 Strategy 추상클래스"""
from abc import ABCMeta, abstractmethod


class Strategy(metaclass=ABCMeta):
    """
    데이터를 받아서 매매 판단을 하고 결과를 받아서 다음 판단에 반영하는 전략 클래스
    """

    @abstractmethod
    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트"""

    @abstractmethod
    def update_result(self, result):
        """요청한 거래의 결과를 업데이트"""

    @abstractmethod
    def get_request(self):
        """전략에 따라 거래 요청 정보를 생성한다"""

    @abstractmethod
    def initialize(self, budget, min_price=100):
        """예산을 설정하고 초기화한다"""
