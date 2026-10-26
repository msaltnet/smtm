"""Bounded public quote reads for opt-in exchange-rules PAPER sessions only."""
import math

import requests

from .binance_data_provider import BinanceDataProvider
from .okx_data_provider import OkxDataProvider


class PaperQuoteError(UserWarning):
    """Diagnostic that does not expose response bodies or request exception details."""


class _PaperQuoteMixin:
    def _fail(self, category):
        message = f"PAPER quote blocked: {category}"
        self.logger.warning(message)
        raise PaperQuoteError(message) from None

    def _get_data_from_server(self):
        try:
            response = requests.get(self._api_url, params=self._query_params,
                                    timeout=5, allow_redirects=False)
        except requests.Timeout:
            self._fail("timeout")
        except requests.ConnectionError:
            self._fail("connection")
        except requests.RequestException:
            self._fail("request_error")
        if response.status_code != 200:
            status = response.status_code
            category = f"http_{status}" if type(status) is int and 100 <= status <= 599 else "http_error"
            self._fail(category)
        try:
            return response.json()
        except ValueError:
            self._fail("invalid_response")

    def get_info(self):
        data = self._get_data_from_server()
        try:
            if self.CODE == "OKX":
                if not isinstance(data, dict) or str(data.get("code")) != "0":
                    raise ValueError
                data = data.get("data")
            if not isinstance(data, list) or not data or not isinstance(data[0], list):
                raise ValueError
            row = data[0]
            quote_index = 6 if self.CODE == "OKX" else 7
            values = [row[i] for i in (0, 1, 2, 3, 4, 5, quote_index)]
            if any(isinstance(value, bool) for value in values):
                raise ValueError
            stamp, opening, high, low, closing, volume, amount = map(float, values)
            if not all(math.isfinite(value) for value in (stamp, opening, high, low, closing, volume, amount)):
                raise ValueError
            if min(opening, high, low, closing) <= 0 or min(stamp, volume, amount) < 0:
                raise ValueError
            if high < max(opening, closing, low) or low > min(opening, closing):
                raise ValueError
            candle = {"type": "primary_candle", "market": self.market,
                      "date_time": self._get_kst_time_from_unix_time_ms(stamp),
                      "opening_price": opening, "high_price": high, "low_price": low,
                      "closing_price": closing, "acc_volume": volume, "acc_price": amount}
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            self._fail("invalid_response")
        return [candle]


class PaperBinanceDataProvider(_PaperQuoteMixin, BinanceDataProvider):
    pass


class PaperOkxDataProvider(_PaperQuoteMixin, OkxDataProvider):
    pass


def create_paper_data_provider(exchange, currency, interval):
    providers = {"BNC": PaperBinanceDataProvider, "OKX": PaperOkxDataProvider}
    if exchange not in providers:
        raise ValueError("unsupported PAPER quote exchange")
    return providers[exchange](currency=currency, interval=interval)
