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
        self.assertEqual(ex.to, None)
        self.assertEqual(ex.count, 100)

        ex.set_period("2020-02-25T06:41:00Z", 10)

        self.assertEqual(ex.to, "2020-02-25T06:41:00Z")
        self.assertEqual(ex.count, 10)

    def test_initialize_from_server_update_data_correctly_example(self):
        ex = TddExercise()
        self.assertEqual(len(ex.data), 0)

        ex.initialize_from_server()
        self.assertEqual(len(ex.data), 100)

    @patch("requests.get")
    def test_initialize_from_server_update_data_correctly_with_empty_data(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        mock_get.return_value = dummy_response

        ex.initialize_from_server()
        self.assertEqual(len(ex.data), 0)

    @patch("requests.get")
    def test_initialize_from_server_update_data_correctly(self, mock_get):
        ex = TddExercise()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        mock_get.return_value = dummy_response

        ex.initialize_from_server()
        self.assertEqual(len(ex.data), 2)
        self.assertEqual(ex.data[0], {"market": "apple"})
        self.assertEqual(ex.data[1], {"market": "banana"})

        mock_get.assert_called_once_with(ex.URL, params=ANY)
        self.assertEqual(mock_get.call_args[1]["params"]["count"], 100)
