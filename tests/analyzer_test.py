import copy
import unittest
from smtm import Analyzer
from unittest.mock import *
from datetime import datetime, timedelta


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_drawing_spot_append_spot_info(self):
        analyzer = Analyzer()
        analyzer.add_drawing_spot("2020-02-27T23:00:00", 12345)
        analyzer.add_drawing_spot("2020-02-27T24:00:00", 700)
        self.assertEqual(analyzer.spot_list[0]["date_time"], "2020-02-27T23:00:00")
        self.assertEqual(analyzer.spot_list[0]["value"], 12345)
        self.assertEqual(analyzer.spot_list[1]["date_time"], "2020-02-27T24:00:00")
        self.assertEqual(analyzer.spot_list[1]["value"], 700)

    def test_put_requests_append_request(self):
        analyzer = Analyzer()
        dummy_requests = [
            {"id": "orange", "type": "buy", "price": 5000, "amount": 1},
            {"id": "mango", "type": "cancel"},
        ]
        analyzer.put_requests(dummy_requests)
        self.assertEqual(
            analyzer.request_list[-2],
            {"id": "orange", "type": "buy", "price": 5000.0, "amount": 1.0, "kind": 1},
        )
        self.assertEqual(
            analyzer.request_list[-1],
            {"id": "mango", "type": "cancel", "price": 0, "amount": 0, "kind": 1},
        )

        dummy_requests = [
            {"id": "banana", "type": "buy", "price": 0, "amount": 1},
            {"id": "apple", "type": "cancel"},
        ]
        analyzer.put_requests(dummy_requests)
        self.assertEqual(analyzer.request_list[-2]["id"], "mango")
        self.assertEqual(analyzer.request_list[-1]["id"], "apple")
        self.assertEqual(analyzer.request_list[-1]["type"], "cancel")

        dummy_requests = [
            {"id": "pineapple", "type": "buy", "price": 500, "amount": 0},
        ]
        analyzer.put_requests(dummy_requests)
        self.assertNotEqual(analyzer.request_list[-1], dummy_requests[0])
        self.assertEqual(analyzer.request_list[-1]["id"], "apple")

        dummy_requests = [
            {"id": "papaya", "type": "sell", "price": 5000, "amount": 0.0007},
            {"id": "orange", "type": "cancel", "price": 500, "amount": 0.0001},
            {"id": "pear", "type": "buy", "price": 500, "amount": 0.0000000000000000000000001},
        ]
        analyzer.put_requests(dummy_requests)
        self.assertEqual(analyzer.request_list[-1]["id"], "pear")
        self.assertEqual(analyzer.request_list[-1]["type"], "buy")
        self.assertEqual(analyzer.request_list[-1]["price"], 500.0)
        self.assertEqual(analyzer.request_list[-1]["amount"], 0.0000000000000000000000001)
        self.assertEqual(analyzer.request_list[-1]["kind"], 1)

        self.assertEqual(analyzer.request_list[-2]["id"], "orange")
        self.assertEqual(analyzer.request_list[-2]["type"], "cancel")
        self.assertEqual(analyzer.request_list[-2]["price"], 0)
        self.assertEqual(analyzer.request_list[-2]["amount"], 0)
        self.assertEqual(analyzer.request_list[-2]["kind"], 1)

        self.assertEqual(analyzer.request_list[-3]["id"], "papaya")
        self.assertEqual(analyzer.request_list[-3]["type"], "sell")
        self.assertEqual(analyzer.request_list[-3]["price"], 5000.0)
        self.assertEqual(analyzer.request_list[-3]["amount"], 0.0007)
        self.assertEqual(analyzer.request_list[-3]["kind"], 1)

    def test_put_trading_info_append_trading_info(self):
        analyzer = Analyzer()
        analyzer.make_periodic_record = MagicMock()
        dummy_info = {"name": "orange"}
        analyzer.put_trading_info(dummy_info)
        self.assertEqual(analyzer.info_list[-1], {"name": "orange", "kind": 0})
        analyzer.make_periodic_record.assert_called_once()

    def test_make_periodic_record_should_call_update_asset_info_after_60s_from_last_asset_info(
        self,
    ):
        analyzer = Analyzer()
        ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
        last = datetime.now() - timedelta(seconds=61)
        dummy_info1 = {"name": "mango", "date_time": last.strftime(ISO_DATEFORMAT)}
        dummy_info2 = {"name": "orange", "date_time": last.strftime(ISO_DATEFORMAT)}
        analyzer.update_asset_info = MagicMock()
        analyzer.asset_info_list.append(dummy_info1)
        analyzer.asset_info_list.append(dummy_info2)

        analyzer.make_periodic_record()

        analyzer.update_asset_info.assert_called_once()

    def test_make_periodic_record_should_NOT_call_update_asset_info_in_60s_from_last_asset_info(
        self,
    ):
        analyzer = Analyzer()
        ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
        last = datetime.now() - timedelta(seconds=55)
        dummy_info1 = {"name": "mango", "date_time": last.strftime(ISO_DATEFORMAT)}
        dummy_info2 = {"name": "orange", "date_time": last.strftime(ISO_DATEFORMAT)}
        analyzer.update_asset_info = MagicMock()
        analyzer.get_asset_info_func = MagicMock(return_value="mango")
        analyzer.asset_info_list.append(dummy_info1)
        analyzer.asset_info_list.append(dummy_info2)

        analyzer.make_periodic_record()

        analyzer.update_asset_info.assert_not_called()
        analyzer.get_asset_info_func.assert_not_called()

    def test_put_result_append_only_success_result(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()

        dummy_result = {"request": {"id": "orange"}, "price": 5000, "amount": 1}
        analyzer.put_result(dummy_result)
        self.assertEqual(
            analyzer.result_list[-1],
            {"request": {"id": "orange"}, "price": 5000, "amount": 1, "kind": 2},
        )

        dummy_result = {"request": {"id": "banana"}, "price": 0, "amount": 1}
        analyzer.put_result(dummy_result)
        self.assertNotEqual(
            analyzer.result_list[-1],
            {"request": {"id": "banana"}, "price": 0, "amount": 1, "kind": 2},
        )
        self.assertEqual(analyzer.result_list[-1]["request"]["id"], "orange")

        dummy_result = {"request": {"id": "apple"}, "price": 500, "amount": 0}
        analyzer.put_result(dummy_result)
        self.assertNotEqual(analyzer.result_list[-1]["request"]["id"], "apple")
        self.assertNotEqual(analyzer.result_list[-1]["price"], 500)
        self.assertEqual(analyzer.result_list[-1]["request"]["id"], "orange")
        self.assertEqual(analyzer.result_list[-1]["kind"], 2)

        dummy_result = {
            "request": {"id": "kiwi"},
            "price": 500,
            "amount": 0.0000000000000000000000001,
        }
        analyzer.put_result(dummy_result)
        self.assertEqual(analyzer.result_list[-1]["request"]["id"], "kiwi")
        self.assertEqual(analyzer.result_list[-1]["price"], 500)
        self.assertEqual(analyzer.result_list[-1]["amount"], 0.0000000000000000000000001)
        self.assertEqual(analyzer.result_list[-1]["kind"], 2)
        analyzer.update_asset_info.assert_called()

    def test_put_result_call_update_asset_info_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()
        dummy_result = {
            "request": {"id": "banana"},
            "price": 500,
            "amount": 0.0000000000000000000000001,
        }
        analyzer.put_result(dummy_result)
        analyzer.update_asset_info.assert_called_once()

    def test_initialize_keep_update_info_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        self.assertEqual(analyzer.get_asset_info_func, "mango")

    def test_update_asset_info_append_asset_info(self):
        analyzer = Analyzer()
        analyzer.make_score_record = MagicMock()
        dummy_info = {
            "balance": 5000,
            "asset": "apple",
            "quote": "apple_quote",
        }
        analyzer.get_asset_info_func = MagicMock(return_value=dummy_info)
        analyzer.update_asset_info()
        self.assertEqual(analyzer.asset_info_list[-1], dummy_info)

    def test_update_asset_info_should_call_make_score_record(self):
        analyzer = Analyzer()
        analyzer.make_score_record = MagicMock()
        dummy_info = {
            "balance": 5000,
            "asset": "apple",
            "quote": "apple_quote",
        }
        analyzer.get_asset_info_func = MagicMock(return_value=dummy_info)
        analyzer.update_asset_info()
        self.assertEqual(analyzer.asset_info_list[-1], dummy_info)
        analyzer.make_score_record.assert_called_once_with(dummy_info)

    def test_make_start_point_call_update_info_func(self):
        analyzer = Analyzer()
        analyzer.update_asset_info = MagicMock()
        analyzer.make_start_point()
        analyzer.update_asset_info.assert_called_once()

    def test_make_start_point_clear_asset_info_and_request_result(self):
        analyzer = Analyzer()
        analyzer.update_asset_info = MagicMock()
        analyzer.request_list.append("mango")
        analyzer.result_list.append("banana")
        analyzer.asset_info_list.append("apple")
        analyzer.make_start_point()
        self.assertEqual(len(analyzer.request_list), 0)
        self.assertEqual(len(analyzer.result_list), 0)
        self.assertEqual(len(analyzer.asset_info_list), 0)
        analyzer.update_asset_info.assert_called_once()

    def test_make_score_record_create_correct_score_record_when_asset_is_not_changed(self):
        analyzer = Analyzer()
        analyzer.make_periodic_record = MagicMock()
        dummy_asset_info = {
            "balance": 50000,
            "asset": {"banana": (1500, 10), "mango": (1000, 4.5), "apple": (250, 2)},
            "quote": {"banana": 1700, "mango": 700, "apple": 500, "pineapple": 300, "kiwi": 77000},
            "date_time": "2020-02-27T23:59:59",
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.update_start_point(dummy_asset_info)
        analyzer.asset_info_list.append(dummy_asset_info)
        analyzer.initialize(MagicMock())
        analyzer.is_simulation = True
        analyzer.put_trading_info({"date_time": "2020-02-27T23:59:59"})
        # 유효하지 않은 정보 무시
        target_dummy_asset = {
            "balance": 50000,
            "asset": {
                "banana": (1500, 10),
                "mango": (1000, 4.5),
                "apple": (250, 2),
                "pineapple": (0, 2),
                "kiwi": (77700, 0),
            },
            "quote": {"banana": 2000, "mango": 1050, "apple": 400, "pineapple": 300, "kiwi": 77000},
            "date_time": "2020-02-27T23:59:59",
        }
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_list), 1)

        score_record = analyzer.score_list[0]
        self.assertEqual(score_record["balance"], 50000)
        self.assertEqual(score_record["cumulative_return"], 6.992)

        self.assertEqual(score_record["asset"][0][0], "banana")
        self.assertEqual(score_record["asset"][0][1], 1500)
        self.assertEqual(score_record["asset"][0][2], 2000)
        self.assertEqual(score_record["asset"][0][3], 10)
        self.assertEqual(score_record["asset"][0][4], 33.333)

        self.assertEqual(score_record["asset"][1][0], "mango")
        self.assertEqual(score_record["asset"][1][1], 1000)
        self.assertEqual(score_record["asset"][1][2], 1050)
        self.assertEqual(score_record["asset"][1][3], 4.5)
        self.assertEqual(score_record["asset"][1][4], 5)

        self.assertEqual(score_record["asset"][2][0], "apple")
        self.assertEqual(score_record["asset"][2][1], 250)
        self.assertEqual(score_record["asset"][2][2], 400)
        self.assertEqual(score_record["asset"][2][3], 2)
        self.assertEqual(score_record["asset"][2][4], 60)

        self.assertEqual(score_record["price_change_ratio"]["banana"], 17.647)
        self.assertEqual(score_record["price_change_ratio"]["mango"], 50)
        self.assertEqual(score_record["price_change_ratio"]["apple"], -20)
        self.assertEqual(score_record["date_time"], "2020-02-27T23:59:59")
        self.assertEqual(score_record["kind"], 3)
        analyzer.make_periodic_record.assert_called_once()

    def test_make_score_record_create_correct_score_record_when_asset_is_changed(self):
        analyzer = Analyzer()
        analyzer.make_periodic_record = MagicMock()
        dummy_asset_info = {
            "balance": 50000,
            "asset": {"banana": (1500, 10), "apple": (250, 2)},
            "quote": {"banana": 1700, "mango": 500, "apple": 500},
            "date_time": "2020-02-27T23:59:59",
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.update_start_point(dummy_asset_info)
        analyzer.asset_info_list.append(dummy_asset_info)
        target_dummy_asset = {
            "balance": 10000,
            "asset": {"mango": (1000, 7.5), "apple": (250, 10.7)},
            "quote": {"banana": 2000, "mango": 500, "apple": 800},
            "date_time": "2020-02-27T23:59:59",
        }
        analyzer.put_trading_info({"date_time": "2020-02-27T23:59:59"})
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_list), 1)

        score_record = analyzer.score_list[0]
        self.assertEqual(score_record["balance"], 10000)
        self.assertEqual(score_record["cumulative_return"], -67.191)

        self.assertEqual(score_record["asset"][0][0], "mango")
        self.assertEqual(score_record["asset"][0][1], 1000)
        self.assertEqual(score_record["asset"][0][2], 500)
        self.assertEqual(score_record["asset"][0][3], 7.5)
        self.assertEqual(score_record["asset"][0][4], -50)

        self.assertEqual(score_record["asset"][1][0], "apple")
        self.assertEqual(score_record["asset"][1][1], 250)
        self.assertEqual(score_record["asset"][1][2], 800)
        self.assertEqual(score_record["asset"][1][3], 10.7)
        self.assertEqual(score_record["asset"][1][4], 220)

        self.assertEqual(score_record["price_change_ratio"]["mango"], 0)
        self.assertEqual(score_record["price_change_ratio"]["apple"], 60)
        analyzer.make_periodic_record.assert_called_once()

    def test_make_score_record_create_correct_score_record_when_start_asset_is_empty(self):
        analyzer = Analyzer()
        analyzer.make_periodic_record = MagicMock()
        dummy_asset_info = {
            "balance": 23456,
            "asset": {},
            "quote": {"banana": 1700, "mango": 300, "apple": 500},
            "date_time": "2020-02-27T23:59:59",
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.update_start_point(dummy_asset_info)
        analyzer.asset_info_list.append(dummy_asset_info)

        target_dummy_asset = {
            "balance": 5000,
            "asset": {"mango": (500, 5.23), "apple": (250, 2.11)},
            "quote": {"banana": 2000, "mango": 300, "apple": 750},
            "date_time": "2020-02-27T23:59:59",
        }
        analyzer.put_trading_info({"date_time": "2020-02-27T23:59:59"})
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_list), 1)

        score_record = analyzer.score_list[0]
        self.assertEqual(score_record["balance"], 5000)
        self.assertEqual(score_record["cumulative_return"], -65.248)

        self.assertEqual(score_record["asset"][0][0], "mango")
        self.assertEqual(score_record["asset"][0][1], 500)
        self.assertEqual(score_record["asset"][0][2], 300)
        self.assertEqual(score_record["asset"][0][3], 5.23)
        self.assertEqual(score_record["asset"][0][4], -40)

        self.assertEqual(score_record["asset"][1][0], "apple")
        self.assertEqual(score_record["asset"][1][1], 250)
        self.assertEqual(score_record["asset"][1][2], 750)
        self.assertEqual(score_record["asset"][1][3], 2.11)
        self.assertEqual(score_record["asset"][1][4], 200)

        self.assertEqual(score_record["price_change_ratio"]["mango"], 0)
        self.assertEqual(score_record["price_change_ratio"]["apple"], 50)
        analyzer.make_periodic_record.assert_called_once()

    def test_make_score_record_create_correct_score_record_when_asset_and_balance_is_NOT_changed(
        self,
    ):
        analyzer = Analyzer()
        dummy_asset_info = {
            "balance": 1000,
            "asset": {},
            "quote": {"apple": 500},
            "date_time": "2020-02-27T23:59:59",
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.start_asset_info = dummy_asset_info
        analyzer.asset_info_list.append(dummy_asset_info)

        target_dummy_asset = {
            "balance": 1000,
            "asset": {},
            "quote": {"apple": 750},
            "date_time": "2020-02-27T23:59:59",
        }
        analyzer.make_periodic_record = MagicMock()
        analyzer.put_trading_info({"date_time": "2020-02-27T23:59:59"})
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_list), 1)

        score_record = analyzer.score_list[0]
        self.assertEqual(score_record["balance"], 1000)
        self.assertEqual(score_record["cumulative_return"], 0)

        self.assertEqual(len(score_record["asset"]), 0)
        self.assertEqual(len(score_record["price_change_ratio"].keys()), 0)
        analyzer.make_periodic_record.assert_called_once()

    def fill_test_data_for_report(self, analyzer):
        dummy_info = {
            "market": "orange",
            "date_time": "2020-02-23T00:00:00",
            "opening_price": 5000,
            "high_price": 15000,
            "low_price": 4500,
            "closing_price": 5500,
            "acc_price": 1500000000,
            "acc_volume": 1500,
            "kind": 0,
        }
        analyzer.info_list.append(dummy_info)

        dummy_request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 5000,
            "amount": 1,
            "date_time": "2020-02-23T00:00:00",
            "kind": 1,
        }
        analyzer.request_list.append(dummy_request)

        dummy_result = {
            "request": {"id": "1607862457.560075"},
            "type": "buy",
            "price": 5000,
            "amount": 0.5,
            "msg": "success",
            "date_time": "2020-02-23T00:00:00",
            "kind": 2,
        }
        analyzer.result_list.append(dummy_result)

        dummy_spot = {
            "value": 5900,
            "date_time": "2020-02-23T00:00:00",
        }
        analyzer.spot_list.append(dummy_spot)

        dummy_spot2 = {
            "value": 6900,
            "date_time": "2020-02-23T00:00:01",
        }
        analyzer.spot_list.append(dummy_spot2)

        dummy_asset_info = {
            "balance": 23456,
            "asset": {},
            "date_time": "2020-02-23T00:00:00",
            "quote": {"banana": 1700, "mango": 600, "apple": 500},
        }
        analyzer.asset_info_list.append(dummy_asset_info)
        analyzer.start_asset_info = dummy_asset_info
        target_dummy_asset = {
            "balance": 5000,
            "asset": {"mango": (500, 5.23), "apple": (250, 2.11)},
            "quote": {"banana": 2000, "mango": 300, "apple": 750},
            "date_time": "2020-02-23T00:01:00",
        }
        analyzer.asset_info_list.append(target_dummy_asset)
        analyzer.score_list.append(
            {
                "balance": 5000,
                "cumulative_return": -65.248,
                "price_change_ratio": {"mango": -50.0, "apple": 50.0},
                "asset": [("mango", 500, 300, 5.23, -40.0), ("apple", 250, 750, 2.11, 200.0)],
                "date_time": "2020-02-23T00:00:00",
                "kind": 3,
            }
        )

        dummy_info2 = {
            "market": "orange",
            "date_time": "2020-02-23T00:01:00",
            "opening_price": 5500,
            "high_price": 19000,
            "low_price": 4900,
            "closing_price": 8000,
            "acc_price": 15000000,
            "acc_volume": 15000,
            "kind": 0,
        }
        analyzer.info_list.append(dummy_info2)

        dummy_request2 = {
            "id": "1607862457.560075",
            "type": "sell",
            "price": 6000,
            "amount": 0.5,
            "date_time": "2020-02-23T00:01:00",
            "kind": 1,
        }
        analyzer.request_list.append(dummy_request2)

        dummy_result2 = {
            "request": {"id": "1607862457.560075"},
            "type": "buy",
            "price": 5000,
            "amount": 0.5,
            "msg": "success",
            "date_time": "2020-02-23T00:00:05",
            "kind": 2,
        }
        analyzer.result_list.append(dummy_result2)

        dummy_result3 = {
            "request": {"id": "1607862457.560075"},
            "type": "sell",
            "price": 6000,
            "amount": 0.2,
            "msg": "success",
            "date_time": "2020-02-23T00:01:00",
            "kind": 2,
        }
        analyzer.result_list.append(dummy_result3)

        dummy_spot3 = {
            "value": 8888,
            "date_time": "2020-02-23T00:02:00",
        }
        analyzer.spot_list.append(dummy_spot3)

        dummy_spot4 = {
            "value": 9999,
            "date_time": "2020-02-23T00:01:00",
        }
        analyzer.spot_list.append(dummy_spot4)

        target_dummy_asset2 = {
            "balance": 5000,
            "asset": {"mango": (600, 4.23), "apple": (500, 3.11)},
            "quote": {"banana": 3000, "mango": 200, "apple": 0.750},
            "date_time": "2020-02-23T00:01:00",
        }
        analyzer.asset_info_list.append(target_dummy_asset2)
        analyzer.score_list.append(
            {
                "balance": 5000,
                "cumulative_return": -75.067,
                "price_change_ratio": {"mango": -66.667, "apple": -99.85},
                "asset": [("mango", 600, 200, 4.23, -66.667), ("apple", 500, 0.75, 3.11, -99.85)],
                "date_time": "2020-02-23T00:01:00",
                "kind": 3,
            }
        )

        dummy_info3 = {
            "market": "orange",
            "date_time": "2020-02-23T00:02:00",
            "opening_price": 5500,
            "high_price": 19000,
            "low_price": 4900,
            "closing_price": 8000,
            "acc_price": 15000000,
            "acc_volume": 15000,
            "kind": 0,
        }
        analyzer.info_list.append(dummy_info3)

        return (
            dummy_info,
            dummy_request,
            dummy_result,
            target_dummy_asset,
            dummy_info2,
            dummy_request2,
            dummy_result2,
            target_dummy_asset2,
            dummy_result3,
        )

    def test_get_return_report_return_correct_report(self):
        """
        {
            cumulative_return: 기준 시점부터 누적 수익률
            price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
            asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
            date_time: 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간 +3초
            graph: 그래프 파일 패스
        }
        """
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.is_simulation = True
        self.fill_test_data_for_report(analyzer)
        analyzer.update_asset_info = MagicMock()

        report = analyzer.get_return_report()

        self.assertEqual(len(report), 9)
        # 입금 자산
        self.assertEqual(report[0], 23456)
        # 최종 자산
        self.assertEqual(report[1], 5848)
        # 누적 수익률
        self.assertEqual(report[2], -75.067)
        # 가격 변동률
        self.assertEqual(report[3]["mango"], -66.667)
        self.assertEqual(report[3]["apple"], -99.85)

        self.assertEqual(report[4], None)
        self.assertEqual(report[5], "2020-02-23T00:00:00 - 2020-02-23T00:02:00")
        # 최저/최대 수익률
        self.assertEqual(report[6], -75.067)
        self.assertEqual(report[7], -65.248)
        self.assertEqual(
            report[8], ("2020-02-23T00:00:00", "2020-02-23T00:00:00", "2020-02-23T00:02:00")
        )

        analyzer.update_asset_info.assert_called_once()

    @patch("mplfinance.plot")
    def test_get_return_report_return_correct_report_with_index(self, mock_plot):
        """
        {
            cumulative_return: 기준 시점부터 누적 수익률
            price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
            asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
            date_time: 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간 +3초
            graph: 그래프 파일 패스
        }
        """
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.is_simulation = True
        self.fill_test_data_for_report_10(analyzer)
        analyzer.update_asset_info = MagicMock()
        report = analyzer.get_return_report(index_info=(3, -3))

        self.assertEqual(len(report), 9)
        # 입금 자산
        self.assertEqual(report[0], 100016)
        # 최종 자산
        self.assertEqual(report[1], 100093)
        # 누적 수익률
        self.assertEqual(report[2], 0.093)
        # 가격 변동률
        self.assertEqual(report[3]["KRW-BTC"], 0.236)
        self.assertEqual(report[4], None)
        self.assertEqual(report[5], "2020-04-30T05:51:00 - 2020-04-30T05:53:00")
        # 최저/최대 수익률
        self.assertEqual(report[6], 0.016)
        self.assertEqual(report[7], 0.093)
        # 시간 정보
        self.assertEqual(
            report[8], ("2020-04-30T05:50:00", "2020-04-30T05:51:00", "2020-04-30T05:53:00")
        )

        report = analyzer.get_return_report(index_info=(3, 2))

        self.assertEqual(len(report), 9)
        # 입금 자산
        self.assertEqual(report[0], 100197)
        # 최종 자산
        self.assertEqual(report[1], 100197)
        # 누적 수익률
        self.assertEqual(report[2], 0.197)
        # 가격 변동률
        self.assertEqual(report[3]["KRW-BTC"], 0.396)
        self.assertEqual(report[4], None)
        self.assertEqual(report[5], "2020-04-30T05:56:00 - 2020-04-30T05:58:00")
        # 최저/최대 수익률
        self.assertEqual(report[6], 0.197)
        self.assertEqual(report[7], 0.197)
        # 시간 정보
        self.assertEqual(
            report[8], ("2020-04-30T05:50:00", "2020-04-30T05:56:00", "2020-04-30T05:58:00")
        )

        report = analyzer.get_return_report(graph_filename="mango_graph.png", index_info=(3, -1))

        self.assertEqual(len(report), 9)
        # 입금 자산
        self.assertEqual(report[0], 100197)
        # 최종 자산
        self.assertEqual(report[1], 100413)
        # 누적 수익률
        self.assertEqual(report[2], 0.413)
        # 가격 변동률
        self.assertEqual(report[3]["KRW-BTC"], 0.613)
        self.assertEqual(report[4], "mango_graph.png")
        self.assertEqual(report[5], "2020-04-30T05:57:00 - 2020-04-30T05:59:00")
        # 최저/최대 수익률
        self.assertEqual(report[6], 0.197)
        self.assertEqual(report[7], 0.413)
        # 시간 정보
        self.assertEqual(
            report[8], ("2020-04-30T05:50:00", "2020-04-30T05:57:00", "2020-04-30T05:59:00")
        )

        analyzer.update_asset_info.assert_called()

    @patch("mplfinance.make_addplot")
    @patch("mplfinance.plot")
    def test_get_return_report_draw_graph_when_graph_filename_exist(self, mock_plot, mock_addplot):
        """
        {
            cumulative_return: 기준 시점부터 누적 수익률
            price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
            asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
            date_time: 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간 +3초
            graph: 그래프 파일 패스
        }
        """
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.is_simulation = True
        self.fill_test_data_for_report(analyzer)
        analyzer.update_asset_info = MagicMock()
        report = analyzer.get_return_report("mango_graph.png")

        self.assertEqual(len(report), 9)
        # 입금 자산
        self.assertEqual(report[0], 23456)
        # 최종 자산
        self.assertEqual(report[1], 5848)
        # 누적 수익률
        self.assertEqual(report[2], -75.067)
        # 가격 변동률
        self.assertEqual(report[3]["mango"], -66.667)
        self.assertEqual(report[3]["apple"], -99.85)

        self.assertEqual(report[4], "mango_graph.png")
        self.assertEqual(report[5], "2020-02-23T00:00:00 - 2020-02-23T00:02:00")

        # 최저/최대 수익률
        self.assertEqual(report[6], -75.067)
        self.assertEqual(report[7], -65.248)
        # 시간 정보
        self.assertEqual(
            report[8], ("2020-02-23T00:00:00", "2020-02-23T00:00:00", "2020-02-23T00:02:00")
        )

        analyzer.update_asset_info.assert_called_once()
        mock_plot.assert_called_once_with(
            ANY,
            type="candle",
            volume=True,
            addplot=ANY,
            mav=analyzer.sma_info,
            style="starsandstripes",
            savefig=dict(fname="mango_graph.png", dpi=300, pad_inches=0.25),
            figscale=1.25,
        )
        self.assertEqual(len(mock_addplot.call_args_list), 5)
        self.assertEqual(mock_addplot.call_args_list[0][1]["type"], "scatter")
        self.assertEqual(mock_addplot.call_args_list[0][1]["markersize"], 100)
        self.assertEqual(mock_addplot.call_args_list[0][1]["marker"], "^")
        self.assertEqual(mock_addplot.call_args_list[1][1]["type"], "scatter")
        self.assertEqual(mock_addplot.call_args_list[1][1]["markersize"], 100)
        self.assertEqual(mock_addplot.call_args_list[1][1]["marker"], "v")
        self.assertEqual(mock_addplot.call_args_list[3][1]["panel"], 1)
        self.assertEqual(mock_addplot.call_args_list[3][1]["color"], "g")
        self.assertEqual(mock_addplot.call_args_list[3][1]["secondary_y"], True)
        self.assertEqual(mock_addplot.call_args_list[4][1]["type"], "scatter")
        self.assertEqual(mock_addplot.call_args_list[4][1]["markersize"], 50)
        self.assertEqual(mock_addplot.call_args_list[4][1]["marker"], ".")
        self.assertEqual(mock_addplot.call_args_list[0][0][0][0], 5000)
        self.assertEqual(mock_addplot.call_args_list[0][0][0][1], 5000)
        self.assertEqual(mock_addplot.call_args_list[1][0][0][1], 6000.0)
        self.assertEqual(mock_addplot.call_args_list[2][0][0][0], 500)
        self.assertEqual(mock_addplot.call_args_list[2][0][0][1], 600)
        self.assertEqual(mock_addplot.call_args_list[3][0][0][0], -65.248)
        self.assertEqual(mock_addplot.call_args_list[3][0][0][1], -75.067)
        self.assertEqual(mock_addplot.call_args_list[4][0][0][0], 5900)
        self.assertEqual(mock_addplot.call_args_list[4][0][0][1], 9999)
        self.assertEqual(mock_addplot.call_args_list[4][0][0][2], 8888)

    @patch("pandas.to_datetime")
    @patch("pandas.DataFrame")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_return_correct_report(
        self, mock_file, mock_plot, mock_DataFrame, mock_to_datetime
    ):
        """
        {
            "summary": (
                start_budget: 시작 자산
                final_balance: 최종 자산
                cumulative_return : 기준 시점부터 누적 수익률
                price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
                graph: 그래프 파일 패스
            ),
            "trading_table" : [
                {
                    "date_time": 생성 시간, 정렬 기준 값
                    거래 정보, 매매 요청 및 결과 정보, 수익률 정보 딕셔너리
                }
            ]
        }
        """
        analyzer = Analyzer()
        analyzer._get_rss_memory = MagicMock(return_value=123.45678)
        analyzer.initialize("mango")
        analyzer.is_simulation = True
        analyzer.update_asset_info = MagicMock()

        dummy_data = self.fill_test_data_for_report(analyzer)

        report = analyzer.create_report("apple")
        expected_info = copy.deepcopy(dummy_data[0])
        expected_info["kind"] = 0
        expected_request = copy.deepcopy(dummy_data[1])
        expected_request["kind"] = 1
        expected_result = copy.deepcopy(dummy_data[2])
        expected_result["kind"] = 2
        expected_info2 = copy.deepcopy(dummy_data[4])
        expected_info2["kind"] = 0
        expected_request2 = copy.deepcopy(dummy_data[5])
        expected_request2["kind"] = 1
        expected_result2 = copy.deepcopy(dummy_data[6])
        expected_result2["kind"] = 2
        expected_result3 = copy.deepcopy(dummy_data[8])
        expected_result3["kind"] = 2
        expected_info3 = copy.deepcopy(dummy_data[4])
        expected_info3["kind"] = 0
        expected_info3["date_time"] = "2020-02-23T00:02:00"
        expected_return1 = {
            "balance": 5000,
            "cumulative_return": -65.248,
            "price_change_ratio": {"mango": -50.0, "apple": 50.0},
            "asset": [("mango", 500, 300, 5.23, -40.0), ("apple", 250, 750, 2.11, 200.0)],
            "date_time": "2020-02-23T00:00:00",
            "kind": 3,
        }
        expected_return2 = {
            "balance": 5000,
            "cumulative_return": -75.067,
            "price_change_ratio": {"mango": -66.667, "apple": -99.85},
            "asset": [("mango", 600, 200, 4.23, -66.667), ("apple", 500, 0.75, 3.11, -99.85)],
            "date_time": "2020-02-23T00:01:00",
            "kind": 3,
        }

        self.assertEqual(len(report["trading_table"]), 10)
        self.assertEqual(report["trading_table"][0], expected_info)
        self.assertEqual(report["trading_table"][1], expected_request)
        self.assertEqual(report["trading_table"][2], expected_result)
        self.assertEqual(report["trading_table"][3], expected_return1)
        self.assertEqual(report["trading_table"][4], expected_result2)
        self.assertEqual(report["trading_table"][5], expected_info2)
        self.assertEqual(report["trading_table"][6], expected_request2)
        self.assertEqual(report["trading_table"][7], expected_result3)
        self.assertEqual(report["trading_table"][8], expected_return2)
        self.assertEqual(report["trading_table"][9], expected_info3)

        # 입금 자산, 최종 자산, 누적 수익률, 가격 변동률을 포함한다
        # (
        #     start_budget: 시작 자산
        #     final_balance: 최종 자산
        #     cumulative_return: 기준 시점부터 누적 수익률
        #     price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
        #     graph: 그래프 파일 패스
        #     period: 수익률 산출 구간
        #     return_high: 기간내 최고 수익률
        #     return_low: 기간내 최저 수익률
        # )
        self.assertEqual(len(report["summary"]), 9)

        # 입금 자산
        self.assertEqual(report["summary"][0], 23456)

        # 최종 자산
        self.assertEqual(report["summary"][1], 5848)

        # 누적 수익률
        self.assertEqual(report["summary"][2], -75.067)

        # 가격 변동률
        self.assertEqual(report["summary"][3]["mango"], -66.667)
        self.assertEqual(report["summary"][3]["apple"], -99.85)

        self.assertEqual(report["summary"][3]["apple"], -99.85)

        self.assertEqual(report["summary"][4], None)
        self.assertEqual(report["summary"][5], "2020-02-23T00:00:00 - 2020-02-23T00:02:00")
        self.assertEqual(report["summary"][6], -75.067)
        self.assertEqual(report["summary"][7], -65.248)
        # 시간 정보
        self.assertEqual(
            report["summary"][8],
            ("2020-02-23T00:00:00", "2020-02-23T00:00:00", "2020-02-23T00:02:00"),
        )
        analyzer._get_rss_memory.assert_called_once()

    @patch("mplfinance.plot")
    def test_create_report_call_update_info_func_with_asset_type_and_callback(self, mock_plot):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()
        analyzer.create_report()
        analyzer.update_asset_info.assert_called_once()

    @patch("pandas.to_datetime")
    @patch("pandas.DataFrame")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_create_correct_report_file(
        self, mock_file, mock_plot, mock_DataFrame, mock_to_datetime
    ):
        analyzer = Analyzer()
        analyzer._get_rss_memory = MagicMock(return_value=123.45678)
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()

        self.fill_test_data_for_report(analyzer)

        tag = "orange"
        filename = "mango"
        report = analyzer.create_report()
        mock_file.assert_called_with(analyzer.OUTPUT_FOLDER + "untitled-report.txt", "w")
        handle = mock_file()
        expected = [
            "### TRADING TABLE =================================\n",
            "2020-02-23T00:00:00, 5000, 15000, 4500, 5500, 1500000000, 1500\n",
            "2020-02-23T00:00:00, [->] 1607862457.560075, buy, 5000, 1\n",
            "2020-02-23T00:00:00, [<-] 1607862457.560075, buy, 5000, 0.5, success\n",
            "2020-02-23T00:00:00, [#] 5000, -65.248, {'mango': -50.0, 'apple': 50.0}, [('mango', 500, 300, 5.23, -40.0), ('apple', 250, 750, 2.11, 200.0)]\n",
            "2020-02-23T00:00:05, [<-] 1607862457.560075, buy, 5000, 0.5, success\n",
            "2020-02-23T00:01:00, 5500, 19000, 4900, 8000, 15000000, 15000\n",
            "2020-02-23T00:01:00, [->] 1607862457.560075, sell, 6000, 0.5\n",
            "2020-02-23T00:01:00, [<-] 1607862457.560075, sell, 6000, 0.2, success\n",
            "2020-02-23T00:01:00, [#] 5000, -75.067, {'mango': -66.667, 'apple': -99.85}, [('mango', 600, 200, 4.23, -66.667), ('apple', 500, 0.75, 3.11, -99.85)]\n",
            "2020-02-23T00:02:00, 5500, 19000, 4900, 8000, 15000000, 15000\n",
            "### SUMMARY =======================================\n",
            "Property                      23456 ->       5848\n",
            "Gap                                        -17608\n",
            "Cumulative return                       -75.067 %\n",
            "Price_change_ratio {'mango': -66.667, 'apple': -99.85}\n",
        ]

        for idx, val in enumerate(expected):
            self.assertEqual(
                handle.write.call_args_list[idx][0][0],
                val,
            )

        report = analyzer.create_report(tag=tag)
        mock_file.assert_called_with(analyzer.OUTPUT_FOLDER + tag + ".txt", "w")

        analyzer.update_asset_info.assert_called()
        analyzer._get_rss_memory.assert_called()

    @patch("mplfinance.make_addplot")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_draw_correct_graph(self, mock_file, mock_plot, mock_make_addplot):
        analyzer = Analyzer()
        analyzer._get_rss_memory = MagicMock(return_value=123.45678)
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()
        filename = "apple"

        self.fill_test_data_for_report(analyzer)
        analyzer.create_report(filename)

        self.assertEqual(
            mock_make_addplot.call_args_list[0][1],
            {"type": "scatter", "markersize": 100, "marker": "^"},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[1][1],
            {"type": "scatter", "markersize": 100, "marker": "v"},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[3][1],
            {"panel": 1, "color": "g", "secondary_y": True},
        )

        mock_plot.assert_called_once_with(
            ANY,
            type="candle",
            volume=True,
            addplot=ANY,
            mav=analyzer.sma_info,
            style="starsandstripes",
            savefig=dict(
                fname=analyzer.OUTPUT_FOLDER + filename + ".jpg", dpi=300, pad_inches=0.25
            ),
            figscale=1.25,
        )
        analyzer.update_asset_info.assert_called_once()
        analyzer._get_rss_memory.assert_called_once()

    @patch("mplfinance.make_addplot")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_draw_correct_graph_when_rsi_enabled(
        self, mock_file, mock_plot, mock_make_addplot
    ):
        analyzer = Analyzer()
        analyzer.RSI_ENABLE = True
        analyzer.RSI = (30, 70, 2)
        analyzer._get_rss_memory = MagicMock(return_value=123.45678)
        analyzer.initialize("mango")
        analyzer.update_asset_info = MagicMock()
        filename = "apple"

        self.fill_test_data_for_report(analyzer)
        analyzer.create_report(filename)

        self.assertEqual(
            mock_make_addplot.call_args_list[0][1],
            {"panel": 2, "color": "lime", "ylim": (10, 90), "secondary_y": False},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[1][1],
            {"panel": 2, "color": "red", "width": 0.5, "secondary_y": False},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[2][1],
            {"panel": 2, "color": "red", "width": 0.5, "secondary_y": False},
        )

        mock_plot.assert_called_once_with(
            ANY,
            type="candle",
            volume=True,
            addplot=ANY,
            mav=analyzer.sma_info,
            style="starsandstripes",
            savefig=dict(
                fname=analyzer.OUTPUT_FOLDER + filename + ".jpg", dpi=300, pad_inches=0.25
            ),
            figscale=1.25,
        )
        analyzer.update_asset_info.assert_called_once()
        analyzer._get_rss_memory.assert_called_once()

    def test_make_rsi_return_correct_rsi(self):
        prices = [
            26026000.0,
            26075000.0,
            26051000.0,
            26039000.0,
            26007000.0,
            25981000.0,
            26004000.0,
            26020000.0,
            25997000.0,
            25981000.0,
            26002000.0,
            26002000.0,
            25970000.0,
            25940000.0,
            25924000.0,
        ]
        expected = [
            34.27,
            34.27,
            34.27,
            34.27,
            34.27,
            34.27,
            45.27,
            52.22,
            42.52,
            36.6,
            48.38,
            48.38,
            33.54,
            24.67,
            20.97,
        ]
        rsi = Analyzer.make_rsi(prices, count=5)
        for i in range(len(rsi)):
            self.assertAlmostEqual(rsi[i], expected[i], 2)

    def test_get_trading_results_return_result(self):
        analyzer = Analyzer()
        analyzer.result_list = "mango"
        self.assertEqual(analyzer.get_trading_results(), "mango")

    def fill_test_data_for_report_10(self, analyzer):
        analyzer.info_list = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:50:00",
                "opening_price": 10591000.0,
                "high_price": 10605000.0,
                "low_price": 10591000.0,
                "closing_price": 10605000.0,
                "acc_price": 116316536.37072,
                "acc_volume": 10.97288124,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:51:00",
                "opening_price": 10608000.0,
                "high_price": 10611000.0,
                "low_price": 10596000.0,
                "closing_price": 10598000.0,
                "acc_price": 132749879.7377,
                "acc_volume": 12.52234496,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:52:00",
                "opening_price": 10598000.0,
                "high_price": 10611000.0,
                "low_price": 10596000.0,
                "closing_price": 10611000.0,
                "acc_price": 59612254.02454,
                "acc_volume": 5.6232814,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:53:00",
                "opening_price": 10612000.0,
                "high_price": 10622000.0,
                "low_price": 10612000.0,
                "closing_price": 10622000.0,
                "acc_price": 50830798.21126,
                "acc_volume": 4.78835739,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:54:00",
                "opening_price": 10617000.0,
                "high_price": 10630000.0,
                "low_price": 10617000.0,
                "closing_price": 10630000.0,
                "acc_price": 82005173.84158,
                "acc_volume": 7.71635194,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:55:00",
                "opening_price": 10630000.0,
                "high_price": 10650000.0,
                "low_price": 10630000.0,
                "closing_price": 10650000.0,
                "acc_price": 99752483.10131,
                "acc_volume": 9.37410465,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:56:00",
                "opening_price": 10646000.0,
                "high_price": 10657000.0,
                "low_price": 10646000.0,
                "closing_price": 10646000.0,
                "acc_price": 328379382.72467,
                "acc_volume": 30.83367158,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:57:00",
                "opening_price": 10646000.0,
                "high_price": 10650000.0,
                "low_price": 10645000.0,
                "closing_price": 10647000.0,
                "acc_price": 51564466.13633,
                "acc_volume": 4.84241397,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:58:00",
                "opening_price": 10646000.0,
                "high_price": 10669000.0,
                "low_price": 10646000.0,
                "closing_price": 10669000.0,
                "acc_price": 197890470.89159,
                "acc_volume": 18.56679051,
                "kind": 0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T05:59:00",
                "opening_price": 10669000.0,
                "high_price": 10671000.0,
                "low_price": 10666000.0,
                "closing_price": 10670000.0,
                "acc_price": 106676249.34666,
                "acc_volume": 9.99976792,
                "kind": 0,
            },
        ]
        analyzer.asset_info_list = [
            {
                "balance": 100000.0,
                "asset": {},
                "quote": {"KRW-BTC": 10605000.0},
                "date_time": "2020-04-30T05:50:00",
            },
            {
                "balance": 79840.0,
                "asset": {"KRW-BTC": (10605000.0, 0.0019)},
                "quote": {"KRW-BTC": 10598000.0},
                "date_time": "2020-04-30T05:50:00",
            },
            {
                "balance": 59694.0,
                "asset": {"KRW-BTC": (10601500, 0.0038)},
                "quote": {"KRW-BTC": 10611000.0},
                "date_time": "2020-04-30T05:51:00",
            },
            {
                "balance": 59694.0,
                "asset": {"KRW-BTC": (10601500, 0.0038)},
                "quote": {"KRW-BTC": 10622000.0},
                "date_time": "2020-04-30T05:53:00",
            },
            {
                "balance": 39502.0,
                "asset": {"KRW-BTC": (10608333, 0.0057)},
                "quote": {"KRW-BTC": 10630000.0},
                "date_time": "2020-04-30T05:53:00",
            },
            {
                "balance": 19295.0,
                "asset": {"KRW-BTC": (10613750, 0.0076)},
                "quote": {"KRW-BTC": 10650000.0},
                "date_time": "2020-04-30T05:54:00",
            },
            {
                "balance": 115.0,
                "asset": {"KRW-BTC": (10620691, 0.0094)},
                "quote": {"KRW-BTC": 10646000.0},
                "date_time": "2020-04-30T05:55:00",
            },
            {
                "balance": 115.0,
                "asset": {"KRW-BTC": (10620691, 0.0094)},
                "quote": {"KRW-BTC": 10647000.0},
                "date_time": "2020-04-30T05:57:00",
            },
            {
                "balance": 115.0,
                "asset": {"KRW-BTC": (10620691, 0.0094)},
                "quote": {"KRW-BTC": 10670000.0},
                "date_time": "2020-04-30T05:59:00",
            },
            {
                "balance": 115.0,
                "asset": {"KRW-BTC": (10620691, 0.0094)},
                "quote": {"KRW-BTC": 10576000.0},
                "date_time": "2020-04-30T06:01:00",
            },
        ]
        analyzer.score_list = [
            {
                "balance": 100000.0,
                "cumulative_return": 0,
                "price_change_ratio": {},
                "asset": [],
                "date_time": "2020-04-30T05:50:00",
                "kind": 3,
            },
            {
                "balance": 79840.0,
                "cumulative_return": -0.024,
                "price_change_ratio": {"KRW-BTC": -0.066},
                "asset": [("KRW-BTC", 10605000.0, 10598000.0, 0.0019, -0.066)],
                "date_time": "2020-04-30T05:50:00",
                "kind": 3,
            },
            {
                "balance": 59694.0,
                "cumulative_return": 0.016,
                "price_change_ratio": {"KRW-BTC": 0.057},
                "asset": [("KRW-BTC", 10601500.0, 10611000.0, 0.0038, 0.09)],
                "date_time": "2020-04-30T05:51:00",
                "kind": 3,
            },
            {
                "balance": 59694.0,
                "cumulative_return": 0.058,
                "price_change_ratio": {"KRW-BTC": 0.16},
                "asset": [("KRW-BTC", 10601500.0, 10622000.0, 0.0038, 0.193)],
                "date_time": "2020-04-30T05:53:00",
                "kind": 3,
            },
            {
                "balance": 39502.0,
                "cumulative_return": 0.093,
                "price_change_ratio": {"KRW-BTC": 0.236},
                "asset": [("KRW-BTC", 10608333.0, 10630000.0, 0.0057, 0.204)],
                "date_time": "2020-04-30T05:53:00",
                "kind": 3,
            },
            {
                "balance": 19295.0,
                "cumulative_return": 0.235,
                "price_change_ratio": {"KRW-BTC": 0.424},
                "asset": [("KRW-BTC", 10613750.0, 10650000.0, 0.0076, 0.342)],
                "date_time": "2020-04-30T05:54:00",
                "kind": 3,
            },
            {
                "balance": 115.0,
                "cumulative_return": 0.187,
                "price_change_ratio": {"KRW-BTC": 0.387},
                "asset": [("KRW-BTC", 10620691.0, 10646000.0, 0.0094, 0.238)],
                "date_time": "2020-04-30T05:55:00",
                "kind": 3,
            },
            {
                "balance": 115.0,
                "cumulative_return": 0.197,
                "price_change_ratio": {"KRW-BTC": 0.396},
                "asset": [("KRW-BTC", 10620691.0, 10647000.0, 0.0094, 0.248)],
                "date_time": "2020-04-30T05:57:00",
                "kind": 3,
            },
            {
                "balance": 115.0,
                "cumulative_return": 0.413,
                "price_change_ratio": {"KRW-BTC": 0.613},
                "asset": [("KRW-BTC", 10620691.0, 10670000.0, 0.0094, 0.464)],
                "date_time": "2020-04-30T05:59:00",
                "kind": 3,
            },
            {
                "balance": 115.0,
                "cumulative_return": -0.471,
                "price_change_ratio": {"KRW-BTC": -0.273},
                "asset": [("KRW-BTC", 10620691.0, 10576000.0, 0.0094, -0.421)],
                "date_time": "2020-04-30T06:01:00",
                "kind": 3,
            },
        ]
        analyzer.result_list = [
            {
                "request": {
                    "id": "1622473847.721",
                    "type": "buy",
                    "price": 10605000.0,
                    "amount": 0.0019,
                    "date_time": "2020-04-30T05:50:00",
                },
                "type": "buy",
                "price": 10605000.0,
                "amount": 0.0019,
                "msg": "success",
                "balance": 79840,
                "state": "done",
                "date_time": "2020-04-30T05:50:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1622473848.262",
                    "type": "buy",
                    "price": 10598000.0,
                    "amount": 0.0019,
                    "date_time": "2020-04-30T05:51:00",
                },
                "type": "buy",
                "price": 10598000.0,
                "amount": 0.0019,
                "msg": "success",
                "balance": 59694,
                "state": "done",
                "date_time": "2020-04-30T05:51:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1622473849.316",
                    "type": "buy",
                    "price": 10622000.0,
                    "amount": 0.0019,
                    "date_time": "2020-04-30T05:53:00",
                },
                "type": "buy",
                "price": 10622000.0,
                "amount": 0.0019,
                "msg": "success",
                "balance": 39502,
                "state": "done",
                "date_time": "2020-04-30T05:53:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1622473849.851",
                    "type": "buy",
                    "price": 10630000.0,
                    "amount": 0.0019,
                    "date_time": "2020-04-30T05:54:00",
                },
                "type": "buy",
                "price": 10630000.0,
                "amount": 0.0019,
                "msg": "success",
                "balance": 19295,
                "state": "done",
                "date_time": "2020-04-30T05:54:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1622473850.386",
                    "type": "buy",
                    "price": 10650000.0,
                    "amount": 0.0018,
                    "date_time": "2020-04-30T05:55:00",
                },
                "type": "buy",
                "price": 10650000.0,
                "amount": 0.0018,
                "msg": "success",
                "balance": 115,
                "state": "done",
                "date_time": "2020-04-30T05:55:00",
                "kind": 2,
            },
        ]
        analyzer.start_asset_info = analyzer.asset_info_list[0]

    @patch("builtins.open", new_callable=mock_open)
    def test__write_to_file_make_dumpfile_correctly(self, mock_file):
        analyzer = Analyzer()
        dummy_list = [{"mango": 500}, {"orange": 7.7}]
        analyzer._write_to_file("mango_dump_file", dummy_list)
        mock_file.assert_called_with("mango_dump_file", "w")
        handle = mock_file()
        expected = ["[\n", "{'mango': 500},\n", "{'orange': 7.7},\n", "]\n"]
        for idx, val in enumerate(expected):
            self.assertEqual(
                handle.write.call_args_list[idx][0][0],
                val,
            )

    @patch("builtins.open", new_callable=mock_open)
    def test__load_from_file_load_dumpfile_correctly(self, mock_file):
        analyzer = Analyzer()
        handle = mock_file()
        handle.read.return_value = "[ {'mango': 500}, {'orange': 7.7},]"
        dummy_list = analyzer._load_list_from_file("mango_dump_file")
        mock_file.assert_called_with("mango_dump_file")
        self.assertEqual(dummy_list, [{"mango": 500}, {"orange": 7.7}])

    def test_dump_call_should_call__write_to_file_correctly(self):
        analyzer = Analyzer()
        analyzer._write_to_file = MagicMock()
        analyzer.dump("mango")
        called = analyzer._write_to_file.call_args_list
        self.assertEqual(called[0][0][0], "mango.1")
        self.assertEqual(called[1][0][0], "mango.2")
        self.assertEqual(called[2][0][0], "mango.3")
        self.assertEqual(called[3][0][0], "mango.4")
        self.assertEqual(called[4][0][0], "mango.5")
        self.assertEqual(called[0][0][1], analyzer.request_list)
        self.assertEqual(called[1][0][1], analyzer.result_list)
        self.assertEqual(called[2][0][1], analyzer.info_list)
        self.assertEqual(called[3][0][1], analyzer.asset_info_list)
        self.assertEqual(called[4][0][1], analyzer.score_list)

    def test_load_dump_call_should_call__load_list_from_file_correctly(self):
        analyzer = Analyzer()
        analyzer._load_list_from_file = MagicMock(side_effect=["a", "b", "c", "d", "e"])
        analyzer.load_dump("mango")
        called = analyzer._load_list_from_file.call_args_list
        self.assertEqual(called[0][0][0], "mango.1")
        self.assertEqual(called[1][0][0], "mango.2")
        self.assertEqual(called[2][0][0], "mango.3")
        self.assertEqual(called[3][0][0], "mango.4")
        self.assertEqual(called[4][0][0], "mango.5")
        self.assertEqual(analyzer.request_list, "a")
        self.assertEqual(analyzer.result_list, "b")
        self.assertEqual(analyzer.info_list, "c")
        self.assertEqual(analyzer.asset_info_list, "d")
        self.assertEqual(analyzer.score_list, "e")

    def test__get_min_max_return_should_return_min_max_tuple(self):
        dummy = [
            {"cumulative_return": 1},
            {"cumulative_return": 2},
            {"cumulative_return": 3.6},
            {"cumulative_return": 4.55555555},
            {"cumulative_return": -21312},
        ]
        result = Analyzer._get_min_max_return(dummy)
        self.assertEqual(result[0], -21312)
        self.assertEqual(result[1], 4.55555555)
