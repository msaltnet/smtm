import unittest
from smtm import Database
from unittest.mock import *


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("sqlite3.connect")
    def test_constructor_make_connection_correctly(self, mock_connect):
        dummy_connection = MagicMock()
        mock_connect.return_value = dummy_connection
        db = Database()
        mock_connect.assert_called_once_with("smtm.db", check_same_thread=False, timeout=30.0)
        dummy_connection.cursor.assert_called_once()

    def test_create_table_should_execute_and_commit_correct_statement(self):
        db = Database()
        db.cursor = MagicMock()
        db.conn = MagicMock()
        db.create_table()
        db.cursor.execute.assert_called_once_with(
            "CREATE TABLE IF NOT EXISTS upbit (id TEXT PRIMARY KEY, period INT, recovered INT, market TEXT, date_time DATETIME, opening_price FLOAT, high_price FLOAT, low_price FLOAT, closing_price FLOAT, acc_price FLOAT, acc_volume FLOAT)"
        )
        db.conn.commit.assert_called_once()

    def test_query_should_execute_and_commit_correct_statement(self):
        db = Database()
        db.cursor = MagicMock()
        db.query("start_date", "end_date", "mango_market")
        db.cursor.execute.assert_called_once_with(
            "SELECT period, recovered, market, date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume FROM upbit WHERE market = ? AND period = ? AND date_time >= ? AND date_time < ? ORDER BY datetime(date_time) ASC",
            ("mango_market", 60, "start_date", "end_date"),
        )
        db.cursor.fetchall.assert_called_once()

    def test_update_should_execute_and_commit_correct_statement(self):
        db = Database()
        dummy_data = [
            {
                "market": "mango",
                "date_time": "2020-03-10T22:52:00",
                "opening_price": 9777000.00000000,
                "high_price": 9778000.00000000,
                "low_price": 9763000.00000000,
                "closing_price": 9778000.00000000,
                "acc_price": 11277224.71063000,
                "acc_volume": 1.15377852,
                "recovered": 1,
            },
            {
                "market": "mango",
                "date_time": "2020-03-10T22:53:00",
                "opening_price": 8777000.00000000,
                "high_price": 8778000.00000000,
                "low_price": 8763000.00000000,
                "closing_price": 8778000.00000000,
                "acc_price": 11277224.71063000,
                "acc_volume": 1.15377852,
            },
            {
                "market": "mango",
                "date_time": "2020-03-10T22:53:00",
                "opening_price": 7777000.00000000,
                "high_price": 7778000.00000000,
                "low_price": 7763000.00000000,
                "closing_price": 7778000.00000000,
                "acc_price": 11277224.71063000,
                "acc_volume": 1.15377852,
            },
        ]

        db.cursor = MagicMock()
        db.conn = MagicMock()
        db.update(dummy_data)
        expected_tuple_list = [
            (
                "60S-2020-03-10T22:52:00",
                60,
                1,
                "mango",
                "2020-03-10T22:52:00",
                9777000.0,
                9778000.0,
                9763000.0,
                9778000.0,
                11277224.71063,
                1.15377852,
            ),
            (
                "60S-2020-03-10T22:53:00",
                60,
                0,
                "mango",
                "2020-03-10T22:53:00",
                8777000.0,
                8778000.0,
                8763000.0,
                8778000.0,
                11277224.71063,
                1.15377852,
            ),
            (
                "60S-2020-03-10T22:53:00",
                60,
                0,
                "mango",
                "2020-03-10T22:53:00",
                7777000.0,
                7778000.0,
                7763000.0,
                7778000.0,
                11277224.71063,
                1.15377852,
            ),
        ]

        db.cursor.executemany.assert_called_once_with(
            "REPLACE INTO upbit(id, period, recovered, market, date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            expected_tuple_list,
        )
        db.conn.commit.assert_called_once()
