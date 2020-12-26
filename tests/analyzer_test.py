import unittest
from smtm import Analyzer
from unittest.mock import *

class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_put_request_append_request(self):
        analyzer = Analyzer()
        analyzer.put_request("mango")
        self.assertEqual(analyzer.request[-1], "mango")

    def test_put_result_append_result(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.request_asset_update_func = MagicMock()
        analyzer.put_result("banana")
        self.assertEqual(analyzer.result[-1], "banana")

    def test_put_result_call_request_asset_update_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.request_asset_update_func = MagicMock()
        analyzer.put_result("banana")
        analyzer.request_asset_update_func.assert_called_once()

    def test_initialize_keep_request_asset_update_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        self.assertEqual(analyzer.request_asset_update_func, "mango")

    def test_put_asset_info_append_asset_info(self):
        analyzer = Analyzer()
        analyzer.put_asset_info("apple")
        self.assertEqual(analyzer.asset_record_list[-1], "apple")
