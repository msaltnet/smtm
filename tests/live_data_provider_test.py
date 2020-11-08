import unittest
from simulator import LiveDataProvider
from unittest.mock import *
import requests

class LiveDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_info_without_initialize(self):
        dp = LiveDataProvider()
        self.assertEqual(dp.get_info(), False)

    def test_get_info_with_none_initialized(self):
        dp = LiveDataProvider()
        dp.initialize(None)
        self.assertEqual(dp.get_info(), False)

    def test_get_info_with_initialized(self):
        http = Mock()
        jd = lambda: None
        jd.text = '[{"market": "test"}]'
        http.request = MagicMock(return_value=jd)
        dp = LiveDataProvider()
        dp.initialize(http)
        self.assertEqual(dp.get_info()['market'], "test")

    # def test_real_data(self):
    #     http = requests
    #     dp = LiveDataProvider()
    #     dp.initialize(http)
    #     print(dp.get_info())
    #     self.assertEqual(1, 1)