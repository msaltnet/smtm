from .data_provider import DataProvider
from .upbit_data_provider import UpbitDataProvider
from .multi_news_data_provider import MultiNewsDataProvider
from .reddit_data_provider import (
    CryptoCurrencyRedditDataProvider,
    BitcoinRedditDataProvider,
)
from .fear_greed_data_provider import FearGreedDataProvider
from .coingecko_data_provider import CoinGeckoDataProvider
from .blockchain_info_data_provider import BlockchainInfoDataProvider
from .mempool_fees_data_provider import MempoolFeesDataProvider
from .binance_funding_rate_data_provider import BinanceFundingRateDataProvider
from .upbit_notice_data_provider import UpbitNoticeDataProvider
from .exchange_rate_data_provider import ExchangeRateDataProvider
from .hackernews_data_provider import HackerNewsDataProvider


class UpbitFullContextDataProvider(DataProvider):
    """
    Upbit 캔들에 뉴스 · 소셜 · 감정 지수 · 가격 스냅샷 · 온체인 · 수수료 ·
    펀딩비 · 거래소 공지 · 환율 · HN 스토리까지 가능한 많은 공개 소스를
    한 번에 합쳐 제공하는 '풀 컨텍스트' 복합 DataProvider.

    A super-aggregator that bundles as many public data sources as
    practical into a single typed-list response. Good for research
    or experiments where you want the LLM to see everything; probably
    too heavy for tight-loop live trading.

    CODE="UFC"로 Factory에 등록돼 있어 `--exchange UFC`로 바로 쓸 수 있다.
    개별 소스가 실패해도 나머지 소스는 정상 반환한다.
    """

    NAME = "UPBIT FULL CONTEXT DP"
    CODE = "UFC"

    def __init__(self, currency="BTC", interval=60, providers=None):
        self.upbit_dp = UpbitDataProvider(currency, interval)
        if providers is None:
            providers = [
                CoinGeckoDataProvider(currency=currency, interval=interval),
                BlockchainInfoDataProvider(currency=currency, interval=interval),
                MempoolFeesDataProvider(currency=currency, interval=interval),
                BinanceFundingRateDataProvider(currency=currency, interval=interval),
                FearGreedDataProvider(currency=currency, interval=interval),
                ExchangeRateDataProvider(currency=currency, interval=interval),
                UpbitNoticeDataProvider(currency=currency, interval=interval),
                MultiNewsDataProvider(currency=currency, interval=interval),
                CryptoCurrencyRedditDataProvider(
                    currency=currency, interval=interval, count=3
                ),
                BitcoinRedditDataProvider(
                    currency=currency, interval=interval, count=3
                ),
                HackerNewsDataProvider(currency=currency, interval=interval, count=3),
            ]
        self.providers = providers

    def get_info(self):
        candle_info = self.upbit_dp.get_info() or []
        if candle_info:
            candle_info[0]["type"] = "primary_candle"
        extras = []
        for provider in self.providers:
            extras.extend(provider.get_info() or [])
        return [*candle_info, *extras]
