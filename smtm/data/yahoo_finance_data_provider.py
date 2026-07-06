import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class YahooFinanceDataProvider(DataProvider):
    """
    Yahoo Finance의 공개 chart 엔드포인트를 사용해 매크로/전통시장 지표를
    type='macro_market' 딕셔너리 리스트로 반환하는 DataProvider.

    Fetches latest regular-market prices for macro/equity indicators that
    commonly move with crypto (DXY, S&P 500, VIX, Gold, US 10Y yield, Nasdaq)
    and normalizes each one into a `type='macro_market'` dict.

    - 키 불필요, User-Agent 헤더만 필요.
    - primary_candle을 생성하지 않으므로 단독 매매용으로는 사용하지 않는다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "YAHOO FINANCE DP"
    CODE = "YFN"

    DEFAULT_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (compatible; smtm/1.0; +https://github.com/msaltnet/smtm)"
    )
    DEFAULT_SYMBOLS = (
        ("DX-Y.NYB", "DXY"),
        ("^GSPC", "SP500"),
        ("^VIX", "VIX"),
        ("GC=F", "GOLD"),
        ("^TNX", "US10Y"),
        ("^IXIC", "NASDAQ"),
    )
    TIMEOUT = 5

    def __init__(self, currency="BTC", interval=60, url=None, symbols=None, user_agent=None):
        self.logger = LogManager.get_logger("YahooFinanceDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._symbols = list(symbols) if symbols else list(self.DEFAULT_SYMBOLS)
        self._user_agent = user_agent or self.DEFAULT_USER_AGENT

    def get_info(self):
        """구성된 심볼 각각에 대해 최신 시세·전일대비 변동률을 반환."""
        results = []
        for item in self._symbols:
            symbol, label = self._normalize_symbol(item)
            if not symbol:
                continue
            payload = self._fetch(symbol)
            entry = self._extract(payload, symbol, label)
            if entry:
                results.append(entry)
        return results

    def _normalize_symbol(self, item):
        if isinstance(item, (list, tuple)) and len(item) == 2:
            return item[0], item[1]
        if isinstance(item, str):
            return item, item
        return None, None

    def _fetch(self, symbol):
        try:
            response = request_with_retry(
                requests.get,
                f"{self._url}/{symbol}",
                params={"range": "1d", "interval": "5m"},
                headers={"User-Agent": self._user_agent},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch yahoo finance {symbol}: {err}")
            return None

    def _extract(self, payload, symbol, label):
        if not isinstance(payload, dict):
            return None
        chart = payload.get("chart")
        if not isinstance(chart, dict):
            return None
        results = chart.get("result")
        if not isinstance(results, list) or not results:
            return None
        meta = results[0].get("meta") if isinstance(results[0], dict) else None
        if not isinstance(meta, dict):
            return None

        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change_pct = None
        if isinstance(price, (int, float)) and isinstance(prev, (int, float)) and prev:
            change_pct = (price - prev) / prev * 100

        return {
            "type": "macro_market",
            "source": "yahoo_finance",
            "symbol": symbol,
            "label": label,
            "price": price,
            "previous_close": prev,
            "change_24h_pct": change_pct,
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName"),
            "timestamp": meta.get("regularMarketTime"),
        }
