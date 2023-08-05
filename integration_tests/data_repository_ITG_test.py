import time
import random
from datetime import datetime, timedelta
import unittest
import os
import requests
from smtm import DataRepository, DateConverter
from unittest.mock import *


class DataRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        if os.path.isfile("test.db"):
            os.remove("test.db")

    def tearDown(self):
        if os.path.isfile("test.db"):
            os.remove("test.db")

    @staticmethod
    def _convert_to_dt(string):
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _convert_to_string(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    def _get_random_period(self, base_datetime):
        random_day = random.randrange(1, 200)
        base_dt = self._convert_to_dt(base_datetime)
        start_dt = base_dt + timedelta(days=random_day)
        random_count = random.randrange(1, 201)
        end_dt = start_dt + timedelta(minutes=random_count)

        return (self._convert_to_string(start_dt), self._convert_to_string(end_dt), random_count)

    def test_ITG_data_repository_fetch_and_verify_with_random_period(self):
        repo = DataRepository("test.db")
        dt_list = []
        base_datetime = [
            "2019-01-01T00:00:00",
            "2019-03-01T00:00:00",
            "2019-05-01T00:00:00",
            "2019-07-01T00:00:00",
            "2019-09-01T00:00:00",
            "2019-11-01T00:00:00",
            "2020-01-01T00:00:00",
            "2020-03-01T00:00:00",
            "2020-05-01T00:00:00",
            "2020-07-01T00:00:00",
            "2020-09-01T00:00:00",
            "2020-11-01T00:00:00",
            "2021-01-01T00:00:00",
            "2019-03-01T00:00:00",
            "2020-05-01T00:00:00",
            "2020-07-01T00:00:00",
            "2021-01-01T00:00:00",
        ]

        for item in base_datetime:
            dt_list.append(self._get_random_period(item))

        for dt in dt_list:
            print(f"### Check {dt[0]} to {dt[1]}, count: {dt[2]}")
            result = repo.get_data(dt[0], dt[1], "KRW-BTC")
            broken_list = []
            for i in result:
                if "recovered" in i and i["recovered"] > 0:
                    broken_list.append(i)
            print(f"== from repo with broken data {len(broken_list)}")
            upbit = self._fetch_from_upbit_up_to_200(dt[1], dt[2], "KRW-BTC")
            checked = self._check_equal(result, upbit)
            self.assertTrue(checked + len(broken_list), dt[2])
            time.sleep(1)
        del repo
        if os.path.isfile("test.db"):
            os.remove("test.db")

    def _check_equal(self, repo_data, upbit_data):
        idx = 0
        checked = 0
        for data in repo_data:
            while len(upbit_data) > idx:
                upbit_one = upbit_data[idx]
                if data["date_time"] == upbit_one["date_time"]:
                    # check all
                    self.assertEqual(data["date_time"], upbit_one["date_time"])
                    self.assertEqual(data["opening_price"], upbit_one["opening_price"])
                    self.assertEqual(data["high_price"], upbit_one["high_price"])
                    self.assertEqual(data["low_price"], upbit_one["low_price"])
                    self.assertEqual(data["closing_price"], upbit_one["closing_price"])
                    self.assertEqual(data["acc_price"], upbit_one["acc_price"])
                    self.assertEqual(data["acc_volume"], upbit_one["acc_volume"])
                    checked += 1
                    break
                elif "recovered" in data and data["recovered"] > 0:
                    break
                idx += 1
        print(f"== checked data count {checked}")
        return checked

    def _fetch_from_upbit_up_to_200(self, end, count, market):
        """업비트 서버에서 최대 200개까지 데이터 조회해서 반환
        1, 3, 5, 15, 10, 30, 60, 240분 가능
        https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
        """

        URL = f"https://api.upbit.com/v1/candles/minutes/1"
        to = DateConverter.from_kst_to_utc_str(end) + "Z"
        query_string = {"market": market, "to": to, "count": count}
        try:
            response = requests.get(URL, params=query_string)
            response.raise_for_status()
            data = response.json()
            data.reverse()
            final_data = []
            for item in data:
                final_data.append(
                    {
                        "market": item["market"],
                        "date_time": item["candle_date_time_kst"],
                        "opening_price": float(item["opening_price"]),
                        "high_price": float(item["high_price"]),
                        "low_price": float(item["low_price"]),
                        "closing_price": float(item["trade_price"]),
                        "acc_price": float(item["candle_acc_trade_price"]),
                        "acc_volume": float(item["candle_acc_trade_volume"]),
                    }
                )
            return final_data

        except ValueError as error:
            print(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            print(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            print(error)
            raise UserWarning("Fail get data from sever") from error

    def test_get_data_should_return_data_fetched_from_server_with_1m_interval(self):
        repo = DataRepository("test.db", interval=60)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:20:00", "KRW-BTC")
        self.assertEqual(len(result), 200)
        repo.database.update.assert_called()

    def test_get_data_should_return_big_data_fetched_from_server_with_1m_interval(self):
        repo = DataRepository("test.db", interval=60)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T21:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)
        repo.database.update.assert_called()

    def test_get_data_should_return_data_fetched_from_server_with_3m_interval(self):
        repo = DataRepository("test.db", interval=180)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 60)
        repo.database.update.assert_called()

        repo = DataRepository("test.db", interval=180)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:02:00", "2020-02-20T20:01:00", "KRW-BTC")
        self.assertEqual(len(result), 60)
        repo.database.update.assert_called()

    def test_get_data_should_return_big_data_fetched_from_server_with_3m_interval(self):
        repo = DataRepository("test.db", interval=180)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-20T12:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)
        repo.database.update.assert_called()

    def test_get_data_should_return_data_fetched_from_server_with_5m_interval(self):
        repo = DataRepository("test.db", interval=300)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 36)
        repo.database.update.assert_called()

        repo = DataRepository("test.db", interval=300)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:04:00", "2020-02-20T20:01:00", "KRW-BTC")
        self.assertEqual(len(result), 36)
        repo.database.update.assert_called()

    def test_get_data_should_return_big_data_fetched_from_server_with_5m_interval(self):
        repo = DataRepository("test.db", interval=300)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-21T00:00:00", "KRW-BTC")
        self.assertEqual(len(result), 288)
        repo.database.update.assert_called()

    def test_get_data_should_return_data_fetched_from_server_with_10m_interval(self):
        repo = DataRepository("test.db", interval=600)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 18)
        repo.database.update.assert_called()

        repo = DataRepository("test.db", interval=600)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T17:08:00", "2020-02-20T20:06:00", "KRW-BTC")
        self.assertEqual(len(result), 18)
        repo.database.update.assert_called()

    def test_get_data_should_return_big_data_fetched_from_server_with_10m_interval(self):
        repo = DataRepository("test.db", interval=600)
        repo.database = MagicMock()
        repo.database.query.return_value = []
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-22T00:00:00", "KRW-BTC")
        self.assertEqual(len(result), 288)
        repo.database.update.assert_called()

    def test_get_data_should_return_data_fetched_from_database_with_1m_interval(self):
        repo = DataRepository("test.db", interval=60)
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:20:00", "KRW-BTC")
        self.assertEqual(len(result), 200)

    def test_get_data_should_return_big_data_fetched_from_database_with_1m_interval(self):
        repo = DataRepository("test.db", interval=60)
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T21:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)

    def test_get_data_should_return_data_fetched_from_database_with_3m_interval(self):
        repo = DataRepository("test.db", interval=180)
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 60)

        repo = DataRepository("test.db", interval=180)
        result = repo.get_data("2020-02-20T17:02:00", "2020-02-20T20:01:00", "KRW-BTC")
        self.assertEqual(len(result), 60)

    def test_get_data_should_return_big_data_fetched_from_database_with_3m_interval(self):
        repo = DataRepository("test.db", interval=180)
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-20T12:00:00", "KRW-BTC")
        self.assertEqual(len(result), 240)

    def test_get_data_should_return_data_fetched_from_database_with_5m_interval(self):
        repo = DataRepository("test.db", interval=300)
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 36)

        repo = DataRepository("test.db", interval=300)
        result = repo.get_data("2020-02-20T17:04:00", "2020-02-20T20:01:00", "KRW-BTC")
        self.assertEqual(len(result), 36)

    def test_get_data_should_return_big_data_fetched_from_database_with_5m_interval(self):
        repo = DataRepository("test.db", interval=300)
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-21T00:00:00", "KRW-BTC")
        self.assertEqual(len(result), 288)

    def test_get_data_should_return_data_fetched_from_database_with_10m_interval(self):
        repo = DataRepository("test.db", interval=600)
        result = repo.get_data("2020-02-20T17:00:00", "2020-02-20T20:00:00", "KRW-BTC")
        self.assertEqual(len(result), 18)

        repo = DataRepository("test.db", interval=600)
        result = repo.get_data("2020-02-20T17:08:00", "2020-02-20T20:06:00", "KRW-BTC")
        self.assertEqual(len(result), 18)

    def test_get_data_should_return_big_data_fetched_from_database_with_10m_interval(self):
        repo = DataRepository("test.db", interval=600)
        result = repo.get_data("2020-02-20T00:00:00", "2020-02-22T00:00:00", "KRW-BTC")
        self.assertEqual(len(result), 288)
