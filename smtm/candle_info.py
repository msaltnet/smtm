class CandleInfo():
    '''
    Candle로 표현되는 거래 정보를 담고 있는 클래스

    market: 거래 시장 종류 BTC
    date_time: 정보의 기준 시간
    opening_price: 시작 거래 가격
    high_price: 최고 거래 가격
    low_price: 최저 거래 가격
    closing_price: 마지막 거래 가격
    acc_price: 누적 거래 금액
    acc_volume: 누적 거래 양
    '''
    def __init__(self, market=None, date_time=None, 
                opening_price=0, high_price=0, low_price=0, 
                closing_price=0, acc_price=0, acc_volume=0):
        self.market = market
        self.date_time = date_time
        self.opening_price = opening_price
        self.high_price = high_price
        self.low_price = low_price
        self.closing_price = closing_price
        self.acc_price = acc_price
        self.acc_volume = acc_volume
