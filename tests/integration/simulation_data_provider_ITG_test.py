import unittest
from smtm import SimulationDataProvider
from unittest.mock import *
import requests


class SimulationDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_get_info_use_server_data_without_end(self):
        dp = SimulationDataProvider()
        return_value = dp.initialize_from_server(count=50)
        if dp.is_initialized is not True:
            self.assertEqual(dp.get_info(), None)
            self.assertEqual(return_value, None)
            return
        info = dp.get_info()
        self.assertEqual("market" in info, True)
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 50)

    def test_ITG_get_info_use_server_data(self):
        dp = SimulationDataProvider()
        end_date = "2020-04-30T07:30:00Z"
        return_value = dp.initialize_from_server(end=end_date, count=50)
        if dp.is_initialized is not True:
            self.assertEqual(dp.get_info(), None)
            self.assertEqual(return_value, None)
            return
        info = dp.get_info()
        self.assertEqual("market" in info, True)
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 50)

        self.assertEqual(info["market"], "KRW-BTC")
        self.assertEqual(info["date_time"], "2020-04-30T15:40:00")
        self.assertEqual(info["opening_price"], 11356000.0)
        self.assertEqual(info["high_price"], 11372000.0)
        self.assertEqual(info["low_price"], 11356000.0)
        self.assertEqual(info["closing_price"], 11372000.0)
        self.assertEqual(info["acc_price"], 116037727.81296)
        self.assertEqual(info["acc_volume"], 10.20941879)

        info = dp.get_info()
        self.assertEqual(info["market"], "KRW-BTC")
        self.assertEqual(info["date_time"], "2020-04-30T15:41:00")
        self.assertEqual(info["opening_price"], 11370000.0)
        self.assertEqual(info["high_price"], 11372000.0)
        self.assertEqual(info["low_price"], 11360000.0)
        self.assertEqual(info["closing_price"], 11370000.0)
        self.assertEqual(info["acc_price"], 239216440.29876)
        self.assertEqual(info["acc_volume"], 21.05049702)

    def test_ITG_get_info_use_json_file(self):
        dp = SimulationDataProvider()
        dp.initialize_with_file("./tests/data/test_record.json")
        info = dp.get_info()
        self.assertEqual("market" in info, True)
        self.assertEqual("date_time" in info, True)
        self.assertEqual("opening_price" in info, True)
        self.assertEqual("high_price" in info, True)
        self.assertEqual("low_price" in info, True)
        self.assertEqual("closing_price" in info, True)
        self.assertEqual("acc_price" in info, True)
        self.assertEqual("acc_volume" in info, True)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 100)
        self.assertEqual(info["market"], "KRW-BTC")
        self.assertEqual(info["date_time"], "2020-03-10T22:52:00")
        self.assertEqual(info["opening_price"], 9777000.00000000)
        self.assertEqual(info["high_price"], 9778000.00000000)
        self.assertEqual(info["low_price"], 9763000.00000000)
        self.assertEqual(info["closing_price"], 9778000.00000000)
        self.assertEqual(info["acc_price"], 11277224.71063000)
        self.assertEqual(info["acc_volume"], 1.15377852)
