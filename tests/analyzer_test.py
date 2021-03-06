import os
import copy
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
        dummy_request = {"id": "orange", "price": 5000, "amount": 1}
        analyzer.put_request(dummy_request)
        self.assertEqual(
            analyzer.request[-1], {"id": "orange", "price": 5000, "amount": 1, "kind": 1}
        )

        dummy_request = {"id": "banana", "price": 0, "amount": 1}
        analyzer.put_request(dummy_request)
        self.assertNotEqual(analyzer.request[-1], dummy_request)
        self.assertEqual(analyzer.request[-1]["id"], "orange")

        dummy_request = {"id": "apple", "price": 500, "amount": 0}
        analyzer.put_request(dummy_request)
        self.assertNotEqual(analyzer.request[-1], dummy_request)
        self.assertEqual(analyzer.request[-1]["id"], "orange")

        dummy_request = {"id": "kiwi", "price": 500, "amount": 0.0000000000000000000000001}
        analyzer.put_request(dummy_request)
        self.assertEqual(analyzer.request[-1]["id"], "kiwi")
        self.assertEqual(analyzer.request[-1]["price"], 500)
        self.assertEqual(analyzer.request[-1]["amount"], 0.0000000000000000000000001)
        self.assertEqual(analyzer.request[-1]["kind"], 1)

    def test_put_trading_info_append_trading_info(self):
        analyzer = Analyzer()
        dummy_info = {"name": "orange"}
        analyzer.put_trading_info(dummy_info)
        self.assertEqual(analyzer.infos[-1], {"name": "orange", "kind": 0})

    def test_put_result_append_only_success_result(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_info_func = MagicMock()

        dummy_result = {"request_id": "orange", "price": 5000, "amount": 1}
        analyzer.put_result(dummy_result)
        self.assertEqual(
            analyzer.result[-1], {"request_id": "orange", "price": 5000, "amount": 1, "kind": 2}
        )

        dummy_result = {"request_id": "banana", "price": 0, "amount": 1}
        analyzer.put_result(dummy_result)
        self.assertNotEqual(
            analyzer.result[-1], {"request_id": "banana", "price": 0, "amount": 1, "kind": 2}
        )
        self.assertEqual(analyzer.result[-1]["request_id"], "orange")

        dummy_result = {"request_id": "apple", "price": 500, "amount": 0}
        analyzer.put_result(dummy_result)
        self.assertNotEqual(analyzer.result[-1]["request_id"], "apple")
        self.assertNotEqual(analyzer.result[-1]["price"], 500)
        self.assertEqual(analyzer.result[-1]["request_id"], "orange")
        self.assertEqual(analyzer.result[-1]["kind"], 2)

        dummy_result = {"request_id": "kiwi", "price": 500, "amount": 0.0000000000000000000000001}
        analyzer.put_result(dummy_result)
        self.assertEqual(analyzer.result[-1]["request_id"], "kiwi")
        self.assertEqual(analyzer.result[-1]["price"], 500)
        self.assertEqual(analyzer.result[-1]["amount"], 0.0000000000000000000000001)
        self.assertEqual(analyzer.result[-1]["kind"], 2)

    def test_put_result_call_update_info_func_with_asset_type_and_callback(self):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_info_func = MagicMock()
        dummy_result = {"request_id": "banana", "price": 500, "amount": 0.0000000000000000000000001}
        analyzer.put_result(dummy_result)
        analyzer.update_info_func.assert_called_once_with("asset", analyzer.put_asset_info)

    def test_initialize_keep_update_info_func(self):
        analyzer = Analyzer()
        analyzer.initialize("mango", True)
        self.assertEqual(analyzer.update_info_func, "mango")
        self.assertEqual(analyzer.is_simulation, True)

    def test_put_asset_info_append_asset_info(self):
        analyzer = Analyzer()
        analyzer.make_score_record = MagicMock()
        analyzer.put_asset_info("apple")
        self.assertEqual(analyzer.asset_record_list[-1], "apple")

    def test_put_asset_info_should_call_make_score_record(self):
        analyzer = Analyzer()
        analyzer.make_score_record = MagicMock()
        analyzer.put_asset_info("apple")
        self.assertEqual(analyzer.asset_record_list[-1], "apple")
        analyzer.make_score_record.assert_called_once_with("apple")

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

    def test_make_score_record_create_correct_score_record_when_asset_is_not_changed(self):
        analyzer = Analyzer()
        dummy_asset_info = {
            "balance": 50000,
            "asset": {"banana": (1500, 10), "mango": (1000, 4.5), "apple": (250, 2)},
            "quote": {"banana": 1700, "mango": 700, "apple": 500},
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset_info)
        analyzer.initialize(MagicMock(), True)
        analyzer.put_trading_info({"date_time": "2020-02-27T23:59:59"})
        target_dummy_asset = {
            "balance": 50000,
            "asset": {"banana": (1500, 10), "mango": (1000, 4.5), "apple": (250, 2)},
            "quote": {"banana": 2000, "mango": 1050, "apple": 400},
        }
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_record_list), 1)

        score_record = analyzer.score_record_list[0]
        self.assertEqual(score_record["balance"], 50000)
        self.assertEqual(score_record["cumulative_return"], 6.149)

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

    def test_make_score_record_create_correct_score_record_when_asset_is_changed(self):
        analyzer = Analyzer()
        dummy_asset_info = {
            "balance": 50000,
            "asset": {"banana": (1500, 10), "apple": (250, 2)},
            "quote": {"banana": 1700, "mango": 500, "apple": 500},
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset_info)
        target_dummy_asset = {
            "balance": 10000,
            "asset": {"mango": (1000, 7.5), "apple": (250, 10.7)},
            "quote": {"banana": 2000, "mango": 500, "apple": 800},
        }
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_record_list), 1)

        score_record = analyzer.score_record_list[0]
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

    def test_make_score_record_create_correct_score_record_when_start_asset_is_empty(self):
        analyzer = Analyzer()
        dummy_asset_info = {
            "balance": 23456,
            "asset": {},
            "quote": {"banana": 1700, "mango": 300, "apple": 500},
        }

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset_info)

        target_dummy_asset = {
            "balance": 5000,
            "asset": {"mango": (500, 5.23), "apple": (250, 2.11)},
            "quote": {"banana": 2000, "mango": 300, "apple": 750},
        }
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_record_list), 1)

        score_record = analyzer.score_record_list[0]
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

    def test_make_score_record_create_correct_score_record_when_asset_and_balance_is_NOT_changed(
        self,
    ):
        analyzer = Analyzer()
        dummy_asset_info = {"balance": 1000, "asset": {}, "quote": {"apple": 500}}

        # 시작점을 생성하기 위해 초기 자산 정보 추가
        analyzer.asset_record_list.append(dummy_asset_info)

        target_dummy_asset = {"balance": 1000, "asset": {}, "quote": {"apple": 750}}
        analyzer.make_score_record(target_dummy_asset)
        self.assertEqual(len(analyzer.score_record_list), 1)

        score_record = analyzer.score_record_list[0]
        self.assertEqual(score_record["balance"], 1000)
        self.assertEqual(score_record["cumulative_return"], 0)

        self.assertEqual(len(score_record["asset"]), 0)
        self.assertEqual(len(score_record["price_change_ratio"].keys()), 0)

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
        }
        analyzer.put_trading_info(dummy_info)

        dummy_request = {
            "id": "1607862457.560075",
            "type": "buy",
            "price": 5000,
            "amount": 1,
            "date_time": "2020-02-23T00:00:00",
        }
        analyzer.put_request(dummy_request)

        dummy_result = {
            "request_id": "1607862457.560075",
            "type": "buy",
            "price": 5000,
            "amount": 1,
            "msg": "success",
            "balance": 30000,
            "date_time": "2020-02-23T00:00:00",
        }
        analyzer.put_result(dummy_result)

        dummy_asset_info = {
            "balance": 23456,
            "asset": {},
            "quote": {"banana": 1700, "mango": 600, "apple": 500},
        }
        analyzer.asset_record_list.append(dummy_asset_info)

        target_dummy_asset = {
            "balance": 5000,
            "asset": {"mango": (500, 5.23), "apple": (250, 2.11)},
            "quote": {"banana": 2000, "mango": 300, "apple": 750},
        }
        analyzer.put_asset_info(target_dummy_asset)

        dummy_info2 = {
            "market": "orange",
            "date_time": "2020-02-23T00:01:00",
            "opening_price": 5500,
            "high_price": 19000,
            "low_price": 4900,
            "closing_price": 8000,
            "acc_price": 15000000,
            "acc_volume": 15000,
        }
        analyzer.put_trading_info(dummy_info2)

        dummy_request2 = {
            "id": "1607862457.560075",
            "type": "sell",
            "price": 6000,
            "amount": 0.5,
            "date_time": "2020-02-23T00:01:00",
        }
        analyzer.put_request(dummy_request2)

        dummy_result2 = {
            "request_id": "1607862457.560075",
            "type": "sell",
            "price": 6000,
            "amount": 0.5,
            "msg": "success",
            "balance": 33000,
            "date_time": "2020-02-23T00:01:00",
        }
        analyzer.put_result(dummy_result2)

        target_dummy_asset2 = {
            "balance": 5000,
            "asset": {"mango": (600, 4.23), "apple": (500, 3.11)},
            "quote": {"banana": 3000, "mango": 200, "apple": 0.750},
        }
        analyzer.put_asset_info(target_dummy_asset2)
        return (
            dummy_info,
            dummy_request,
            dummy_result,
            target_dummy_asset,
            dummy_info2,
            dummy_request2,
            dummy_result2,
            target_dummy_asset2,
        )

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
                cumulative_return: 기준 시점부터 누적 수익률
                price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
                asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
                date_time: 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간 +3초
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
        analyzer.initialize("mango", True)
        analyzer.update_info_func = MagicMock()

        dummy_data = self.fill_test_data_for_report(analyzer)

        report = analyzer.create_report()
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

        self.assertEqual(len(report["trading_table"]), 8)
        self.assertEqual(report["trading_table"][0], expected_info)
        self.assertEqual(report["trading_table"][1], expected_request)
        self.assertEqual(report["trading_table"][2], expected_result)
        self.assertEqual(report["trading_table"][3], ANY)
        self.assertEqual(report["trading_table"][4], expected_info2)
        self.assertEqual(report["trading_table"][5], expected_request2)
        self.assertEqual(report["trading_table"][6], expected_result2)
        self.assertEqual(report["trading_table"][7], ANY)

        # 입금 자산, 최종 자산, 누적 수익률, 가격 변동률을 포함한다
        self.assertEqual(len(report["summary"]), 4)

        # 입금 자산
        self.assertEqual(report["summary"][0], 23456)

        # 최종 자산
        # mango 300 * 5.23 = 1569, apple 750 * 2.11 = 1582.5, balance 5000
        self.assertEqual(report["summary"][1], 5848)

        # 누적 수익률
        # (8151.5 - 23456) / 23456 * 100 = -65.248
        self.assertEqual(report["summary"][2], -75.067)

        # 가격 변동률
        self.assertEqual(report["summary"][3]["mango"], -66.667)
        self.assertEqual(report["summary"][3]["apple"], -99.85)

    @patch("mplfinance.plot")
    def test_create_report_call_update_info_func_with_asset_type_and_callback(self, mock_plot):
        analyzer = Analyzer()
        analyzer.initialize("mango")
        analyzer.update_info_func = MagicMock()
        analyzer.create_report()
        analyzer.update_info_func.assert_called_once_with("asset", analyzer.put_asset_info)

    @patch("pandas.to_datetime")
    @patch("pandas.DataFrame")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_create_correct_report_file(
        self, mock_file, mock_plot, mock_DataFrame, mock_to_datetime
    ):
        analyzer = Analyzer()
        analyzer.initialize("mango", True)
        analyzer.update_info_func = MagicMock()

        self.fill_test_data_for_report(analyzer)

        filename = "mango"
        report = analyzer.create_report(filename)
        mock_file.assert_called_once_with(filename, "w")
        handle = mock_file()
        expected = [
            "### TRADING TABLE =================================\n",
            "2020-02-23T00:00:00, 5000, 15000, 4500, 5500, 1500000000, 1500\n",
            "2020-02-23T00:00:00, [->] 1607862457.560075, buy, 5000, 1\n",
            "2020-02-23T00:00:00, [<-] 1607862457.560075, buy, 5000, 1, success, 30000\n",
            "2020-02-23T00:00:00, [#] 5000, -65.248, {'mango': -50.0, 'apple': 50.0}, [('mango', 500, 300, 5.23, -40.0), ('apple', 250, 750, 2.11, 200.0)]\n",
            "2020-02-23T00:01:00, 5500, 19000, 4900, 8000, 15000000, 15000\n",
            "2020-02-23T00:01:00, [->] 1607862457.560075, sell, 6000, 0.5\n",
            "2020-02-23T00:01:00, [<-] 1607862457.560075, sell, 6000, 0.5, success, 33000\n",
            "2020-02-23T00:01:00, [#] 5000, -75.067, {'mango': -66.667, 'apple': -99.85}, [('mango', 600, 200, 4.23, -66.667), ('apple', 500, 0.75, 3.11, -99.85)]\n",
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

    @patch("mplfinance.make_addplot")
    @patch("pandas.to_datetime")
    @patch("pandas.DataFrame")
    @patch("mplfinance.plot")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_report_draw_correct_graph(
        self, mock_file, mock_plot, mock_DataFrame, mock_to_datetime, mock_make_addplot
    ):
        class DummyDataFrame:
            def __init__(self):
                self.index = "mango"
                self.columns = {
                    "buy": "orange",
                    "sell": "apple",
                    "avr_price": "banana",
                    "return": "kiwi",
                }
                self.rename = MagicMock(return_value=self)
                self.set_index = MagicMock(return_value=self)

            def __getitem__(self, item):
                return self.columns[item]

        dummyDataFrame = DummyDataFrame()
        mock_DataFrame.return_value = dummyDataFrame
        analyzer = Analyzer()
        analyzer.initialize("mango", True)
        analyzer.update_info_func = MagicMock()

        dummy_data = self.fill_test_data_for_report(analyzer)
        analyzer.create_report()

        mock_DataFrame.assert_called_once_with(
            [
                {
                    "market": "orange",
                    "date_time": "2020-02-23T00:00:00",
                    "opening_price": 5000,
                    "high_price": 15000,
                    "low_price": 4500,
                    "closing_price": 5500,
                    "acc_price": 1500000000,
                    "acc_volume": 1500,
                    "kind": 0,
                    "buy": 5000,
                    "return": -65.248,
                    "avr_price": 500,
                },
                {
                    "market": "orange",
                    "date_time": "2020-02-23T00:01:00",
                    "opening_price": 5500,
                    "high_price": 19000,
                    "low_price": 4900,
                    "closing_price": 8000,
                    "acc_price": 15000000,
                    "acc_volume": 15000,
                    "kind": 0,
                    "sell": 6000,
                    "return": -75.067,
                    "avr_price": 600,
                },
            ]
        )
        dummyDataFrame.rename.assert_called_once_with(
            columns={
                "date_time": "Date",
                "opening_price": "Open",
                "high_price": "High",
                "low_price": "Low",
                "closing_price": "Close",
                "acc_volume": "Volume",
            }
        )

        # "buy": "orange",
        # "sell": "apple",
        # "avr_price": "banana",
        # "return": "kiwi",

        dummyDataFrame.set_index.assert_called_once_with("Date")
        mock_to_datetime.assert_called_once_with("mango")
        self.assertEqual(
            mock_make_addplot.call_args_list[0][0][0],
            "orange",
        )
        self.assertEqual(
            mock_make_addplot.call_args_list[0][1],
            {"type": "scatter", "markersize": 100, "marker": "^"},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[1][0][0],
            "apple",
        )
        self.assertEqual(
            mock_make_addplot.call_args_list[1][1],
            {"type": "scatter", "markersize": 100, "marker": "v"},
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[2][0][0],
            "banana",
        )

        self.assertEqual(
            mock_make_addplot.call_args_list[3][0][0],
            "kiwi",
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
            style="starsandstripes",
        )
