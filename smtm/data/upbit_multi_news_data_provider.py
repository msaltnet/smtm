from .data_provider import DataProvider
from .upbit_data_provider import UpbitDataProvider
from .multi_news_data_provider import MultiNewsDataProvider


class UpbitMultiNewsDataProvider(DataProvider):
    """
    Upbit 캔들 + 여러 뉴스 소스(CoinDesk, CoinTelegraph, Decrypt, CryptoSlate)를
    한 응답에 합쳐 제공하는 복합 DataProvider.

    CODE="UMN"으로 Factory에 등록돼 있어 `--exchange UMN`으로 바로 사용할 수 있다.
    """

    NAME = "UPBIT MULTI NEWS DP"
    CODE = "UMN"

    def __init__(
        self,
        currency="BTC",
        interval=60,
        news_providers=None,
        per_source_count=None,
    ):
        self.upbit_dp = UpbitDataProvider(currency, interval)
        self.news_dp = MultiNewsDataProvider(
            currency=currency,
            interval=interval,
            providers=news_providers,
            per_source_count=per_source_count,
        )

    def get_info(self):
        """Upbit 캔들 + 여러 소스의 뉴스 항목을 합쳐 반환.

        Returns: [primary_candle 한 건, news 0~N건]
        """
        candle_info = self.upbit_dp.get_info() or []
        if candle_info:
            candle_info[0]["type"] = "primary_candle"
        news_info = self.news_dp.get_info() or []
        return [*candle_info, *news_info]
