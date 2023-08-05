from datetime import date, datetime
import unittest
from smtm import DateConverter
from unittest.mock import *


class DateConverterToEndMinTests(unittest.TestCase):
    def test_to_end_min_return_correct_tuple(self):
        result = DateConverter.to_end_min("200220-200320", max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 41760)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220.120000-200320", max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 41040)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220-200320.120000", max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 42480)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220.120000-200320.235500", max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T23:55:00", 42475)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("201220.170000-201220.180000", max_count=50000)
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 60)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200520-200320", max_count=50000)
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_list(self):
        result = DateConverter.to_end_min("200220-200223", max_count=5000)
        expect = ("2020-02-20T00:00:00", "2020-02-23T00:00:00", 4320)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220-200223", max_count=200)
        self.assertEqual(len(result), 22)
        self.assertEqual(result[0], ("2020-02-20T00:00:00", "2020-02-20T03:20:00", 200))
        self.assertEqual(result[1], ("2020-02-20T03:20:00", "2020-02-20T06:40:00", 200))
        self.assertEqual(result[2], ("2020-02-20T06:40:00", "2020-02-20T10:00:00", 200))
        self.assertEqual(result[3], ("2020-02-20T10:00:00", "2020-02-20T13:20:00", 200))
        self.assertEqual(result[4], ("2020-02-20T13:20:00", "2020-02-20T16:40:00", 200))
        self.assertEqual(result[5], ("2020-02-20T16:40:00", "2020-02-20T20:00:00", 200))
        self.assertEqual(result[6], ("2020-02-20T20:00:00", "2020-02-20T23:20:00", 200))
        self.assertEqual(result[7], ("2020-02-20T23:20:00", "2020-02-21T02:40:00", 200))
        self.assertEqual(result[8], ("2020-02-21T02:40:00", "2020-02-21T06:00:00", 200))
        self.assertEqual(result[9], ("2020-02-21T06:00:00", "2020-02-21T09:20:00", 200))
        self.assertEqual(result[10], ("2020-02-21T09:20:00", "2020-02-21T12:40:00", 200))
        self.assertEqual(result[11], ("2020-02-21T12:40:00", "2020-02-21T16:00:00", 200))
        self.assertEqual(result[12], ("2020-02-21T16:00:00", "2020-02-21T19:20:00", 200))
        self.assertEqual(result[13], ("2020-02-21T19:20:00", "2020-02-21T22:40:00", 200))
        self.assertEqual(result[14], ("2020-02-21T22:40:00", "2020-02-22T02:00:00", 200))
        self.assertEqual(result[15], ("2020-02-22T02:00:00", "2020-02-22T05:20:00", 200))
        self.assertEqual(result[16], ("2020-02-22T05:20:00", "2020-02-22T08:40:00", 200))
        self.assertEqual(result[17], ("2020-02-22T08:40:00", "2020-02-22T12:00:00", 200))
        self.assertEqual(result[18], ("2020-02-22T12:00:00", "2020-02-22T15:20:00", 200))
        self.assertEqual(result[19], ("2020-02-22T15:20:00", "2020-02-22T18:40:00", 200))
        self.assertEqual(result[20], ("2020-02-22T18:40:00", "2020-02-22T22:00:00", 200))
        self.assertEqual(result[21], ("2020-02-22T22:00:00", "2020-02-23T00:00:00", 120))

        result = DateConverter.to_end_min("200220.120000-200220.235500", max_count=300)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ("2020-02-20T12:00:00", "2020-02-20T17:00:00", 300))
        self.assertEqual(result[1], ("2020-02-20T17:00:00", "2020-02-20T22:00:00", 300))
        self.assertEqual(result[2], ("2020-02-20T22:00:00", "2020-02-20T23:55:00", 115))

        result = DateConverter.to_end_min("210310.050000-210310.230000", max_count=200)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0], ("2021-03-10T05:00:00", "2021-03-10T08:20:00", 200))
        self.assertEqual(result[1], ("2021-03-10T08:20:00", "2021-03-10T11:40:00", 200))
        self.assertEqual(result[2], ("2021-03-10T11:40:00", "2021-03-10T15:00:00", 200))
        self.assertEqual(result[3], ("2021-03-10T15:00:00", "2021-03-10T18:20:00", 200))
        self.assertEqual(result[4], ("2021-03-10T18:20:00", "2021-03-10T21:40:00", 200))
        self.assertEqual(result[5], ("2021-03-10T21:40:00", "2021-03-10T23:00:00", 80))

        result = DateConverter.to_end_min("200520-200320")
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_with_start_end(self):
        start = datetime.strptime("2020-02-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 41760)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-02-20T12:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 41040)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-02-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T12:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 42480)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-02-20T12:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T23:55:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T23:55:00", 42475)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-12-20T17:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-12-20T18:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 60)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-05-20T17:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T18:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000)
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_with_start_and_end_iso_format_string(self):
        start = "2020-02-20T00:00:00"
        end = "2020-03-20T00:00:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 41760)
        self.assertEqual(result[0], expect)

        start = "2020-02-20T12:00:00"
        end = "2020-03-20T00:00:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 41040)
        self.assertEqual(result[0], expect)

        start = "2020-02-20T00:00:00"
        end = "2020-03-20T12:00:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 42480)
        self.assertEqual(result[0], expect)

        start = "2020-02-20T12:00:00"
        end = "2020-03-20T23:55:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        expect = ("2020-02-20T12:00:00", "2020-03-20T23:55:00", 42475)
        self.assertEqual(result[0], expect)

        start = "2020-12-20T17:00:00"
        end = "2020-12-20T18:00:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 60)
        self.assertEqual(result[0], expect)

        start = "2020-05-20T17:00:00"
        end = "2020-03-20T18:00:00"
        result = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000)
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_when_3_interval(self):
        result = DateConverter.to_end_min("200220-200320", max_count=50000, interval_min=3)
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 13920)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220.120000-200320", max_count=50000, interval_min=3)
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 13680)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220-200320.120000", max_count=50000, interval_min=3)
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 14160)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min(
            "201220.170000-201220.180000", max_count=50000, interval_min=3
        )
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 20)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200520-200320", max_count=50000, interval_min=3)
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_list_when_3_interval(self):
        result = DateConverter.to_end_min("200220-200223", max_count=5000, interval_min=3)
        expect = ("2020-02-20T00:00:00", "2020-02-23T00:00:00", 1440)
        self.assertEqual(result[0], expect)

        result = DateConverter.to_end_min("200220-200223", max_count=200, interval_min=3)
        self.assertEqual(len(result), 8)
        self.assertEqual(result[0], ("2020-02-20T00:00:00", "2020-02-20T10:00:00", 200))
        self.assertEqual(result[1], ("2020-02-20T10:00:00", "2020-02-20T20:00:00", 200))
        self.assertEqual(result[2], ("2020-02-20T20:00:00", "2020-02-21T06:00:00", 200))
        self.assertEqual(result[3], ("2020-02-21T06:00:00", "2020-02-21T16:00:00", 200))
        self.assertEqual(result[4], ("2020-02-21T16:00:00", "2020-02-22T02:00:00", 200))
        self.assertEqual(result[5], ("2020-02-22T02:00:00", "2020-02-22T12:00:00", 200))
        self.assertEqual(result[6], ("2020-02-22T12:00:00", "2020-02-22T22:00:00", 200))
        self.assertEqual(result[7], ("2020-02-22T22:00:00", "2020-02-23T00:00:00", 40))

        result = DateConverter.to_end_min(
            "210310.050000-210310.230000", max_count=200, interval_min=3
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("2021-03-10T05:00:00", "2021-03-10T15:00:00", 200))
        self.assertEqual(result[1], ("2021-03-10T15:00:00", "2021-03-10T23:00:00", 160))

        result = DateConverter.to_end_min("200520-200320")
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_with_start_end_and_3_interval(self):
        start = datetime.strptime("2020-02-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(
            start_dt=start, end_dt=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 13920)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-02-20T12:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(
            start_dt=start, end_dt=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 13680)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-02-20T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T12:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(
            start_dt=start, end_dt=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 14160)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-12-20T17:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-12-20T18:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(
            start_dt=start, end_dt=end, max_count=50000, interval_min=3
        )
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 20)
        self.assertEqual(result[0], expect)

        start = datetime.strptime("2020-05-20T17:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T18:00:00", "%Y-%m-%dT%H:%M:%S")
        result = DateConverter.to_end_min(
            start_dt=start, end_dt=end, max_count=50000, interval_min=3
        )
        self.assertEqual(result, None)

    def test_to_end_min_return_correct_tuple_with_start_and_end_iso_format_string_and_3_interval(
        self,
    ):
        start = "2020-02-20T00:00:00"
        end = "2020-03-20T00:00:00"
        result = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T00:00:00", "2020-03-20T00:00:00", 13920)
        self.assertEqual(result[0], expect)

        start = "2020-02-20T12:00:00"
        end = "2020-03-20T00:00:00"
        result = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T12:00:00", "2020-03-20T00:00:00", 13680)
        self.assertEqual(result[0], expect)

        start = "2020-02-20T00:00:00"
        end = "2020-03-20T12:00:00"
        result = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=50000, interval_min=3
        )
        expect = ("2020-02-20T00:00:00", "2020-03-20T12:00:00", 14160)
        self.assertEqual(result[0], expect)

        start = "2020-12-20T17:00:00"
        end = "2020-12-20T18:00:00"
        result = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=50000, interval_min=3
        )
        expect = ("2020-12-20T17:00:00", "2020-12-20T18:00:00", 20)
        self.assertEqual(result[0], expect)

        start = "2020-05-20T17:00:00"
        end = "2020-03-20T18:00:00"
        result = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=50000, interval_min=3
        )
        self.assertEqual(result, None)

    def test_to_end_min_raise_user_warning_when_invalid_duration_and_3_interval(self):
        with self.assertRaises(UserWarning):
            DateConverter.to_end_min("200220.120015-200320.235510", max_count=50000, interval_min=3)

        start = datetime.strptime("2020-02-20T12:00:15", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime("2020-03-20T23:55:10", "%Y-%m-%dT%H:%M:%S")
        with self.assertRaises(UserWarning):
            DateConverter.to_end_min(start_dt=start, end_dt=end, max_count=50000, interval_min=3)

        start = "2020-02-20T12:00:15"
        end = "2020-03-20T23:55:10"
        with self.assertRaises(UserWarning):
            DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=50000, interval_min=3)


class DateConverterTests(unittest.TestCase):
    def test_num_2_datetime_return_correct_datetime(self):
        result = DateConverter.num_2_datetime(200220)
        expect = "2020-02-20T00:00:00"
        self.assertEqual(result.strftime("%Y-%m-%dT%H:%M:%S"), expect)

        result = DateConverter.num_2_datetime("200220")
        expect = "2020-02-20T00:00:00"
        self.assertEqual(result.strftime("%Y-%m-%dT%H:%M:%S"), expect)

        result = DateConverter.num_2_datetime(200220.213015)
        expect = "2020-02-20T21:30:15"
        self.assertEqual(result.strftime("%Y-%m-%dT%H:%M:%S"), expect)

        result = DateConverter.num_2_datetime(200220.213015)
        expect = "2020-02-20T21:30:15"
        self.assertEqual(result.strftime("%Y-%m-%dT%H:%M:%S"), expect)

        with self.assertRaises(ValueError):
            result = DateConverter.num_2_datetime(200220.21301)

        with self.assertRaises(ValueError):
            result = DateConverter.num_2_datetime(2022)

        with self.assertRaises(ValueError):
            result = DateConverter.num_2_datetime("20022a.21301")

    def test_to_iso_string_return_correct_string(self):
        dt = date(1981, 4, 30)
        result = DateConverter.to_iso_string(dt)
        self.assertEqual(result, "1981-04-30T00:00:00")

    def test_to_ktc_iso_str_return_correct_string(self):
        result = DateConverter.from_kst_to_utc_str("2019-01-04T13:48:09")
        self.assertEqual(result, "2019-01-04T04:48:09")

        result = DateConverter.from_kst_to_utc_str("2019-01-04T23:48:09")
        self.assertEqual(result, "2019-01-04T14:48:09")

    def test_timestamp_id_should_return_correct_string(self):
        now = datetime.now()
        now_time = now.strftime("%H%M%S")
        result = DateConverter.timestamp_id()
        self.assertEqual(result[-6:], now_time)

    def test_floor_min_should_return_correct_datetime_string(self):
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:01:15", 3), "2020-02-20T12:00:15")
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:02:15", 3), "2020-02-20T12:00:15")
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:03:15", 3), "2020-02-20T12:03:15")
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:04:15", 3), "2020-02-20T12:03:15")
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:04:15", 5), "2020-02-20T12:00:15")
        self.assertEqual(DateConverter.floor_min("2020-02-20T12:05:15", 5), "2020-02-20T12:05:15")
