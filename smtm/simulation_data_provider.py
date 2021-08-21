"""시뮬레이션을 위한 DataProvider 구현체"""

from datetime import datetime, timedelta
from .data_provider import DataProvider
from .log_manager import LogManager
from .data_repository import DataRepository


class SimulationDataProvider(DataProvider):
    """
    거래소로부터 과거 데이터를 수집해서 순차적으로 제공하는 클래스

    업비트의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"

    def __init__(self):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.repo = DataRepository("smtm.db")
        self.data = []
        self.index = 0

    def initialize_simulation(self, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""

        self.index = 0
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        start_dt = end_dt - timedelta(minutes=count)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        self.data = self.repo.get_data(start, end, market="KRW-BTC")

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
        now = self.index

        if now >= len(self.data):
            return None

        self.index = now + 1
        self.logger.info(f'[DATA] @ {self.data[now]["date_time"]}')
        return self.data[now]
