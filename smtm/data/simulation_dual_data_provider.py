import copy
from datetime import datetime, timedelta
from .data_provider import DataProvider
from .database import Database
from ..log_manager import LogManager
from .data_repository import DataRepository


class SimulationDualDataProvider(DataProvider):
    """
    Upbit, Binance 2개의 거래소로부터 과거 데이터를 수집해서 순차적으로 제공하는 클래스
    Upbit 데이터의 타입을 primary_candle로 설정, Binance 데이터를 binance로 설정
    어느 거래소의 데이터를 기준으로 거래할지는 DataProvider는 관여하지 않음

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
    NAME = "SIMULATION DUAL DP"
    CODE = "SID"

    def __init__(self, currency="BTC", interval=60):
        if (
            currency not in self.AVAILABLE_CURRENCY["upbit"]
            or currency not in self.AVAILABLE_CURRENCY["binance"]
        ):
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        database = Database("smtm.db")
        self.repo_upbit = DataRepository(
            interval=interval, source="upbit", database=database
        )
        self.repo_binance = DataRepository(
            interval=interval, source="binance", database=database
        )
        self.interval_min = interval / 60
        self.data_upbit = []
        self.data_binance = []
        self.index = 0
        self.currency = currency

    def initialize_simulation(self, end=None, count=100):
        """
        DataRepository를 통해서 데이터를 가져와서 초기화한다
        Initialize by retrieving data through DataRepository
        """

        self.index = 0
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        start_dt = end_dt - timedelta(minutes=count * self.interval_min)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        self.data_upbit = self.repo_upbit.get_data(
            start, end, market=self.AVAILABLE_CURRENCY["upbit"][self.currency]
        )
        self.data_binance = self.repo_binance.get_data(
            start, end, market=self.AVAILABLE_CURRENCY["binance"][self.currency]
        )

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

        if now >= len(self.data_upbit) or now >= len(self.data_binance):
            return None

        self.index = now + 1
        self.logger.info(f'[DATA] @ {self.data_upbit[now]["date_time"]}')
        self.data_upbit[now]["type"] = "primary_candle"
        self.data_binance[now]["type"] = "binance"
        return [
            copy.deepcopy(self.data_upbit[now]),
            copy.deepcopy(self.data_binance[now]),
        ]
