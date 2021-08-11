import requests
import unittest
from datetime import datetime
from smtm import DataRepository
from unittest.mock import *


class DataRepositoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

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
        result = repo._fetch_from_upbit(start, end, "mango_market")

        mock_to_end_min.assert_called_once_with(start_iso=start, end_iso=end, max_count=200)
        self.assertEqual(repo._query.call_args_list[0][0][0], "2020-03-20T00:00:00")
        self.assertEqual(repo._query.call_args_list[1][0][0], "2020-03-20T00:10:00")
        self.assertEqual(repo._query.call_args_list[2][0][0], "2020-03-20T00:20:00")
        self.assertEqual(repo._query.call_args_list[0][0][1], "2020-03-21T00:10:00")
        self.assertEqual(repo._query.call_args_list[1][0][1], "2020-03-21T00:20:00")
        self.assertEqual(repo._query.call_args_list[2][0][1], "2020-03-21T00:30:00")
        repo._fetch_from_upbit_up_to_200.assert_called_once_with(
            "2020-03-21T00:30:00", 2, "mango_market"
        )
        repo._update.assert_called_once_with(["kiwi"])
        self.assertEqual(result, ["mango", "apple", "kiwi"])

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
        result = repo._fetch_from_upbit(start, end, "mango_market")

        mock_to_end_min.assert_called_once_with(start_iso=start, end_iso=end, max_count=200)
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
        repo._update.assert_called_once_with(["melon"])
        self.assertEqual(result, ["kiwi", "pear", "melon"])
        self.assertEqual(repo._is_equal.call_args_list[0][0][0], ["mango"])
        self.assertEqual(repo._is_equal.call_args_list[1][0][0], ["apple"])
        self.assertEqual(repo._is_equal.call_args_list[0][0][1], ["kiwi"])
        self.assertEqual(repo._is_equal.call_args_list[1][0][1], ["pear"])

    @patch("smtm.DateConverter.to_end_min")
    def test_get_data_should_return_data_when_database_return_data(self, mock_to_end_min):
        repo = DataRepository()
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:00:00", 2),
        ]
        repo.database = MagicMock()
        repo.database.query.return_value = ["mango", "banana"]
        repo._convert_to_upbit_datetime_string = MagicMock(return_value=["mango2", "banana2"])
        repo._convert_to_datetime = MagicMock()
        repo._fetch_from_upbit = MagicMock()
        result = repo.get_data("2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango")

        self.assertEqual(result, ["mango2", "banana2"])
        repo._fetch_from_upbit.assert_not_called()
        repo.database.update.assert_not_called()
        repo._convert_to_datetime.assert_not_called()
        repo._convert_to_upbit_datetime_string.assert_called_once_with(["mango", "banana"])
        mock_to_end_min.assert_called_once_with(
            start_iso="2020-02-20T17:00:15", end_iso="2020-02-20T22:00:15", max_count=100000000
        )

    @patch("smtm.DateConverter.to_end_min")
    def test_get_data_should_return_data_when_database_data_not_enough(self, mock_to_end_min):
        repo = DataRepository()
        mock_to_end_min.return_value = [
            ("2020-03-20T00:00:00", "2020-03-21T00:00:00", 10),
        ]
        repo.database = MagicMock()
        repo.database.query.return_value = []
        repo._convert_to_upbit_datetime_string = MagicMock()
        repo._fetch_from_upbit = MagicMock(return_value=["mango", "banana"])
        result = repo.get_data("2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango")

        self.assertEqual(result, ["mango", "banana"])
        repo._convert_to_upbit_datetime_string.assert_not_called()
        mock_to_end_min.assert_called_once_with(
            start_iso="2020-02-20T17:00:15", end_iso="2020-02-20T22:00:15", max_count=100000000
        )
        repo._fetch_from_upbit.assert_called_once_with(
            "2020-02-20T17:00:15", "2020-02-20T22:00:15", "mango"
        )

    def test__is_equal_should_return_correct_judgement(self):
        dummy_data_a = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15", "period": 30},
            {"market": "apple", "date_time": "2020-02-20T18:00:15", "period": 30},
            {"market": "kiwi", "date_time": "2020-02-20T19:00:15", "period": 30},
        ]
        dummy_data_b = [
            {"market": "mango", "date_time": "2020-02-20T17:00:15", "period": 30},
            {"market": "apple", "date_time": "2020-02-20T18:00:15", "period": 30},
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
        repo.database.query.assert_called_once_with("2020-02-20 17:00:15", "2020-02-20 18:00:15", "orange_market")

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
        repo.database.update.assert_called_once_with(expected_data)
