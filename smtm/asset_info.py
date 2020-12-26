import time

class AssetInfo():
    """
    계좌 정보를 담고 있는 클래스

    balance: 계좌 현금 잔고
    asset_value: 현금 잔고를 제외한 자산 총액
    asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 수량)
    """
    def __init__(self, balance=0, asset_value=0, asset=None):
        self.balance = balance
        self.asset_value = asset_value
        self.asset = asset
        self.timestamp = time.time()
