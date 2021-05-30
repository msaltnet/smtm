from datetime import date
import unittest
from smtm import DateConverter
from unittest.mock import *


class DateConverterTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_to_end_min_return_correct_tuple(self):
        result = DateConverter.to_end_min("200220-200320")
        expect = ("2020-03-20T00:00:00", 41760)
        self.assertEqual(result, expect)

        result = DateConverter.to_end_min("200220.120015-200320")
        expect = ("2020-03-20T00:00:00", 41040)
        self.assertEqual(result, expect)

        result = DateConverter.to_end_min("200220-200320.120015")
        expect = ("2020-03-20T12:00:15", 42480)
        self.assertEqual(result, expect)

        result = DateConverter.to_end_min("200220.120015-200320.235510")
        expect = ("2020-03-20T23:55:10", 42475)
        self.assertEqual(result, expect)

        result = DateConverter.to_end_min("201220.170000-201220.180000")
        expect = ("2020-12-20T18:00:00", 60)
        self.assertEqual(result, expect)

        result = DateConverter.to_end_min("200520-200320")
        self.assertEqual(result, None)

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
