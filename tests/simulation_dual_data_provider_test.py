import unittest
from smtm import SimulationDualDataProvider
from unittest.mock import *


class SimulationDualDataProviderTests(unittest.TestCase):
    def test_initialize_simulation_should_call_repo_get_data_correctly(self):
        dp = SimulationDualDataProvider()
        dp.index = 10
        dp.repo_upbit = MagicMock()
        dp.repo_upbit.get_data = MagicMock(return_value="orange")
        dp.repo_binance = MagicMock()
        dp.repo_binance.get_data = MagicMock(return_value="banana")
        dp.initialize_simulation("2020-03-20T00:00:00", 10)

        self.assertEqual(dp.index, 0)
        self.assertEqual(dp.data_upbit, "orange")
        self.assertEqual(dp.data_binance, "banana")
        dp.repo_upbit.get_data.assert_called_once_with(
            "2020-03-19T23:50:00", "2020-03-20T00:00:00", market="KRW-BTC"
        )
        dp.repo_binance.get_data.assert_called_once_with(
            "2020-03-19T23:50:00", "2020-03-20T00:00:00", market="BTCUSDT"
        )

    def test_get_info_return_None_without_initialize(self):
        dp = SimulationDualDataProvider()
        self.assertEqual(dp.get_info(), None)

    def test_get_info_return_next_data_correctly(self):
        dummy_data_upbit = [
            {"market": "mango", "date_time": "2020-03-20T00:00:00"},
            {"market": "banana", "date_time": "2020-03-20T00:01:00"},
            {"market": "orange", "date_time": "2020-03-20T00:02:00"},
        ]
        dummy_data_binance = [
            {"market": "mango-binance", "date_time": "2020-03-20T00:00:00"},
            {"market": "banana-binance", "date_time": "2020-03-20T00:01:00"},
            {"market": "orange-binance", "date_time": "2020-03-20T00:02:00"},
        ]
        dp = SimulationDualDataProvider()
        dp.index = 0
        dp.data_upbit = dummy_data_upbit
        dp.data_binance = dummy_data_binance
        data = dp.get_info()
        self.assertEqual(len(data), 2)
        self.assertTrue(dummy_data_upbit[0] in data)
        self.assertTrue(dummy_data_binance[0] in data)
        self.assertEqual(dp.index, 1)
        data = dp.get_info()
        self.assertEqual(len(data), 2)
        self.assertTrue(dummy_data_upbit[1] in data)
        self.assertTrue(dummy_data_binance[1] in data)
        self.assertEqual(dp.index, 2)
        data = dp.get_info()
        self.assertEqual(len(data), 2)
        self.assertTrue(dummy_data_upbit[2] in data)
        self.assertTrue(dummy_data_binance[2] in data)
        self.assertEqual(dp.index, 3)
        data = dp.get_info()
        self.assertEqual(data, None)
        self.assertEqual(dp.index, 3)
