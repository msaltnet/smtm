import unittest
from smtm import SimulationDataProvider
from unittest.mock import *
import requests


class SimulationDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_simulation_call_initialize_from_server(self):
        dp = SimulationDataProvider()
        dp.initialize_from_server = MagicMock()
        dp.initialize_simulation("mango", "banana")
        dp.initialize_from_server.assert_called_once_with("mango", "banana")

    def test_initialize_with_file_update_data_correctly(self):
        dp = SimulationDataProvider()
        dp.index = 50
        dp.is_initialized = False

        dp.initialize_with_file("./tests/data/test_record.json")
        self.assertEqual(dp.index, 0)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 100)
        self.assertEqual(dp.data[-1]["candle_acc_trade_volume"], 8.06234416)

    def test_initialize_with_file_NOT_initialized_with_wrong_filepath(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("orange")
        self.assertEqual(dp.is_initialized, False)

    def test_initialize_with_file_NOT_initialized_with_empty_file(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("./tests/data/test_empty.json")
        self.assertEqual(dp.is_initialized, False)

    def test_initialize_with_file_NOT_initialized_with_invalid_JSON_file(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("./tests/data/test_string.json")
        self.assertEqual(dp.is_initialized, False)

    @patch("requests.get")
    def test_initialize_from_server_update_data_correctly(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        dp.initialize_from_server("mango", 300)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 2)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(dp.data[0]["market"], "banana")
        self.assertEqual(dp.data[1]["market"], "apple")

        mock_get.assert_called_once_with(dp.URL, params=ANY)
        self.assertEqual(mock_get.call_args[1]["params"]["to"], "mango")
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 300)

    @patch("requests.get")
    def test_initialize_from_server_call_request_with_default_arguments(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        dp.initialize_from_server()
        mock_get.assert_called_once_with(dp.URL, params=ANY)
        self.assertEqual("to" in mock_get.call_args[1]["params"], False)
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 100)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_with_invalid_response_data(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_from_server("mango", 300)
        self.assertEqual(dp.is_initialized, False)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_with_invalid_response_error(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_from_server("mango", 300)
        self.assertEqual(dp.is_initialized, False)

    @patch("requests.get")
    def test_initialize_from_server_NOT_initialized_when_connection_fail(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_from_server("mango", 300)
        self.assertEqual(dp.is_initialized, False)

    def test_get_info_return_None_without_initialize(self):
        dp = SimulationDataProvider()
        self.assertEqual(dp.get_info(), None)

    def test_get_info_return_correct_info_after_initialized_with_dummy_data_file(self):
        dp = SimulationDataProvider()
        dp.initialize_with_file("./tests/data/test_record.json")
        data1 = dp.get_info()
        self.assertEqual(data1["date_time"], "2020-03-10T22:52:00")
        self.assertEqual(data1["opening_price"], 9777000.00000000)
        self.assertEqual(data1["low_price"], 9763000.00000000)

        data2 = dp.get_info()
        self.assertEqual(data2["date_time"], "2020-03-10T22:51:00")
        self.assertEqual(data2["opening_price"], 9717000.00000000)
        self.assertEqual(data2["low_price"], 9717000.00000000)
