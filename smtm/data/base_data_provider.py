import requests
from .data_provider import DataProvider
from ..log_manager import LogManager


class BaseDataProvider(DataProvider):
    """
    거래소 DataProvider의 공통 로직을 제공하는 기본 클래스

    Base class providing common logic for exchange data providers.
    Subclasses must implement:
        - get_info()
        - _create_candle_info(data)
    And set:
        - self._api_url: API endpoint URL
        - self._query_params: query parameters dict or None
    """

    def __init__(self, logger_name):
        self.logger = LogManager.get_logger(logger_name)
        self._api_url = None
        self._query_params = None
        self.market = None

    def _get_data_from_server(self):
        try:
            if self._query_params is not None:
                response = requests.get(self._api_url, params=self._query_params)
            else:
                response = requests.get(self._api_url)
            response.raise_for_status()
            return response.json()
        except ValueError as error:
            self.logger.error(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
