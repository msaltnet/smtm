import unittest
from smtm import TddExercise
from unittest.mock import *
import requests


class TddExerciseTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_set_period_update_period_correctly(self):
        ex = TddExercise()
        # check default value
        self.assertEqual(ex.end, None)
        self.assertEqual(ex.count, 100)

        ex.set_period("2020-02-25T06:41:00Z", 10)

        self.assertEqual(ex.end, "2020-02-25T06:41:00Z")
        self.assertEqual(ex.count, 10)

    @patch("requests.get")
    def test_initialize_from_server_update_is_initialized(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        ex.initialize_from_server("mango", 300)
        self.assertEqual(ex.is_initialized, True)
        self.assertEqual(len(ex.data), 2)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(ex.data[0]["market"], "banana")
        self.assertEqual(ex.data[1]["market"], "apple")

        mock_get.assert_called_once_with(ex.URL, params=ANY)
        self.assertEqual(mock_get.call_args[1]["params"]["to"], "mango")
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 300)

    @patch("requests.get")
    def test_initialize_from_server_update_data_correctly(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        ex.initialize_from_server("mango", 300)
        self.assertEqual(ex.is_initialized, True)
        self.assertEqual(len(ex.data), 2)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(ex.data[0]["market"], "banana")
        self.assertEqual(ex.data[1]["market"], "apple")

        mock_get.assert_called_once_with(ex.URL, params=ANY)
        self.assertEqual(mock_get.call_args[1]["params"]["to"], "mango")
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 300)

    @patch("requests.get")
    def test_initialize_from_server_call_request_with_default_arguments(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        ex.initialize_from_server()
        mock_get.assert_called_once_with(ex.URL, params=ANY)
        self.assertEqual("to" in mock_get.call_args[1]["params"], False)
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 100)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_with_invalid_response_data(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            ex.initialize_from_server("mango", 300)
        self.assertEqual(ex.is_initialized, False)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_with_invalid_response_error(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            ex.initialize_from_server("mango", 300)
        self.assertEqual(ex.is_initialized, False)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_when_connection_fail(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            ex.initialize_from_server("mango", 300)
        self.assertEqual(ex.is_initialized, False)
