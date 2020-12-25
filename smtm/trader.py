from abc import *

class Trader(metaclass=ABCMeta):
    """
    거래 요청 정보를 받아서 거래소에 요청 후 결과를 돌려준다
    """

    @abstractmethod
    def send_request(self, request, callback):
        """거래 요청 정보를 보낸다"""
        pass
