from .data_provider import DataProvider
from .news_data_provider import NewsDataProvider
from .news_sources import (
    CoinTelegraphNewsDataProvider,
    DecryptNewsDataProvider,
    CryptoSlateNewsDataProvider,
)


class MultiNewsDataProvider(DataProvider):
    """
    여러 뉴스 소스를 하나의 리스트로 합쳐 제공하는 집계형 DataProvider.

    Aggregates multiple NewsDataProvider instances and returns their
    items merged into a single typed list (all `type='news'`).

    - 기본 구성: CoinDesk + CoinTelegraph + Decrypt + CryptoSlate.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 개별 소스가 실패하면 해당 소스만 빈 리스트가 되고 나머지는 정상 반환된다.
    """

    NAME = "MULTI NEWS DP"
    CODE = "MNS"

    DEFAULT_PER_SOURCE_COUNT = 3

    def __init__(
        self,
        currency="BTC",
        interval=60,
        providers=None,
        per_source_count=None,
    ):
        self.market = currency
        self.interval = interval
        count = per_source_count or self.DEFAULT_PER_SOURCE_COUNT
        if providers is None:
            providers = [
                NewsDataProvider(currency=currency, interval=interval, count=count),
                CoinTelegraphNewsDataProvider(
                    currency=currency, interval=interval, count=count
                ),
                DecryptNewsDataProvider(
                    currency=currency, interval=interval, count=count
                ),
                CryptoSlateNewsDataProvider(
                    currency=currency, interval=interval, count=count
                ),
            ]
        self.providers = providers

    def get_info(self):
        results = []
        for provider in self.providers:
            items = provider.get_info() or []
            results.extend(items)
        return results
