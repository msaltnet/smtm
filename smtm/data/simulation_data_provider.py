from datetime import datetime, timedelta
from ..config import Config
from .data_provider import DataProvider
from ..log_manager import LogManager
from .data_repository import DataRepository


class SimulationDataProvider(DataProvider):
    """시뮬레이션을 위한 DataProvider 구현체 SimulationDataProvider 클래스
    거래소로부터 과거 데이터를 수집해서 순차적으로 제공

    Implementation of DataProvider for simulation SimulationDataProvider class
    Collect past data from the exchange and provide it sequentially
    """

    AVAILABLE_CURRENCY = {
        "upbit": {
            "BTC": "KRW-BTC",
            "ETH": "KRW-ETH",
            "DOGE": "KRW-DOGE",
            "XRP": "KRW-XRP",
        },
        "binance": {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "DOGE": "DOGEUSDT",
            "XRP": "XRPUSDT",
        },
    }
    NAME = "SIMULATION DP"
    CODE = "SIM"

    def __init__(self, currency="BTC", interval=60):
        if Config.simulation_source not in self.AVAILABLE_CURRENCY.keys():
            raise UserWarning(f"not supported source: {Config.simulation_source}")
        if currency not in self.AVAILABLE_CURRENCY[Config.simulation_source]:
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        self.repo = DataRepository(
            "smtm.db", interval=interval, source=Config.simulation_source
        )
        self.interval_min = interval / 60
        self.data = []
        self.index = 0
        self.market = self.AVAILABLE_CURRENCY[Config.simulation_source][currency]

    def initialize_simulation(self, end=None, count=100):
        """
        DataRepository를 통해서 데이터를 가져와서 초기화한다
        Initialize by retrieving data through DataRepository
        """

        self.index = 0
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        start_dt = end_dt - timedelta(minutes=count * self.interval_min)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        self.data = self.repo.get_data(start, end, market=self.market)

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
        self.data[now]["type"] = "primary_candle"
        return [self.data[now]]
