import time
import unittest
from smtm import MassSimulator, Config
from unittest.mock import *


class MassSimulatorIntegrationTests(unittest.TestCase):
    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        mass = MassSimulator()

        mass.run("tests/integration_tests/data/mass_simulation_config.json")
        expected_score = [
            "Result Summary =========================================",
            "수익률 평균:   -2.029",
            "수익률 편차:    0.865",
            "수익률 최대:   -1.417",
            "수익률 최소:    -2.64",
            "========================================================",
        ]

        self.assertEqual(mock_print.call_args_list[-6][0][0], expected_score[0])
        self.assertEqual(mock_print.call_args_list[-5][0][0], expected_score[1])
        self.assertEqual(mock_print.call_args_list[-4][0][0], expected_score[2])
        self.assertEqual(mock_print.call_args_list[-3][0][0], expected_score[3])
        self.assertEqual(mock_print.call_args_list[-2][0][0], expected_score[4])
        self.assertEqual(mock_print.call_args_list[-1][0][0], expected_score[5])


class MassSimulator3mIntervalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.interval_backup = Config.candle_interval
        Config.candle_interval = 180

    def tearDown(self):
        Config.candle_interval = self.interval_backup

    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        mass = MassSimulator()

        mass.run("tests/integration_tests/data/mass_simulation_3m_config.json")
        expected_score = [
            "Result Summary =========================================",
            "수익률 평균:   -2.034",
            "수익률 편차:    0.872",
            "수익률 최대:   -1.418",
            "수익률 최소:   -2.651",
            "========================================================",
        ]
        self.assertEqual(mock_print.call_args_list[-6][0][0], expected_score[0])
        self.assertEqual(mock_print.call_args_list[-5][0][0], expected_score[1])
        self.assertEqual(mock_print.call_args_list[-4][0][0], expected_score[2])
        self.assertEqual(mock_print.call_args_list[-3][0][0], expected_score[3])
        self.assertEqual(mock_print.call_args_list[-2][0][0], expected_score[4])
        self.assertEqual(mock_print.call_args_list[-1][0][0], expected_score[5])

class MassSimulatorDual3mIntervalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dp_type_backup = Config.simulation_data_provider_type
        self.interval_backup = Config.candle_interval
        Config.candle_interval = 180
        Config.simulation_data_provider_type = "dual"

    def tearDown(self):
        Config.candle_interval = self.interval_backup
        Config.simulation_data_provider_type = self.dp_type_backup

    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        mass = MassSimulator()

        mass.run("tests/integration_tests/data/mass_simulation_3m_config.json")
        expected_score = [
            "Result Summary =========================================",
            "수익률 평균:   -2.034",
            "수익률 편차:    0.872",
            "수익률 최대:   -1.418",
            "수익률 최소:   -2.651",
            "========================================================",
        ]
        self.assertEqual(mock_print.call_args_list[-6][0][0], expected_score[0])
        self.assertEqual(mock_print.call_args_list[-5][0][0], expected_score[1])
        self.assertEqual(mock_print.call_args_list[-4][0][0], expected_score[2])
        self.assertEqual(mock_print.call_args_list[-3][0][0], expected_score[3])
        self.assertEqual(mock_print.call_args_list[-2][0][0], expected_score[4])
        self.assertEqual(mock_print.call_args_list[-1][0][0], expected_score[5])
