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
        analyzer.update_info_func = MagicMock()
        analyzer.put_result("banana")
        self.assertEqual(analyzer.result[-1], "banana")

    def test_put_result_call_update_info_func_with_asset_type_and_callback(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_info_func = MagicMock()
        analyzer.put_result("banana")
        analyzer.update_info_func.assert_called_once_with("asset", analyzer.put_asset_info)

    def test_initialize_keep_update_info_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        self.assertEqual(analyzer.update_info_func, "mango")

    def test_put_asset_info_append_asset_info(self):
        analyzer = Analyzer()
        analyzer.make_yield_record = MagicMock()
        analyzer.put_asset_info("apple")
        self.assertEqual(analyzer.asset_record_list[-1], "apple")

    def test_put_asset_info_should_call_make_yield_record(self):
        analyzer = Analyzer()
        analyzer.make_yield_record = MagicMock()
        analyzer.put_asset_info("apple")
        self.assertEqual(analyzer.asset_record_list[-1], "apple")
        analyzer.make_yield_record.assert_called_once_with("apple")

    def test_make_start_point_call_update_info_func_with_asset_type_and_callback(self):
        analyzer = Analyzer()
        analyzer.update_info_func = MagicMock()
        analyzer.make_start_point()
        analyzer.update_info_func.assert_called_once_with("asset", analyzer.put_asset_info)

    def test_make_start_point_clear_asset_info_and_request_result(self):
        analyzer = Analyzer()
        analyzer.update_info_func = MagicMock()
        analyzer.request.append("mango")
        analyzer.result.append("banana")
        analyzer.asset_record_list.append("apple")
        analyzer.make_start_point()
        self.assertEqual(len(analyzer.request), 0)
        self.assertEqual(len(analyzer.result), 0)
        self.assertEqual(len(analyzer.asset_record_list), 0)

    def test_make_yield_record_create_correct_yield_record_when_asset_is_not_changed(self):
        analyzer = Analyzer()
        class DummyAssetInfo():
            pass
        dummy_asset = DummyAssetInfo()
        dummy_asset.balance = 50000
        dummy_asset.asset = [
            ("banana", 1500, 1700, 10),
            ("mango", 1000, 700, 4.5),
            ("apple", 250, 500, 2)]

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset)

        target_dummy_asset = DummyAssetInfo()
        target_dummy_asset.balance = 50000
        target_dummy_asset.asset = [
            ("banana", 1500, 2000, 10),
            ("mango", 1000, 1050, 4.5),
            ("apple", 250, 400, 2)]
        target_dummy_asset.timestamp = 500

        analyzer.make_yield_record(target_dummy_asset)
        self.assertEqual(len(analyzer.yield_record_list), 1)

        yield_record = analyzer.yield_record_list[0]
        self.assertEqual(yield_record.balance, 50000)
        self.assertEqual(yield_record.cumulative_return, 6.149)

        self.assertEqual(yield_record.asset[0][0], "banana")
        self.assertEqual(yield_record.asset[0][1], 1500)
        self.assertEqual(yield_record.asset[0][2], 2000)
        self.assertEqual(yield_record.asset[0][3], 10)
        self.assertEqual(yield_record.asset[0][4], 33.333)

        self.assertEqual(yield_record.asset[1][0], "mango")
        self.assertEqual(yield_record.asset[1][1], 1000)
        self.assertEqual(yield_record.asset[1][2], 1050)
        self.assertEqual(yield_record.asset[1][3], 4.5)
        self.assertEqual(yield_record.asset[1][4], 5)

        self.assertEqual(yield_record.asset[2][0], "apple")
        self.assertEqual(yield_record.asset[2][1], 250)
        self.assertEqual(yield_record.asset[2][2], 400)
        self.assertEqual(yield_record.asset[2][3], 2)
        self.assertEqual(yield_record.asset[2][4], 60)

    def test_make_yield_record_create_correct_yield_record_when_asset_is_changed(self):
        analyzer = Analyzer()
        class DummyAssetInfo():
            pass
        dummy_asset = DummyAssetInfo()
        dummy_asset.balance = 50000
        dummy_asset.asset = [
            ("banana", 1500, 1700, 10),
            ("apple", 250, 500, 2)]

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset)

        target_dummy_asset = DummyAssetInfo()
        target_dummy_asset.balance = 10000
        target_dummy_asset.asset = [
            ("mango", 1000, 50, 7.5),
            ("apple", 250, 800, 10.7)]
        target_dummy_asset.timestamp = 500

        analyzer.make_yield_record(target_dummy_asset)
        self.assertEqual(len(analyzer.yield_record_list), 1)

        yield_record = analyzer.yield_record_list[0]
        self.assertEqual(yield_record.balance, 10000)
        self.assertEqual(yield_record.cumulative_return, -72.154)

        self.assertEqual(yield_record.asset[0][0], "mango")
        self.assertEqual(yield_record.asset[0][1], 1000)
        self.assertEqual(yield_record.asset[0][2], 50)
        self.assertEqual(yield_record.asset[0][3], 7.5)
        self.assertEqual(yield_record.asset[0][4], -95)

        self.assertEqual(yield_record.asset[1][0], "apple")
        self.assertEqual(yield_record.asset[1][1], 250)
        self.assertEqual(yield_record.asset[1][2], 800)
        self.assertEqual(yield_record.asset[1][3], 10.7)
        self.assertEqual(yield_record.asset[1][4], 220)
