import unittest
from smtm import SimulatorDataProvider
from unittest.mock import *
import requests

class SimulatorDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_info_return_false_without_initialize(self):
        dp = SimulatorDataProvider()
        self.assertEqual(dp.get_info(), False)

    def test_get_info_return_false_with_none_initialized(self):
        dp = SimulatorDataProvider()
        dp.initialize(None)
        self.assertEqual(dp.get_info(), False)

    def test_get_info_return_correct_info_after_initialized_with_dummy_data(self):
        http = Mock()
        jd = lambda: None
        jd.text = '''
        [
            {
                "market":"mango",
                "candle_date_time_utc":"2020-02-25T06:41:00",
                "candle_date_time_kst":"2020-02-25T15:41:00",
                "opening_price":11436000.00000000,
                "high_price":11443000.00000000,
                "low_price":11428000.00000000,
                "trade_price":11443000.00000000,
                "timestamp":1582612901489,
                "candle_acc_trade_price":17001839.06758000,
                "candle_acc_trade_volume":1.48642105,
                "unit":1
            },
            {
                "market":"banana",
                "candle_date_time_utc":"2020-02-25T06:41:00",
                "candle_date_time_kst":"2020-02-25T15:41:00",
                "opening_price":11436000.00000000,
                "high_price":11443000.00000000,
                "low_price":11428000.00000000,
                "trade_price":11443000.00000000,
                "timestamp":1582612901489,
                "candle_acc_trade_price":17001839.06758000,
                "candle_acc_trade_volume":1.48642105,
                "unit":1
            }
        ]
        '''
        http.request = MagicMock(return_value=jd)
        dp = SimulatorDataProvider()
        dp.initialize(http)
        self.assertEqual(dp.get_info().market, "mango")
        self.assertEqual(dp.get_info().market, "banana")
        self.assertEqual(dp.get_info(), None)
    # def test_temp(self):
    #     http = requests
    #     dp = SimulatorDataProvider()
    #     dp.initialize(http, "2020-01-19 20:34:42", 10)
    #     self.assertEqual(dp.get_info(), "test")