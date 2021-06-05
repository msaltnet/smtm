import time
import unittest
from smtm import Simulator
from .data import simulation_data
from unittest.mock import *


class SimulatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        budget = 100000
        interval = 0.01
        from_dash_to = "200430.055000-200430.073000"
        simulator = Simulator(
            budget=1000000,
            interval=interval,
            strategy=0,
            from_dash_to=from_dash_to,
        )

        simulator.run_single()
        self.assertEqual(mock_print.call_args[0][0], "Good Bye~")

    @patch("builtins.input")
    @patch("builtins.print")
    def test_ITG_run_simulation(self, mock_print, mock_input):
        simulator = Simulator()
        mock_input.side_effect = [
            "i",
            "200430.055000",
            "200430.073000",
            "0.1",
            "1000000",
            "1",
            "r",
            "1",
            "s",
            "3",
            "1",
            "2",
            "t",
        ]
        simulator.main()

        expected_score = [
            "running",
            "ready",
            "current score ==========",
            "Good Bye~",
        ]

        self.assertEqual(mock_print.call_args_list[-10][0][0], expected_score[0])
        self.assertEqual(mock_print.call_args_list[-7][0][0], expected_score[1])
        self.assertEqual(mock_print.call_args_list[-6][0][0], expected_score[2])
        self.assertEqual(mock_print.call_args_list[-1][0][0], expected_score[3])
