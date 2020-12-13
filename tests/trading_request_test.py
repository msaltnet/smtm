import unittest
from smtm import TradingRequest
from unittest.mock import *

class TradingRequestTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_set_info_update_info(self):
        trading_request = TradingRequest('banana')
        trading_request.set_info('buy', 5, 100)
        self.assertEqual(trading_request.type, 'banana')
        self.assertEqual(trading_request.price, 5)
        self.assertEqual(trading_request.amount, 100)

    def test_set_info_should_not_update_fixed_info(self):
        trading_request = TradingRequest('banana', 1000, 5)
        trading_request.set_info('buy', 5, 100)
        self.assertEqual(trading_request.type, 'banana')
        self.assertEqual(trading_request.price, 1000)
        self.assertEqual(trading_request.amount, 5)

    def test_is_stained_should_find_stain(self):
        trading_request = TradingRequest('banana', 1234, 5678)
        self.assertEqual(trading_request.is_stained(), False)
        trading_request.id = 1234
        self.assertEqual(trading_request.is_stained(), True)

        trading_request.type = 'mango'
        self.assertEqual(trading_request.is_stained(), True)

        trading_request2 = TradingRequest('banana', 1234, 5678)
        trading_request2.price = 1233
        self.assertEqual(trading_request2.is_stained(), True)

        trading_request3 = TradingRequest('banana', 1234, 5678)
        trading_request3.amount = 5678
        self.assertEqual(trading_request3.is_stained(), False)
        trading_request3.amount = 5679
        self.assertEqual(trading_request3.is_stained(), True)

    def test_set_state_submitted_should_update_submitted_state(self):
        trading_request = TradingRequest('banana', 1000, 5)
        self.assertEqual(trading_request.is_submitted(), False)
        trading_request.set_state_submitted()
        self.assertEqual(trading_request.is_submitted(), True)
