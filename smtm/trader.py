"""거래 요청을 거래소에 보내고, 결과를 받아서 리턴"""
from abc import ABCMeta, abstractmethod


class Trader(metaclass=ABCMeta):
    """
    거래 요청 정보를 받아서 거래소에 요청 후 결과를 돌려준다
    """

    @abstractmethod
    def send_request(self, request, callback):
        """거래 요청 정보를 보낸다"""

    @abstractmethod
    def send_account_info_request(self, callback):
        """계좌 요청 정보를 요청한다
        현금을 포함한 모든 자산 정보를 제공한다

        returns:
        {
            balance: 계좌 현금 잔고
            asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
            quote: 종목별 현재 가격 딕셔너리
        }
        """
