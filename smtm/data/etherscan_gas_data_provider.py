import os
import requests
from .data_provider import DataProvider
from ..log_manager import LogManager
from ..http_session import request_with_retry


class EtherscanGasDataProvider(DataProvider):
    """
    Etherscan Gas Tracker로 Ethereum 가스 가격 권장값을
    type='eth_gas' 한 건으로 반환하는 DataProvider.

    Fetches the safe / propose / fast gas prices (gwei) plus the suggested
    base fee from https://api.etherscan.io/api?module=gastracker&action=gasoracle
    and normalizes them into a single `type='eth_gas'` dict.

    - API 키 없이도 호출되지만 rate limit이 낮다. `ETHERSCAN_API_KEY` 환경변수를
      설정하거나 `api_key` 인자로 전달하면 상향된다.
    - ETH 거래와 무관한 통화에서 호출돼도 네트워크 혼잡 지표로 의미가 있다.
    - 실패 시 빈 리스트를 반환해 매매 루프를 막지 않는다.
    """

    NAME = "ETHERSCAN GAS DP"
    CODE = "EGS"

    DEFAULT_URL = "https://api.etherscan.io/api"
    TIMEOUT = 5

    def __init__(self, currency="ETH", interval=60, url=None, api_key=None):
        self.logger = LogManager.get_logger("EtherscanGasDataProvider")
        self.market = currency
        self.interval = interval
        self._url = url or self.DEFAULT_URL
        self._api_key = api_key or os.environ.get("ETHERSCAN_API_KEY")

    def get_info(self):
        payload = self._fetch()
        if not isinstance(payload, dict):
            return []
        if str(payload.get("status")) != "1":
            self.logger.warning(f"Etherscan gas oracle returned status: {payload.get('message')}")
            return []
        result = payload.get("result")
        if not isinstance(result, dict):
            return []

        return [
            {
                "type": "eth_gas",
                "source": "etherscan",
                "unit": "gwei",
                "safe_gas_price": self._to_float(result.get("SafeGasPrice")),
                "propose_gas_price": self._to_float(result.get("ProposeGasPrice")),
                "fast_gas_price": self._to_float(result.get("FastGasPrice")),
                "suggest_base_fee": self._to_float(result.get("suggestBaseFee")),
                "gas_used_ratio": result.get("gasUsedRatio"),
                "last_block": result.get("LastBlock"),
            }
        ]

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fetch(self):
        params = {"module": "gastracker", "action": "gasoracle"}
        if self._api_key:
            params["apikey"] = self._api_key
        try:
            response = request_with_retry(
                requests.get, self._url, params=params, timeout=self.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as err:
            self.logger.warning(f"Failed to fetch etherscan gas: {err}")
            return None
