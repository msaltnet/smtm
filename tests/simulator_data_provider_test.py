import unittest
from smtm import SimulatorDataProvider
from unittest.mock import *
import requests

class SimulatorDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_info_without_initialize(self):
        dp = SimulatorDataProvider()
        self.assertEqual(dp.get_info(), False)

    def test_get_info_with_none_initialized(self):
        dp = SimulatorDataProvider()
        dp.initialize(None, None, None)
        self.assertEqual(dp.get_info(), False)

    def test_get_info_after_initialized_with_dummy_data(self):
        http = Mock()
        jd = lambda: None
        jd.text = '[{"market": "mango"}, {"market": "banana"}]'
        http.request = MagicMock(return_value=jd)
        dp = SimulatorDataProvider()
        dp.initialize(http, None, None)
        self.assertEqual(dp.get_info()['market'], "mango")
        self.assertEqual(dp.get_info()['market'], "banana")
        self.assertEqual(dp.get_info(), None)

    # def test_temp(self):
    #     http = requests
    #     dp = SimulatorDataProvider()
    #     dp.initialize(http, "2020-01-19 20:34:42", 10)
    #     self.assertEqual(dp.get_info(), "test")