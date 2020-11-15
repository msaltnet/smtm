from abc import *

# 데이터 소스로부터 데이터를 수집해서 정보를 제공
class DataProvider(metaclass=ABCMeta):
    # 현재 거래 정보 전달
    @abstractmethod
    def get_info(self):
        pass

    # 초기화
    @abstractmethod
    def initialize(self, http):
        pass