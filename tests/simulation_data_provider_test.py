import unittest
from smtm import SimulationDataProvider
from unittest.mock import *


class SimulationDataProviderTests(unittest.TestCase):
    def test_initialize_simulation_should_call_repo_get_data_correctly(self):
        dp = SimulationDataProvider()
        dp.index = 10
        dp.repo = MagicMock()
        dp.repo.get_data = MagicMock(return_value="orange")
        dp.initialize_simulation("2020-03-20T00:00:00", 10)

        self.assertEqual(dp.index, 0)
        self.assertEqual(dp.data, "orange")
        dp.repo.get_data.assert_called_once_with(
            "2020-03-19T23:50:00", "2020-03-20T00:00:00", market="KRW-BTC"
        )

    def test_get_info_return_None_without_initialize(self):
        dp = SimulationDataProvider()
        self.assertEqual(dp.get_info(), None)

    def test_get_info_return_next_data_correctly(self):
        dummy_data = [
            {"market": "mango", "date_time": "2020-03-20T00:00:00"},
            {"market": "banana", "date_time": "2020-03-20T00:01:00"},
            {"market": "orange", "date_time": "2020-03-20T00:02:00"},
        ]
        dp = SimulationDataProvider()
        dp.index = 0
        dp.data = dummy_data
        self.assertEqual(dp.get_info(), dummy_data[0])
        self.assertEqual(dp.get_info(), dummy_data[1])
        self.assertEqual(dp.get_info(), dummy_data[2])
        self.assertEqual(dp.get_info(), None)
