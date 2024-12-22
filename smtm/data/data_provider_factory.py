from .binance_data_provider import BinanceDataProvider
from .upbit_data_provider import UpbitDataProvider
from .bithumb_data_provider import BithumbDataProvider
from .upbit_binance_data_provider import UpbitBinanceDataProvider


class DataProviderFactory:
    """
    DataProvider 정보 조회 및 생성을 담당하는 Factory 클래스
    Factory class responsible for retrieving and creating DataProvider information
    """

    DataProvider_LIST = [
        BinanceDataProvider,
        UpbitDataProvider,
        BithumbDataProvider,
        UpbitBinanceDataProvider,
    ]

    @staticmethod
    def create(code, currency="BTC", interval=60):
        for data_provider in DataProviderFactory.DataProvider_LIST:
            if data_provider.CODE == code:
                return data_provider(currency=currency, interval=interval)
        return None

    @staticmethod
    def get_name(code):
        for data_provider in DataProviderFactory.DataProvider_LIST:
            if data_provider.CODE == code:
                return data_provider.NAME
        return None

    @staticmethod
    def get_all_strategy_info():
        all_data_provider = []
        for data_provider in DataProviderFactory.DataProvider_LIST:
            all_data_provider.append(
                {
                    "name": data_provider.NAME,
                    "code": data_provider.CODE,
                    "class": data_provider,
                }
            )
        return all_data_provider
