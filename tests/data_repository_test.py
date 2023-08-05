import json
import requests
import unittest
from smtm import DataRepository
from unittest.mock import *


class DataRepositoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_init_should_set_interval_and_url_correctly(self):
        repo = DataRepository()
        self.assertEqual(repo.interval_min, 1)
        self.assertEqual(repo.url, "https://api.upbit.com/v1/candles/minutes/1")
        repo = DataRepository(interval=180)
        self.assertEqual(repo.interval_min, 3)
        self.assertEqual(repo.url, "https://api.upbit.com/v1/candles/minutes/3")
        repo = DataRepository(interval=300)
        self.assertEqual(repo.interval_min, 5)
        self.assertEqual(repo.url, "https://api.upbit.com/v1/candles/minutes/5")
        repo = DataRepository(interval=600)
        self.assertEqual(repo.interval_min, 10)
        self.assertEqual(repo.url, "https://api.upbit.com/v1/candles/minutes/10")

    def test_init_should_raise_UserWarning_when_interval_not_supported(self):
        with self.assertRaises(UserWarning):
            repo = DataRepository(interval=1)

    @patch("requests.get")
    def test__fetch_from_upbit_up_to_200_should_call_get_correctly(self, mock_get):
        dummy_response = MagicMock()
        expected_value = [
            {
                "market": "mango",
                "candle_date_time_utc": "2020-03-10T13:52:00",
                "candle_date_time_kst": "2020-03-10T22:52:00",
                "opening_price": 9777000.00000000,
                "high_price": 9778000.00000000,
                "low_price": 9763000.00000000,
                "trade_price": 9778000.00000000,
                "timestamp": 1583848334534,
                "candle_acc_trade_price": 11277224.71063000,
                "candle_acc_trade_volume": 1.15377852,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-03-10T13:52:00",
                "candle_date_time_kst": "2020-03-10T22:52:00",
                "opening_price": 8777000.00000000,
                "high_price": 8778000.00000000,
                "low_price": 8763000.00000000,
                "trade_price": 8778000.00000000,
                "timestamp": 1583848334534,
                "candle_acc_trade_price": 11277224.71063000,
                "candle_acc_trade_volume": 1.15377852,
                "unit": 1,
            },
        ]
        dummy_response.json.return_value = expected_value
        mock_get.return_value = dummy_response

        end = "2020-03-20T00:00:00"
        repo = DataRepository()
        data = repo._fetch_from_upbit_up_to_200(end, 41760, "mango")
        mock_get.assert_called_once_with(
            "https://api.upbit.com/v1/candles/minutes/1",
            params={"market": "mango", "to": "2020-03-19T15:00:00Z", "count": 41760},
        )
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["opening_price"], 8777000.00000000)
        self.assertEqual(data[0]["high_price"], 8778000.00000000)
        self.assertEqual(data[0]["low_price"], 8763000.00000000)
        self.assertEqual(data[0]["closing_price"], 8778000.00000000)
        self.assertEqual(data[1]["opening_price"], 9777000.00000000)
        self.assertEqual(data[1]["high_price"], 9778000.00000000)
        self.assertEqual(data[1]["low_price"], 9763000.00000000)
        self.assertEqual(data[1]["closing_price"], 9778000.00000000)

    @patch("requests.get")
    def test__fetch_from_upbit_up_to_200_NOT_throw_UserWarning_when_receive_invalid_data(
        self, mock_get
    ):
        end = "2020-03-20T00:00:00"
        repo = DataRepository()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            data = repo._fetch_from_upbit_up_to_200(end, 200, "mango")
            self.assertIsNone(data)

    @patch("requests.get")
    def test__fetch_from_upbit_up_to_200_NOT_throw_UserWarning_when_receive_response_error(
        self, mock_get
    ):
        end = "2020-03-20T00:00:00"
        repo = DataRepository()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            data = repo._fetch_from_upbit_up_to_200(end, 200, "mango")
            self.assertIsNone(data)

    @patch("smtm.DateConverter.to_end_min")
    def test__fetch_from_upbit_should_call__fetch_from_upbit_up_to_200(self, mock_to_end_min):
        start = "2020-03-20T00:00:00"
        end = "2020-03-21T00:00:00"
        repo = DataRepository()
        repo._query = MagicMock(side_effect=[["mango"], ["apple"], ["orange"]])
        repo._is_equal = MagicMock()
        repo._update = MagicMock()
        repo.verify_mode = False
        repo._fetch_from_upbit_up_to_200 = MagicMock(side_effect=[["kiwi"]])
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:10:00", 1),
            ("2020-03-20T00:10:00", "2020-03-21T00:20:00", 1),
            ("2020-03-20T00:20:00", "2020-03-21T00:30:00", 2),
        ]
        repo._recovery_upbit_data = MagicMock(side_effect=[["orange"]])
        result = repo._fetch_from_upbit(start, end, "mango_market")

        mock_to_end_min.assert_called_once_with(
            start_iso=start, end_iso=end, max_count=200, interval_min=1.0
        )
        self.assertEqual(repo._query.call_args_list[0][0][0], "2020-03-20T00:00:00")
        self.assertEqual(repo._query.call_args_list[1][0][0], "2020-03-20T00:10:00")
        self.assertEqual(repo._query.call_args_list[2][0][0], "2020-03-20T00:20:00")
        self.assertEqual(repo._query.call_args_list[0][0][1], "2020-03-21T00:10:00")
        self.assertEqual(repo._query.call_args_list[1][0][1], "2020-03-21T00:20:00")
        self.assertEqual(repo._query.call_args_list[2][0][1], "2020-03-21T00:30:00")
        repo._fetch_from_upbit_up_to_200.assert_called_once_with(
            "2020-03-21T00:30:00", 2, "mango_market"
        )
        repo._update.assert_called_once_with(["orange"])
        self.assertEqual(result, ["mango", "apple", "orange"])
        repo._recovery_upbit_data.assert_called_once_with(
            ["kiwi"], "2020-03-20T00:20:00", 2, "mango_market"
        )

    @patch("smtm.DateConverter.to_end_min")
    def test__fetch_from_upbit_should_call__fetch_from_upbit_up_to_200_always_in_verify_mode(
        self, mock_to_end_min
    ):
        start = "2020-03-20T00:00:00"
        end = "2020-03-21T00:00:00"
        repo = DataRepository()
        repo._query = MagicMock(side_effect=[["mango"], ["apple"], ["orange"]])
        repo._is_equal = MagicMock()
        repo._update = MagicMock()
        repo.verify_mode = True
        repo._fetch_from_upbit_up_to_200 = MagicMock(side_effect=[["kiwi"], ["pear"], ["melon"]])
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:10:00", 1),
            ("2020-03-20T00:10:00", "2020-03-21T00:20:00", 1),
            ("2020-03-20T00:20:00", "2020-03-21T00:30:00", 2),
        ]
        repo._recovery_upbit_data = MagicMock(side_effect=[["kiwi"], ["pear"], ["orange"]])
        result = repo._fetch_from_upbit(start, end, "mango_market")

        mock_to_end_min.assert_called_once_with(
            start_iso=start, end_iso=end, max_count=200, interval_min=1.0
        )
        self.assertEqual(
            repo._fetch_from_upbit_up_to_200.call_args_list[0][0][0], "2020-03-21T00:10:00"
        )
        self.assertEqual(
            repo._fetch_from_upbit_up_to_200.call_args_list[1][0][0], "2020-03-21T00:20:00"
        )
        self.assertEqual(
            repo._fetch_from_upbit_up_to_200.call_args_list[2][0][0], "2020-03-21T00:30:00"
        )
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[0][0][1], 1)
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[1][0][1], 1)
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[2][0][1], 2)
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[0][0][2], "mango_market")
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[1][0][2], "mango_market")
        self.assertEqual(repo._fetch_from_upbit_up_to_200.call_args_list[2][0][2], "mango_market")
        repo._update.assert_called_once_with(["orange"])
        self.assertEqual(result, ["kiwi", "pear", "orange"])
        self.assertEqual(repo._is_equal.call_args_list[0][0][0], ["mango"])
        self.assertEqual(repo._is_equal.call_args_list[1][0][0], ["apple"])
        self.assertEqual(repo._is_equal.call_args_list[0][0][1], ["kiwi"])
        self.assertEqual(repo._is_equal.call_args_list[1][0][1], ["pear"])
        self.assertEqual(repo._recovery_upbit_data.call_args_list[0][0][0], ["kiwi"])
        self.assertEqual(repo._recovery_upbit_data.call_args_list[1][0][0], ["pear"])
        self.assertEqual(repo._recovery_upbit_data.call_args_list[2][0][0], ["melon"])
        self.assertEqual(repo._recovery_upbit_data.call_args_list[0][0][1], "2020-03-20T00:00:00")
        self.assertEqual(repo._recovery_upbit_data.call_args_list[1][0][1], "2020-03-20T00:10:00")
        self.assertEqual(repo._recovery_upbit_data.call_args_list[2][0][1], "2020-03-20T00:20:00")

    @patch("smtm.DateConverter.to_end_min")
    def test_get_data_should_return_data_when_database_return_data(self, mock_to_end_min):
        repo = DataRepository()
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:00:00", 2),
        ]
        repo.database = MagicMock()
        repo.database.query.return_value = [
            {"content": "mango", "date_time": "2020-03-20 00:00:00"},
            {"content": "banana", "date_time": "2020-03-20 00:01:00"},
        ]
        repo._convert_to_datetime = MagicMock()
        repo._fetch_from_upbit = MagicMock()
        result = repo.get_data("2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango")

        self.assertEqual(
            result,
            [
                {"content": "mango", "date_time": "2020-03-20T00:00:00"},
                {"content": "banana", "date_time": "2020-03-20T00:01:00"},
            ],
        )
        repo._fetch_from_upbit.assert_not_called()
        repo.database.update.assert_not_called()
        repo._convert_to_datetime.assert_not_called()
        mock_to_end_min.assert_called_once_with(
            start_iso="2020-02-20T17:00:15", end_iso="2020-02-20T22:00:15", interval_min=1.0
        )

    @patch("smtm.DateConverter.to_end_min")
    def test_get_data_should_return_data_when_database_data_not_enough(self, mock_to_end_min):
        repo = DataRepository()
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:00:00", 10),
        ]
        repo.database = MagicMock()
        repo.database.query.return_value = []
        repo._fetch_from_upbit = MagicMock(
            return_value=[
                {"content": "mango", "date_time": "2020-03-20T00:00:00"},
                {"content": "banana", "date_time": "2020-03-20 00:01:00"},
            ]
        )
        result = repo.get_data("2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango")

        self.assertEqual(
            result,
            [
                {"content": "mango", "date_time": "2020-03-20T00:00:00"},
                {"content": "banana", "date_time": "2020-03-20T00:01:00"},
            ],
        )
        mock_to_end_min.assert_called_once_with(
            start_iso="2020-02-20T17:00:15", end_iso="2020-02-20T22:00:15", interval_min=1.0
        )
        repo._fetch_from_upbit.assert_called_once_with(
            "2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango"
        )

    def test__is_equal_should_return_correct_judgement(self):
        dummy_data_a = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15", "period": 30, "recovered": 0},
            {"market": "apple", "date_time": "2020-02-20T18:00:15", "period": 30, "recovered": 0},
            {"market": "kiwi", "date_time": "2020-02-20T19:00:15", "period": 30, "recovered": 0},
        ]
        dummy_data_b = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15", "period": 30, "recovered": 0},
            {"market": "apple", "date_time": "2020-02-20T18:00:15", "period": 30, "recovered": 0},
        ]
        dummy_data_c = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15"},
            {"market": "apple", "date_time": "2020-02-20T18:00:15"},
        ]
        dummy_data_d = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15", "period": 30},
            {"market": "apple", "date_time": "2020-02-20T18:00:15", "period": 30},
            {"market": "kiwi", "date_time": "2020-02-20T19:00:15", "period": 30},
        ]
        self.assertFalse(DataRepository._is_equal(dummy_data_a, dummy_data_b))
        self.assertTrue(DataRepository._is_equal(dummy_data_b, dummy_data_c))
        self.assertFalse(DataRepository._is_equal(dummy_data_b, dummy_data_d))

    def test__query_should_call_database_query_correctly(self):
        repo = DataRepository()
        repo.database = MagicMock()
        repo._query("2020-02-20T17:00:15", "2020-02-20T18:00:15", "orange_market")
        repo.database.query.assert_called_once_with(
            "2020-02-20 17:00:15", "2020-02-20 18:00:15", "orange_market", period=60
        )

    def test__update_should_call_database_update_correctly(self):
        dummy_data = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15"},
            {"market": "apple", "date_time": "2020-02-20T18:00:15"},
        ]
        expected_data = [
            {"market": "mango", "date_time": "2020-02-20 17:00:15"},
            {"market": "apple", "date_time": "2020-02-20 18:00:15"},
        ]
        repo = DataRepository()
        repo.database = MagicMock()
        repo._update(dummy_data)
        repo.database.update.assert_called_once_with(expected_data, period=60)

    def test__recovery_upbit_data_should_return_recovered_data(self):
        repo = DataRepository()
        broken_data_0355_skipped = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:52:00",
                "closing_price": 11546000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:53:00",
                "closing_price": 11546000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:54:00",
                "closing_price": 11545000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:56:00",
                "closing_price": 11561000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_0355_skipped, "2020-02-22T03:53:00", 4, "mango"
        )
        repo._report_broken_block.assert_called_once_with("2020-02-22T03:55:00", "mango")
        self.assertEqual(len(recovered), 4)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:53:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[2]["date_time"], "2020-02-22T03:55:00")
        self.assertEqual(recovered[3]["date_time"], "2020-02-22T03:56:00")
        self.assertEqual(recovered[2]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11546000)
        self.assertEqual(recovered[1]["closing_price"], 11545000)
        self.assertEqual(recovered[2]["closing_price"], 11545000)
        self.assertEqual(recovered[3]["closing_price"], 11561000)

        broken_data_2_skipped = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:52:00",
                "closing_price": 11547000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:53:00",
                "closing_price": 11546000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:54:00",
                "closing_price": 11545000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:57:00",
                "closing_price": 11561000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_2_skipped, "2020-02-22T03:54:00", 4, "mango"
        )
        self.assertEqual(repo._report_broken_block.call_args_list[0][0][0], "2020-02-22T03:55:00")
        self.assertEqual(repo._report_broken_block.call_args_list[1][0][0], "2020-02-22T03:56:00")
        self.assertEqual(len(recovered), 4)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:55:00")
        self.assertEqual(recovered[2]["date_time"], "2020-02-22T03:56:00")
        self.assertEqual(recovered[3]["date_time"], "2020-02-22T03:57:00")
        self.assertEqual(recovered[1]["recovered"], 1)
        self.assertEqual(recovered[2]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11545000)
        self.assertEqual(recovered[1]["closing_price"], 11545000)
        self.assertEqual(recovered[2]["closing_price"], 11545000)
        self.assertEqual(recovered[3]["closing_price"], 11561000)

        broken_data_2_skipped2 = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:52:00",
                "closing_price": 11547000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:53:00",
                "closing_price": 11546000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:55:00",
                "closing_price": 11545000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:57:00",
                "closing_price": 11561000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_2_skipped2, "2020-02-22T03:54:00", 4, "mango"
        )
        self.assertEqual(repo._report_broken_block.call_args_list[0][0][0], "2020-02-22T03:54:00")
        self.assertEqual(repo._report_broken_block.call_args_list[1][0][0], "2020-02-22T03:56:00")
        self.assertEqual(len(recovered), 4)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:55:00")
        self.assertEqual(recovered[2]["date_time"], "2020-02-22T03:56:00")
        self.assertEqual(recovered[3]["date_time"], "2020-02-22T03:57:00")
        self.assertEqual(recovered[0]["recovered"], 1)
        self.assertEqual(recovered[2]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11546000)
        self.assertEqual(recovered[1]["closing_price"], 11545000)
        self.assertEqual(recovered[2]["closing_price"], 11545000)
        self.assertEqual(recovered[3]["closing_price"], 11561000)

        broken_data_first_skipped = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:52:00",
                "closing_price": 11547000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:54:00",
                "closing_price": 11546000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_first_skipped, "2020-02-22T03:53:00", 2, "mango"
        )
        repo._report_broken_block.assert_called_with("2020-02-22T03:53:00", "mango")
        self.assertEqual(len(recovered), 2)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:53:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[0]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11547000)
        self.assertEqual(recovered[1]["closing_price"], 11546000)

        broken_data_first_2_skipped = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:51:00",
                "closing_price": 11547000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:52:00",
                "closing_price": 11546000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_first_2_skipped, "2020-02-22T03:53:00", 2, "mango"
        )
        self.assertEqual(repo._report_broken_block.call_args_list[0][0][0], "2020-02-22T03:53:00")
        self.assertEqual(repo._report_broken_block.call_args_list[1][0][0], "2020-02-22T03:54:00")
        self.assertEqual(len(recovered), 2)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:53:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[0]["recovered"], 1)
        self.assertEqual(recovered[1]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11546000)
        self.assertEqual(recovered[1]["closing_price"], 11546000)

        broken_data_last_skipped = [
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:53:00",
                "closing_price": 11547000.0,
            },
            {
                "market": "KRW-BTC",
                "date_time": "2020-02-22T03:54:00",
                "closing_price": 11546000.0,
            },
        ]
        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_last_skipped, "2020-02-22T03:54:00", 2, "mango"
        )
        repo._report_broken_block.assert_called_with("2020-02-22T03:55:00", "mango")
        self.assertEqual(len(recovered), 2)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:55:00")
        self.assertEqual(recovered[1]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11546000)
        self.assertEqual(recovered[1]["closing_price"], 11546000)

        repo._report_broken_block = MagicMock()
        recovered = repo._recovery_upbit_data(
            broken_data_last_skipped, "2020-02-22T03:54:00", 3, "mango"
        )
        self.assertEqual(repo._report_broken_block.call_args_list[0][0][0], "2020-02-22T03:55:00")
        self.assertEqual(repo._report_broken_block.call_args_list[1][0][0], "2020-02-22T03:56:00")
        self.assertEqual(len(recovered), 3)
        self.assertEqual(recovered[0]["date_time"], "2020-02-22T03:54:00")
        self.assertEqual(recovered[1]["date_time"], "2020-02-22T03:55:00")
        self.assertEqual(recovered[2]["date_time"], "2020-02-22T03:56:00")
        self.assertEqual(recovered[1]["recovered"], 1)
        self.assertEqual(recovered[2]["recovered"], 1)
        self.assertEqual(recovered[0]["closing_price"], 11546000)
        self.assertEqual(recovered[1]["closing_price"], 11546000)
        self.assertEqual(recovered[2]["closing_price"], 11546000)

    @patch("requests.get")
    def test_get_data_should_return_data_fetched_from_server_with_1m_interval(self, get_mock):
        with open("tests/data/upbit_1m_20200220_170000-20200220_202000.json", "r") as f:
            get_mock.return_value.json.return_value = json.load(f)
        repo = DataRepository(interval=60)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:20:00", "KRW-BTC")
        self.assertEqual(len(result), 200)
        repo.database.update.assert_called_with(ANY, period=60)
        repo.database.query.assert_called_with(
            "2020-02-20 17:00:00", "2020-02-20 20:20:00", "KRW-BTC", period=60
        )

    @patch("requests.get")
    def test_get_data_should_return_big_data_fetched_from_server_with_1m_interval(self, get_mock):
        dummy_data = []
        with open("tests/data/upbit_1m_20200220_170000-20200220_202000.json", "r") as f:
            dummy_data.append(json.load(f))
        with open("tests/data/upbit_1m_20200220_202000-20200220_210000.json", "r") as f:
            dummy_data.append(json.load(f))
        get_mock.return_value.json.side_effect = dummy_data

        repo = DataRepository(interval=60)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T21:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)
        self.assertEqual(result[0]["date_time"], "2020-02-20T17:00:00")
        self.assertEqual(result[1]["date_time"], "2020-02-20T17:01:00")
        self.assertEqual(result[2]["date_time"], "2020-02-20T17:02:00")
        self.assertEqual(result[3]["date_time"], "2020-02-20T17:03:00")
        repo.database.update.assert_called_with(ANY, period=60)

    @patch("requests.get")
    def test_get_data_should_return_data_fetched_from_server_with_3m_interval(self, get_mock):
        with open("tests/data/upbit_3m_20200220_170000-20200220_200000.json", "r") as f:
            get_mock.return_value.json.return_value = json.load(f)

        repo = DataRepository(interval=180)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:01:00", "2020-02-20T20:02:00", "KRW-BTC")
        self.assertEqual(len(result), 60)
        self.assertEqual(result[0]["date_time"], "2020-02-20T17:00:00")
        self.assertEqual(result[1]["date_time"], "2020-02-20T17:03:00")
        self.assertEqual(result[2]["date_time"], "2020-02-20T17:06:00")
        self.assertEqual(result[3]["date_time"], "2020-02-20T17:09:00")
        repo.database.update.assert_called_with(ANY, period=180)

    @patch("requests.get")
    def test_get_data_should_return_big_data_fetched_from_server_with_3m_interval(self, get_mock):
        dummy_data = []
        with open("tests/data/upbit_3m_20200220_000000-20200220_100000.json", "r") as f:
            dummy_data.append(json.load(f))
        with open("tests/data/upbit_3m_20200220_100000-20200220_120000.json", "r") as f:
            dummy_data.append(json.load(f))
        get_mock.return_value.json.side_effect = dummy_data

        repo = DataRepository(interval=180)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-20T12:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)
        repo.database.update.assert_called_with(ANY, period=180)
        self.assertEqual(result[0]["date_time"], "2020-02-20T00:00:00")
        self.assertEqual(result[1]["date_time"], "2020-02-20T00:03:00")
        self.assertEqual(result[2]["date_time"], "2020-02-20T00:06:00")
        self.assertEqual(result[3]["date_time"], "2020-02-20T00:09:00")
        self.assertEqual(result[199]["date_time"], "2020-02-20T09:57:00")
        self.assertEqual(result[200]["date_time"], "2020-02-20T10:00:00")
        self.assertEqual(result[201]["date_time"], "2020-02-20T10:03:00")
        self.assertEqual(result[202]["date_time"], "2020-02-20T10:06:00")
