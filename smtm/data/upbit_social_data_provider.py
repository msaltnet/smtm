from .data_provider import DataProvider
from .upbit_data_provider import UpbitDataProvider
from .multi_news_data_provider import MultiNewsDataProvider
from .reddit_data_provider import (
    CryptoCurrencyRedditDataProvider,
    BitcoinRedditDataProvider,
)
from .fear_greed_data_provider import FearGreedDataProvider


class UpbitSocialDataProvider(DataProvider):
    """
    Upbit 캔들 + 다중 뉴스 + Reddit(CryptoCurrency, Bitcoin) + Fear & Greed
    지수를 한 번에 제공하는 복합 DataProvider.

    Provides a rich multi-modal snapshot: candle, news, social chatter,
    and sentiment index — all in a single typed list. Useful when the
    LLM should consider market psychology alongside price action.

    CODE="USC"로 Factory에 등록돼 있어 `--exchange USC`로 바로 사용할 수 있다.
    개별 소스가 실패해도 나머지는 정상 반환되도록 설계돼 있다.
    """

    NAME = "UPBIT SOCIAL DP"
    CODE = "USC"

    def __init__(self, currency="BTC", interval=60, providers=None):
        self.upbit_dp = UpbitDataProvider(currency, interval)
        if providers is None:
            providers = [
                MultiNewsDataProvider(currency=currency, interval=interval),
                CryptoCurrencyRedditDataProvider(
                    currency=currency, interval=interval, count=5
                ),
                BitcoinRedditDataProvider(
                    currency=currency, interval=interval, count=5
                ),
                FearGreedDataProvider(currency=currency, interval=interval),
            ]
        self.providers = providers

    def get_info(self):
        """Upbit 캔들 + 뉴스/소셜/감정 지수 항목을 합쳐 반환.

        Returns: [primary_candle 한 건, news/reddit/sentiment_index 0~N건]
        """
        candle_info = self.upbit_dp.get_info() or []
        if candle_info:
            candle_info[0]["type"] = "primary_candle"
        extras = []
        for provider in self.providers:
            extras.extend(provider.get_info() or [])
        return [*candle_info, *extras]
