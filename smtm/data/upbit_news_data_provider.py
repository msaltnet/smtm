from .data_provider import DataProvider
from .upbit_data_provider import UpbitDataProvider
from .news_data_provider import NewsDataProvider


class UpbitNewsDataProvider(DataProvider):
    """
    Upbit 캔들과 공용 뉴스 피드를 함께 제공하는 복합 DataProvider.

    Combines Upbit primary_candle with a text-type news feed in a single
    get_info() response, demonstrating how heterogeneous data sources
    can coexist under the DataProvider contract.
    """

    NAME = "UPBIT NEWS DP"
    CODE = "UPN"

    def __init__(
        self,
        currency="BTC",
        interval=60,
        news_url=None,
        news_source=None,
        news_count=None,
    ):
        self.upbit_dp = UpbitDataProvider(currency, interval)
        self.news_dp = NewsDataProvider(
            currency=currency,
            interval=interval,
            url=news_url,
            source=news_source,
            count=news_count,
        )

    def get_info(self):
        """Upbit 캔들 + 뉴스 항목을 하나의 리스트로 합쳐 반환.

        Returns: [primary_candle 한 건, news 0~N건]
        """
        candle_info = self.upbit_dp.get_info() or []
        if candle_info:
            candle_info[0]["type"] = "primary_candle"
        news_info = self.news_dp.get_info() or []
        return [*candle_info, *news_info]
