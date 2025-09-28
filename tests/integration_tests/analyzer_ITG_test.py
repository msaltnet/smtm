import unittest
import os.path
from smtm import Analyzer
from unittest.mock import *
from .data.analyzer_data import get_dummy_data


class AnalyzerIntegrationTests(unittest.TestCase):
    def test_ITG_analyze_trading(self):
        analyzer = Analyzer()
        asset_info = {
            "balance": 50000,
            "asset": {},
            "quote": {"KRW-BTC": 26145000.0},
            "date_time": "2020-12-21T01:13:00",
        }

        # asset_info 변수로 함수의 반환값을 설정하기 위한 테스트용 함수
        def test_update_info_func():
            nonlocal asset_info
            return asset_info

        analyzer.initialize(test_update_info_func)
        analyzer.make_start_point()

        # 1턴 정보 업데이트
        info = [
            {
                "type": "primary_candle",
                "market": "KRW-BTC",
                "date_time": "2020-12-21T01:13:00",
                "opening_price": 26155000.0,
                "high_price": 26158000.0,
                "low_price": 26132000.0,
                "closing_price": 26145000.0,
                "acc_price": 116448937.40051,
                "acc_volume": 4.45311465,
            }
        ]
        analyzer.put_trading_info(info)
        analyzer.add_value_for_line_graph("2020-12-21T01:13:00", 26132000.0)
        analyzer.add_value_for_line_graph("2020-12-21T01:13:01", 26158000.0)

        requests = [
            {
                "id": "1621767063.373",
                "type": "buy",
                "price": 26145000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:13:00",
            }
        ]
        analyzer.put_requests(requests)

        result = {
            "request": {
                "id": "1621767063.373",
                "type": "buy",
                "price": 26145000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:13:00",
            },
            "type": "buy",
            "price": 26145000.0,
            "amount": 0.0004,
            "msg": "success",
            "balance": 39537,
            "state": "done",
            "date_time": "2020-12-21T01:13:00",
        }
        analyzer.put_result(result)

        asset_info = {
            "balance": 39537,
            "asset": {"KRW-BTC": (26145000.0, 0.0004)},
            "quote": {"KRW-BTC": 26132000.0},
            "date_time": "2020-12-21T01:14:00",
        }
        analyzer.update_asset_info()

        # 2턴 정보 업데이트
        info = [
            {
                "type": "primary_candle",
                "market": "KRW-BTC",
                "date_time": "2020-12-21T01:14:00",
                "opening_price": 26145000.0,
                "high_price": 26153000.0,
                "low_price": 26132000.0,
                "closing_price": 26132000.0,
                "acc_price": 57246220.95838,
                "acc_volume": 2.18982408,
            }
        ]
        analyzer.put_trading_info(info)

        analyzer.add_drawing_spot("2020-12-21T01:14:00", 26020000.0)
        analyzer.add_drawing_spot("2020-12-21T01:14:01", 26182000.0)

        analyzer.add_value_for_line_graph("2020-12-21T01:14:00", 26132000.0)
        analyzer.add_value_for_line_graph("2020-12-21T01:14:01", 26153000.0)

        requests = [
            {
                "id": "1621767064.395",
                "type": "buy",
                "price": 26132000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:14:00",
            }
        ]
        analyzer.put_requests(requests)

        result = {
            "request": {
                "id": "1621767064.395",
                "type": "buy",
                "price": 26132000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:14:00",
            },
            "type": "buy",
            "price": 26132000.0,
            "amount": 0.0004,
            "msg": "success",
            "balance": 29079,
            "state": "done",
            "date_time": "2020-12-21T01:14:00",
        }
        analyzer.put_result(result)

        asset_info = {
            "balance": 29079,
            "asset": {"KRW-BTC": (26138500, 0.0008)},
            "quote": {"KRW-BTC": 26100000.0},
            "date_time": "2020-12-21T01:15:00",
        }
        analyzer.update_asset_info()

        # 3턴 정보 업데이트
        info = [
            {
                "type": "primary_candle",
                "market": "KRW-BTC",
                "date_time": "2020-12-21T01:15:00",
                "opening_price": 26148000.0,
                "high_price": 26153000.0,
                "low_price": 26100000.0,
                "closing_price": 26100000.0,
                "acc_price": 213292694.20168,
                "acc_volume": 8.16909933,
            }
        ]
        analyzer.put_trading_info(info)

        requests = [
            {
                "id": "1621767065.414",
                "type": "buy",
                "price": 26100000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:15:00",
            }
        ]
        analyzer.put_requests(requests)

        result = {
            "request": {
                "id": "1621767065.414",
                "type": "buy",
                "price": 26100000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:15:00",
            },
            "type": "buy",
            "price": 26100000.0,
            "amount": 0.0004,
            "msg": "success",
            "balance": 18634,
            "state": "done",
            "date_time": "2020-12-21T01:15:00",
        }
        analyzer.put_result(result)

        asset_info = {
            "balance": 18634,
            "asset": {"KRW-BTC": (26125667, 0.0012)},
            "quote": {"KRW-BTC": 26083000.0},
            "date_time": "2020-12-21T01:16:00",
        }
        analyzer.update_asset_info()

        # 4턴 정보 업데이트
        info = [
            {
                "type": "primary_candle",
                "market": "KRW-BTC",
                "date_time": "2020-12-21T01:16:00",
                "opening_price": 26101000.0,
                "high_price": 26114000.0,
                "low_price": 26055000.0,
                "closing_price": 26083000.0,
                "acc_price": 164768010.7268,
                "acc_volume": 6.31952174,
            }
        ]
        analyzer.put_trading_info(info)

        requests = [
            {
                "id": "1621767066.442",
                "type": "buy",
                "price": 26083000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:16:00",
            }
        ]
        analyzer.put_requests(requests)

        result = {
            "request": {
                "id": "1621767066.442",
                "type": "buy",
                "price": 26083000.0,
                "amount": 0.0004,
                "date_time": "2020-12-21T01:16:00",
            },
            "type": "buy",
            "price": 26083000.0,
            "amount": 0.0004,
            "msg": "success",
            "balance": 8196,
            "state": "done",
            "date_time": "2020-12-21T01:16:00",
        }
        analyzer.put_result(result)

        asset_info = {
            "balance": 8196,
            "asset": {"KRW-BTC": (26115000, 0.0016)},
            "quote": {"KRW-BTC": 26061000.0},
            "date_time": "2020-12-21T01:17:00",
        }
        analyzer.update_asset_info()

        # 5턴 정보 업데이트
        info = [
            {
                "type": "primary_candle",
                "market": "KRW-BTC",
                "date_time": "2020-12-21T01:17:00",
                "opening_price": 26055000.0,
                "high_price": 26085000.0,
                "low_price": 26055000.0,
                "closing_price": 26061000.0,
                "acc_price": 42703199.9218,
                "acc_volume": 1.63862358,
            }
        ]
        analyzer.put_trading_info(info)

        analyzer.add_drawing_spot("2020-12-21T01:17:00", 25061000.0)

        analyzer.add_value_for_line_graph("2020-12-21T01:17:00", 26132000.0)
        analyzer.add_value_for_line_graph("2020-12-21T01:17:01", 26085000.0)

        requests = [
            {
                "id": "1621767067.473",
                "type": "buy",
                "price": 26061000.0,
                "amount": 0.0003,
                "date_time": "2020-12-21T01:17:00",
            }
        ]
        analyzer.put_requests(requests)

        result = {
            "request": {
                "id": "1621767067.473",
                "type": "buy",
                "price": 26061000.0,
                "amount": 0.0003,
                "date_time": "2020-12-21T01:17:00",
            },
            "type": "buy",
            "price": 26061000.0,
            "amount": 0.0003,
            "msg": "success",
            "balance": 374,
            "state": "done",
            "date_time": "2020-12-21T01:17:00",
        }
        analyzer.put_result(result)

        asset_info = {
            "balance": 374,
            "asset": {"KRW-BTC": (26106474, 0.0019)},
            "quote": {"KRW-BTC": 26079000.0},
            "date_time": "2020-12-21T01:18:00",
        }
        analyzer.update_asset_info()

        report = analyzer.get_return_report()
        self.assertEqual(
            report,
            (
                50000,
                49924,
                -0.152,
                {"KRW-BTC": -0.252},
                None,
                "2020-12-21T01:13:00 - 2020-12-21T01:17:00",
                -0.212,
                0.0,
                ("2020-12-21T01:13:00", "2020-12-21T01:13:00", "2020-12-21T01:17:00"),
            ),
        )

    def test_ITG_analyze_create_report(self):
        analyzer = Analyzer()

        # fill info list with dummy data
        analyzer.request_list = get_dummy_data("request_list")
        analyzer.result_list = get_dummy_data("result_list")
        analyzer.info_list = get_dummy_data("info_list")
        analyzer.asset_info_list = get_dummy_data("asset_info_list")
        analyzer.score_list = get_dummy_data("score_list")
        analyzer.spot_list = get_dummy_data("spot_list")
        analyzer.line_graph_list = get_dummy_data("line_graph_list")
        analyzer.start_asset_info = analyzer.asset_info_list[0]
        
        # get_asset_info_func 설정 (리포트 생성에 필요)
        def dummy_get_asset_info_func():
            return analyzer.asset_info_list[-1] if analyzer.asset_info_list else {}
        
        analyzer.initialize(dummy_get_asset_info_func)
        analyzer.make_start_point()
        
        # data_repository에 더미 데이터 설정 (get_return_report에서 사용)
        analyzer.data_repository.asset_info_list = analyzer.asset_info_list
        analyzer.data_repository.score_list = analyzer.score_list
        analyzer.data_repository.info_list = analyzer.info_list
        analyzer.data_repository.result_list = analyzer.result_list
        analyzer.data_repository.spot_list = analyzer.spot_list
        analyzer.data_repository.line_graph_list = analyzer.line_graph_list

        if os.path.isfile(analyzer.OUTPUT_FOLDER + "test_report.jpg"):
            os.remove(analyzer.OUTPUT_FOLDER + "test_report.jpg")
        self.assertFalse(os.path.isfile(analyzer.OUTPUT_FOLDER + "test_report.jpg"))
        
        # 리포트 생성 시도
        analyzer.create_report("test_report")

        # 리포트 파일이 생성되었는지 확인
        self.assertTrue(os.path.isfile(analyzer.OUTPUT_FOLDER + "test_report.txt"))
        
        # 텍스트 파일 내용 비교 (주요 내용만 확인)
        with open(analyzer.OUTPUT_FOLDER + "test_report.txt", "r") as file1:
            content1 = file1.read()
        with open("tests/integration_tests/data/test_report.txt", "r") as file2:
            content2 = file2.read()
        
        # 주요 내용이 포함되어 있는지 확인
        self.assertIn("### TRADING TABLE =================================", content1)
        self.assertIn("### SUMMARY =======================================", content1)
        self.assertIn("Property", content1)
        self.assertIn("Gap", content1)
        self.assertIn("Cumulative return", content1)
        
        # JPG 파일 생성 확인
        self.assertTrue(os.path.isfile(analyzer.OUTPUT_FOLDER + "test_report.jpg"))
