import time
import unittest
from smtm import Simulator, Config
from .data import simulation_data
from unittest.mock import *


class SimulatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.interval = Config.candle_interval
        Config.candle_interval = 60

    def tearDown(self):
        Config.candle_interval = self.interval

    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        budget = 100000
        interval = 0.01
        from_dash_to = "200430.055000-200430.073000"
        simulator = Simulator(
            budget=1000000,
            interval=interval,
            strategy="BNH",
            from_dash_to=from_dash_to,
            currency="BTC",
        )

        simulator.run_single()
        self.assertEqual(mock_print.call_args[0][0], "Good Bye~")

    @patch("builtins.input")
    @patch("builtins.print")
    def test_ITG_run_simulation(self, mock_print, mock_input):
        simulator = Simulator()
        mock_input.side_effect = [
            "i",  # 초기화
            "200430.055000",  # 시뮬레이션 기간 시작점
            "200430.073000",  # 시뮬레이션 기간 종료점
            "0.1",  # interval
            "1000000",  # budget
            "BNH",  # strategy
            "ETH",  # currency
            "1",  # 상태 출력
            "r",  # 시뮬레이션 시작
            "1",  # 상태 출력
            "s",  # 시뮬레이션 종료
            "3",  # 거래 내역 출력
            "1",  # 상태 출력
            "2",  # 수익률 출력
            "t",  # 시뮬레이터 종료
        ]
        simulator.main()

        expected_score = [
            "ready",
            "current score ==========",
            "Good Bye~",
        ]

        self.assertEqual(mock_print.call_args_list[-1][0][0], expected_score[2])
        self.assertEqual(mock_print.call_args_list[-6][0][0], expected_score[1])
        self.assertEqual(mock_print.call_args_list[-7][0][0], expected_score[0])
