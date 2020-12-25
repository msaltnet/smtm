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
        analyzer.put_result("banana")
        self.assertEqual(analyzer.result[-1], "banana")
