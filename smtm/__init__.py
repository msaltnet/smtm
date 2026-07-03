"""
Description for Package
"""

from .config import Config
from .worker import Worker
from .date_converter import DateConverter
from .log_manager import LogManager
from .data.upbit_data_provider import UpbitDataProvider
from .data.upbit_binance_data_provider import UpbitBinanceDataProvider
from .data.bithumb_data_provider import BithumbDataProvider
from .data.binance_data_provider import BinanceDataProvider
from .data.news_data_provider import NewsDataProvider
from .data.news_sources import (
    CoinTelegraphNewsDataProvider,
    DecryptNewsDataProvider,
    CryptoSlateNewsDataProvider,
    BitcoinMagazineNewsDataProvider,
    TheBlockNewsDataProvider,
    WSJMarketsNewsDataProvider,
    MarketWatchNewsDataProvider,
    CNBCFinanceNewsDataProvider,
)
from .data.multi_news_data_provider import MultiNewsDataProvider
from .data.reddit_data_provider import (
    RedditDataProvider,
    CryptoCurrencyRedditDataProvider,
    BitcoinRedditDataProvider,
)
from .data.fear_greed_data_provider import FearGreedDataProvider
from .data.coingecko_data_provider import CoinGeckoDataProvider
from .data.blockchain_info_data_provider import BlockchainInfoDataProvider
from .data.mempool_fees_data_provider import MempoolFeesDataProvider
from .data.binance_funding_rate_data_provider import BinanceFundingRateDataProvider
from .data.upbit_notice_data_provider import UpbitNoticeDataProvider
from .data.exchange_rate_data_provider import ExchangeRateDataProvider
from .data.hackernews_data_provider import HackerNewsDataProvider
from .data.yahoo_finance_data_provider import YahooFinanceDataProvider
from .data.crypto_global_data_provider import CryptoGlobalDataProvider
from .data.binance_open_interest_data_provider import BinanceOpenInterestDataProvider
from .data.binance_long_short_ratio_data_provider import BinanceLongShortRatioDataProvider
from .data.etherscan_gas_data_provider import EtherscanGasDataProvider
from .data.coincap_data_provider import CoinCapDataProvider
from .data.upbit_news_data_provider import UpbitNewsDataProvider
from .data.upbit_multi_news_data_provider import UpbitMultiNewsDataProvider
from .data.upbit_social_data_provider import UpbitSocialDataProvider
from .data.upbit_full_context_data_provider import UpbitFullContextDataProvider
from .data.data_provider_factory import DataProviderFactory
from .trader.upbit_trader import UpbitTrader
from .trader.bithumb_trader import BithumbTrader
from .trader.trader_factory import TraderFactory
from .controller.controller import Controller
from .controller.jpt_controller import JptController
from .controller.telegram import TelegramController
from .llm.llm_operator import LlmOperator
from .llm.llm_client import LlmClient
from .llm.claude_llm_client import ClaudeLlmClient
from .llm.safety_guard import SafetyGuard, SafetyConfig
from .llm.system_monitor import SystemMonitor
from .strategy.strategy import Strategy
from .strategy.strategy_bnh import StrategyBuyAndHold
from .strategy.strategy_rsi import StrategyRsi
from .strategy.strategy_sma import StrategySma

__all__ = [
    "LogManager",
    "LlmOperator",
    "Controller",
    "JptController",
    "TelegramController",
]

__version__ = "1.7.1"
