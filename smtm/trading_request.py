class TradingRequest():
    '''
    거래 요청 정보를 담고 있는 클래스

    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    '''

    def __init__(self, type=None, price=0, amount=0):
        self.__type = self.type = type
        self.__price = self.price = price
        self.__amount = self.amount = amount

        if type is not None and price > 0 and amount > 0:
            self.__is_fixed = True
        else:
            self.__is_fixed = False

        self.__is_submitted = False
        pass

    def set_info(self, type=None, price=0, amount=0):
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
        return (self.__type != self.type or
                self.__price != self.price or 
                self.__amount != self.amount)

    def is_submitted(self):
        return self.__is_submitted

    def set_state_submitted(self):
        self.__is_submitted = True