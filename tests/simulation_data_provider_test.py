import unittest
from smtm import SimulationDataProvider
from unittest.mock import *
import requests

class SimulationDataProviderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_call_initialize_from_server(self):
        dp = SimulationDataProvider()
        dp.initialize_from_server = MagicMock()
        dp.initialize("mango")
        dp.initialize_from_server.assert_called_once_with("mango")
        print(dp._SimulationDataProvider__create_candle_info())

    def test_initialize_with_file_initialize_variable_and_update_data_correctly(self):
        dp = SimulationDataProvider()
        dp.index = 50
        dp.is_initialized = False
        dp.end = -1
        dp.count = -500

        dp.initialize_with_file("test_record.json", "banana", 50000)
        self.assertEqual(dp.index, 0)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(dp.end, "banana")
        self.assertEqual(dp.count, 50000)
        self.assertEqual(len(dp.data), 100)
        self.assertEqual(dp.data[-1]["candle_acc_trade_volume"], 8.06234416)

    def test_initialize_with_file_NOT_initialized_with_wrong_filepath(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("orange", "banana", 50000)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "banana")
        self.assertEqual(dp.count, 50000)

    def test_initialize_with_file_NOT_initialized_with_empty_file(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("test_empty.json", "banana", 50000)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "banana")
        self.assertEqual(dp.count, 50000)

    def test_initialize_with_file_NOT_initialized_with_invalid_JSON_file(self):
        dp = SimulationDataProvider()

        dp.initialize_with_file("test_string.json", "banana", 50000)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "banana")
        self.assertEqual(dp.count, 50000)

    def test_initialize_from_server_initialize_configuration_variables(self):
        dp = SimulationDataProvider()
        dp.index = 50
        dp.is_initialized = False
        dp.end = -1
        dp.count = -500

        dp.initialize_from_server(None, "mango", 300)
        self.assertEqual(dp.index, 0)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "mango")
        self.assertEqual(dp.count, 300)

    def test_initialize_from_server_NOT_initialized_with_invalid_response_data(self):
        dp = SimulationDataProvider()
        http_mock = Mock()
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.text = 'orange'
        dummy_response.raise_for_status = MagicMock()
        http_mock.request = MagicMock(return_value=dummy_response)
        dp.initialize_from_server(http_mock, "mango", 300)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "mango")
        self.assertEqual(dp.count, 300)

    def create_http_mock(self):
        http_mock = Mock()
        class HTTPError(Exception):
            def __init__(self, value):
                self.value = value
            def __str__(self):
                return self.value

        class RequestException(Exception):
            def __init__(self, value):
                self.value = value
            def __str__(self):
                return self.value

        http_mock.exceptions.HTTPError = HTTPError
        http_mock.exceptions.RequestException = RequestException
        return http_mock

    def test_initialize_from_server_NOT_initialized_with_invalid_response_error(self):
        dp = SimulationDataProvider()
        http_mock = self.create_http_mock()

        def raise_exception():
            raise http_mock.exceptions.HTTPError('HTTPError dummy exception')
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.text = 'orange'
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)

        dp.initialize_from_server(http_mock, "mango", 300)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "mango")
        self.assertEqual(dp.count, 300)

    def test_initialize_from_server_NOT_initialized_when_connection_fail(self):
        dp = SimulationDataProvider()
        http_mock = self.create_http_mock()

        def raise_exception():
            raise http_mock.exceptions.RequestException('RequestException dummy exception')
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)

        dp.initialize_from_server(http_mock, "mango", 300)
        self.assertEqual(dp.is_initialized, False)
        self.assertEqual(dp.end, "mango")
        self.assertEqual(dp.count, 300)

    def test_initialize_from_server_update_data_correctly(self):
        dp = SimulationDataProvider()
        http_mock = self.create_http_mock()

        def raise_exception():
            pass
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "apple"}, {"market": "banana"}]'
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)

        dp.initialize_from_server(http_mock, "mango", 300)
        self.assertEqual(dp.is_initialized, True)
        self.assertEqual(len(dp.data), 2)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(dp.data[0]['market'], "banana")
        self.assertEqual(dp.data[1]['market'], "apple")

    def test_initialize_from_server_call_request_with_correct_arguments(self):
        dp = SimulationDataProvider()
        http_mock = self.create_http_mock()

        def raise_exception():
            pass
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "apple"}, {"market": "banana"}]'
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)

        dp.initialize_from_server(http_mock)
        http_mock.request.assert_called_once_with("GET", dp.url, params=ANY)
        self.assertEqual(dp.query_string["to"], "2020-11-11 00:00:00")
        self.assertEqual(dp.query_string["count"], 100)

    def test_initialize_from_server_set_default_params(self):
        dp = SimulationDataProvider()
        http_mock = self.create_http_mock()

        def raise_exception():
            pass
        class DummyResponse:
            pass
        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "apple"}, {"market": "banana"}]'
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)

        dp.initialize_from_server(http_mock)
        http_mock.request.assert_called_once_with("GET", dp.url, params=ANY)
        self.assertEqual(dp.query_string["to"], "2020-11-11 00:00:00")
        self.assertEqual(dp.query_string["count"], 100)

    def test_get_info_return_None_without_initialize(self):
        dp = SimulationDataProvider()
        self.assertEqual(dp.get_info(), None)

    def test_get_info_return_correct_info_after_initialized_with_dummy_data_file(self):
        dp = SimulationDataProvider()
        dp.initialize_with_file("test_record.json", "banana", 50000)
        data1 = dp.get_info()
        self.assertEqual(data1.date_time, "2020-03-10T13:52:00")
        self.assertEqual(data1.opening_price, 9777000.00000000)
        self.assertEqual(data1.low_price, 9763000.00000000)

        data2 = dp.get_info()
        self.assertEqual(data2.date_time, "2020-03-10T13:51:00")
        self.assertEqual(data2.opening_price, 9717000.00000000)
        self.assertEqual(data2.low_price, 9717000.00000000)
