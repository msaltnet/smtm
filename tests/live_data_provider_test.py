import unittest
from simulator import LiveDataProvider
from unittest.mock import *
import requests

class LiveDataProviderTests(unittest.TestCase):
    url = 'https://api.upbit.com/v1/candles/minutes/1?market=KRW-BTC&count=100'

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_info_without_initialize(self):
        dp = LiveDataProvider()
        self.assertEqual(dp.get_info(), False)

    def test_get_info_with_none_initialized(self):
        dp = LiveDataProvider()
        dp.initialize(None, None)
        self.assertEqual(dp.get_info(), False)

    def test_get_info_with_initialized(self):
        http = Mock()
        http.get = MagicMock(side_effect=lambda value: value)
        dp = LiveDataProvider()
        dp.initialize(http, "Mock Url")
        self.assertEqual(dp.get_info(), "Mock Url")