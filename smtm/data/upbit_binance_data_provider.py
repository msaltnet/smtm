from .data_provider import DataProvider
from .upbit_data_provider import UpbitDataProvider
from .binance_data_provider import BinanceDataProvider


class UpbitBinanceDataProvider(DataProvider):
    """
    Upbit, Binance 2개의 거래소로부터 실시간 데이터를 수집해서 제공하는 클래스
    Upbit 데이터의 타입을 primary_candle로 설정, Binance 데이터를 binance로 설정
    어느 거래소의 데이터를 기준으로 거래할지는 DataProvider는 관여하지 않음

    Collects real-time data from two exchanges, Upbit and Binance, and provides it
    Set the type of Upbit data to primary_candle and Binance data to binance
    DataProvider does not affect which exchange's data is used as the basis for trading
    """

    NAME = "UPBIT BINANCE DP"
    CODE = "UBD"

    def __init__(self, currency="BTC", interval=60):
        self.upbit_dp = UpbitDataProvider(currency, interval)
        self.binance_dp = BinanceDataProvider(currency, interval)

    def get_info(self):
        """순차적으로 거래 정보 전달한다

        Returns: 거래 정보 딕셔너리
        {
            "market": 거래 시장 종류 BTC
            "date_time": 정보의 기준 시간
            "opening_price": 시작 거래 가격
            "high_price": 최고 거래 가격
            "low_price": 최저 거래 가격
            "closing_price": 마지막 거래 가격
            "acc_price": 단위 시간내 누적 거래 금액
            "acc_volume": 단위 시간내 누적 거래 양
        }
        """
        upbit_info = self.upbit_dp.get_info()
        upbit_info[0]["type"] = "primary_candle"

        binance_info = self.binance_dp.get_info()
        binance_info[0]["type"] = "binance"
        return [upbit_info[0], binance_info[0]]
