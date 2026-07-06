from .news_data_provider import NewsDataProvider


class CoinTelegraphNewsDataProvider(NewsDataProvider):
    """CoinTelegraph RSS 피드를 사용하는 뉴스 DataProvider."""

    NAME = "COINTELEGRAPH NEWS DP"
    CODE = "CTN"

    DEFAULT_URL = "https://cointelegraph.com/rss"
    DEFAULT_SOURCE = "cointelegraph"


class DecryptNewsDataProvider(NewsDataProvider):
    """Decrypt RSS 피드를 사용하는 뉴스 DataProvider."""

    NAME = "DECRYPT NEWS DP"
    CODE = "DCN"

    DEFAULT_URL = "https://decrypt.co/feed"
    DEFAULT_SOURCE = "decrypt"


class CryptoSlateNewsDataProvider(NewsDataProvider):
    """CryptoSlate RSS 피드를 사용하는 뉴스 DataProvider."""

    NAME = "CRYPTOSLATE NEWS DP"
    CODE = "CSN"

    DEFAULT_URL = "https://cryptoslate.com/feed/"
    DEFAULT_SOURCE = "cryptoslate"


class BitcoinMagazineNewsDataProvider(NewsDataProvider):
    """Bitcoin Magazine RSS 피드를 사용하는 뉴스 DataProvider."""

    NAME = "BITCOIN MAGAZINE NEWS DP"
    CODE = "BMN"

    DEFAULT_URL = "https://bitcoinmagazine.com/.rss/full/"
    DEFAULT_SOURCE = "bitcoinmagazine"


class TheBlockNewsDataProvider(NewsDataProvider):
    """The Block RSS 피드를 사용하는 뉴스 DataProvider (크립토·금융 교차 보도)."""

    NAME = "THE BLOCK NEWS DP"
    CODE = "TBN"

    DEFAULT_URL = "https://www.theblock.co/rss.xml"
    DEFAULT_SOURCE = "theblock"


class WSJMarketsNewsDataProvider(NewsDataProvider):
    """Wall Street Journal Markets RSS 피드를 사용하는 경제 뉴스 DataProvider."""

    NAME = "WSJ MARKETS NEWS DP"
    CODE = "WSJ"

    DEFAULT_URL = "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
    DEFAULT_SOURCE = "wsj_markets"


class MarketWatchNewsDataProvider(NewsDataProvider):
    """MarketWatch Top Stories RSS 피드를 사용하는 경제 뉴스 DataProvider."""

    NAME = "MARKETWATCH NEWS DP"
    CODE = "MWN"

    DEFAULT_URL = "http://feeds.marketwatch.com/marketwatch/topstories/"
    DEFAULT_SOURCE = "marketwatch"


class CNBCFinanceNewsDataProvider(NewsDataProvider):
    """CNBC Finance (Markets) RSS 피드를 사용하는 경제 뉴스 DataProvider."""

    NAME = "CNBC FINANCE NEWS DP"
    CODE = "CNB"

    DEFAULT_URL = "https://www.cnbc.com/id/10000664/device/rss/rss.html"
    DEFAULT_SOURCE = "cnbc_finance"
