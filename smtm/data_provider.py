from abc import *

class DataProvider(metaclass=ABCMeta):
    """
    데이터 소스로부터 데이터를 수집해서 정보를 제공하는 클래스
    """

    @abstractmethod
    def get_info(self):
        """현재 거래 정보를 CandleInfo로 전달"""
        pass

    @abstractmethod
    def initialize(self, http):
        """현재 거래 정보를 CandleInfo로 전달"""
        pass