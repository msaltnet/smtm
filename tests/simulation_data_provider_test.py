import unittest
from smtm import SimulationDataProvider
from unittest.mock import *
import requests


class SimulationDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("requests.get")
    def test_initialize_simulation_update_data_correctly(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        dp.initialize_simulation("2020-12-20T18:00:00", 300)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 2)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(dp.data[0]["market"], "banana")
        self.assertEqual(dp.data[1]["market"], "apple")

        mock_get.assert_called_once_with(dp.URL, params=ANY)
        self.assertEqual(mock_get.call_args[1]["params"]["to"], "2020-12-20T09:00:00Z")
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 300)

    @patch("requests.get")
    def test_initialize_simulation_call_request_with_default_arguments(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        dp.initialize_simulation()
        mock_get.assert_called_once_with(dp.URL, params=ANY)
        self.assertEqual("to" in mock_get.call_args[1]["params"], False)
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 100)

    @patch("requests.get")
    def test_initialize_simulation_NOT_initialized_with_invalid_response_data(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_simulation("2020-12-20T18:00:00", 300)
        self.assertEqual(dp.is_initialized, False)

    @patch("requests.get")
    def test_initialize_simulation_NOT_initialized_with_invalid_response_error(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_simulation("2020-12-20T18:00:00", 300)
        self.assertEqual(dp.is_initialized, False)

    @patch("requests.get")
    def test_initialize_simulation_NOT_initialized_when_connection_fail(self, mock_get):
        dp = SimulationDataProvider()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        with self.assertRaises(UserWarning):
            dp.initialize_simulation("2020-12-20T18:00:00", 300)
        self.assertEqual(dp.is_initialized, False)

    def test_get_info_return_None_without_initialize(self):
        dp = SimulationDataProvider()
        self.assertEqual(dp.get_info(), None)
