from datetime import datetime, timezone, timedelta
import requests
from ..date_converter import DateConverter
from .data_provider import DataProvider
from ..log_manager import LogManager


class BinanceDataProvider(DataProvider):
    """
    바이낸스 거래소의 실시간 거래 데이터를 제공하는 클래스
    A class that provides real-time trading data from the Binance exchange.

    바이낸스의 open api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    Uses Binance's OPEN API. No signup, authentication, or tokens required.

    https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
    """

    URL = "https://api.binance.com/api/v3/klines"
    AVAILABLE_CURRENCY = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "DOGE": "DOGEUSDT",
        "XRP": "XRPUSDT",
    }
    NAME = "BINANCE DP"
    CODE = "BNC"
    KST = timezone(timedelta(hours=9))

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        self.logger = LogManager.get_logger(__class__.__name__)
        self.market = currency
        if interval == 60:
            self.interval = "1m"
        elif interval == 180:
            self.interval = "3m"
        elif interval == 300:
            self.interval = "5m"
        elif interval == 600:
            self.interval = "10m"
        else:
            raise UserWarning(f"not supported interval: {interval}")
        self.query_string = {
            "symbol": self.AVAILABLE_CURRENCY[currency],
            "limit": 1,
            "interval": self.interval,
        }

    def get_info(self):
        """실시간 거래 정보 전달한다

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
        data = self._get_data_from_server()
        return [self._create_candle_info(data[0])]

    def _create_candle_info(self, data):
        """
        sample response:
        [
            [
                1499040000000,      // Kline open time
                "0.01634790",       // Open price
                "0.80000000",       // High price
                "0.01575800",       // Low price
                "0.01577100",       // Close price
                "148976.11427815",  // Volume, 거래수량
                1499644799999,      // Kline Close time
                "2434.19055334",    // Quote asset volume, 거래대금
                308,                // Number of trades
                "1756.87402397",    // Taker buy base asset volume
                "28.46694368",      // Taker buy quote asset volume
                "0"                 // Unused field, ignore.
            ]
        ]
        """
        try:
            return {
                "type": "primary_candle",
                "market": self.market,
                "date_time": self._get_kst_time_from_unix_time_ms(data[0]),
                "opening_price": float(data[1]),
                "high_price": float(data[2]),
                "low_price": float(data[3]),
                "closing_price": float(data[4]),
                "acc_price": float(data[7]),
                "acc_volume": float(data[5]),
            }
        except KeyError as err:
            self.logger.warning(f"invalid data for candle info: {err}")
            return None

    @staticmethod
    def _get_kst_time_from_unix_time_ms(unix_time_ms):
        return DateConverter.to_iso_string(
            datetime.fromtimestamp(unix_time_ms / 1000, tz=BinanceDataProvider.KST)
        )

    def _get_data_from_server(self):
        try:
            response = requests.get(self.URL, params=self.query_string)
            response.raise_for_status()
            return response.json()
        except ValueError as error:
            self.logger.error(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
