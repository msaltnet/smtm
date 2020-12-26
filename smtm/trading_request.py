import time

class TradingRequest():
    """
    거래 요청 정보를 담고 있는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    """

    def __init__(self, type=None, price=0, amount=0):
        self.__id = self.id = time.time()
        self.__type = self.type = type
        self.__price = self.price = price
        self.__amount = self.amount = amount
        self.__timestamp = time.time()

        if type is not None and price > 0 and amount > 0:
            self.__is_fixed = True
        else:
            self.__is_fixed = False

        self.__is_submitted = False
        pass

    def set_info(self, type=None, price=0, amount=0):
        """거래 유형, 가격, 수량을 설정한다"""
        if self.__is_fixed:
            return

        if self.__type is None and type is not None:
            self.__type = self.type = type
        if self.__price == 0 and price > 0:
            self.__price = self.price = price
        if self.__amount == 0 and amount > 0:
            self.__amount = self.amount = amount

        if self.type is not None and self.price > 0 and self.amount > 0:
            self.__is_fixed = True

    def is_stained(self):
        """정보가 중간에서 변경되었는지 확인한다"""
        return (self.__type != self.type or
                self.__price != self.price or
                self.__amount != self.amount or
                self.__id != self.id)

    def is_submitted(self):
        """이미 요청된 정보인지 확인한다"""
        return self.__is_submitted

    def set_state_submitted(self):
        """이미 요청된 정보라고 표기한다"""
        self.__is_submitted = True
