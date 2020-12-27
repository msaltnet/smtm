import time

class ScoreRecord():
    """
    특정 시점의 수익률 정보를 담고 있는 클래스

    balance: 계좌 현금 잔고
    asset_value: 현금 잔고를 제외한 추정 자산 총액
    cumulative_return: 기준 시점부터 누적 수익률
    asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
    timestamp: 기록이 생성된 시점
    """
    def __init__(self, balance=0, cumulative_return=0, asset=None):
        self.balance = balance
        self.cumulative_return = cumulative_return
        self.asset = asset
        self.timestamp = time.time()
