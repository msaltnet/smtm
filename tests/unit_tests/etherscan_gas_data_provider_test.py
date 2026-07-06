import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import EtherscanGasDataProvider


SAMPLE = {
    "status": "1",
    "message": "OK",
    "result": {
        "LastBlock": "20000000",
        "SafeGasPrice": "15",
        "ProposeGasPrice": "18",
        "FastGasPrice": "22",
        "suggestBaseFee": "14.3",
        "gasUsedRatio": "0.45,0.62,0.55",
    },
}


class EtherscanGasTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_normalized_entry(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = EtherscanGasDataProvider().get_info()

        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["type"], "eth_gas")
        self.assertEqual(entry["unit"], "gwei")
        self.assertEqual(entry["safe_gas_price"], 15.0)
        self.assertEqual(entry["propose_gas_price"], 18.0)
        self.assertEqual(entry["fast_gas_price"], 22.0)
        self.assertAlmostEqual(entry["suggest_base_fee"], 14.3)
        self.assertEqual(entry["last_block"], "20000000")

    @patch("requests.get")
    def test_api_key_sent_when_provided(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        EtherscanGasDataProvider(api_key="secret").get_info()

        self.assertEqual(mock_get.call_args.kwargs["params"]["apikey"], "secret")

    @patch("requests.get")
    def test_status_zero_returns_empty(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"status": "0", "message": "NOTOK", "result": {}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        self.assertEqual(EtherscanGasDataProvider().get_info(), [])

    @patch("requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")
        self.assertEqual(EtherscanGasDataProvider().get_info(), [])
