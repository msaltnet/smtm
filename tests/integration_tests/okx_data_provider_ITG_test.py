import unittest
from smtm import OkxDataProvider


class OkxDataProviderIntegrationTests(unittest.TestCase):
    def _assert_candle_schema(self, info, market=None):
        self.assertEqual(info["type"], "primary_candle")
        if market is not None:
            self.assertEqual(info["market"], market)
        for key in ("market", "date_time", "opening_price", "high_price",
                    "low_price", "closing_price", "acc_price", "acc_volume"):
            self.assertIn(key, info)
        for key in ("opening_price", "high_price", "low_price",
                    "closing_price", "acc_price", "acc_volume"):
            self.assertIsInstance(info[key], float)

    def test_ITG_get_info_return_correct_data(self):
        self._assert_candle_schema(OkxDataProvider().get_info()[0])

    def test_ITG_get_info_return_correct_data_when_currency_is_BTC(self):
        self._assert_candle_schema(OkxDataProvider("BTC").get_info()[0], "BTC")

    def test_ITG_get_info_return_correct_data_when_currency_is_ETH(self):
        self._assert_candle_schema(OkxDataProvider("ETH").get_info()[0], "ETH")

    def test_ITG_get_info_return_correct_data_when_currency_is_DOGE(self):
        self._assert_candle_schema(OkxDataProvider("DOGE").get_info()[0], "DOGE")

    def test_ITG_get_info_return_correct_data_when_currency_is_XRP(self):
        self._assert_candle_schema(OkxDataProvider("XRP").get_info()[0], "XRP")
