class TradingResult():
    '''
    거래 요청의 결과 정보를 담고 있는 클래스

    request_id: 요청 정보 id
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    '''

    def __init__(self, request_id, type, price, amount):
        self.request_id = request_id
        self.type = type
        self.price = price
        self.amount = amount
        pass
