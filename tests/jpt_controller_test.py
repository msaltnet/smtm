import unittest
from smtm import (
    JptController,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    BithumbTrader,
    BithumbDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
)
from unittest.mock import *


class JptControllerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("smtm.Operator.set_interval")
    @patch("smtm.Operator.initialize")
    def test_initialize_should_call_initialize_operator_correctly(
        self, mock_initialize, mock_set_interval
    ):
        controller = JptController()
        self.assertEqual(controller.need_init, True)
        controller.initialize(interval=7, strategy="BNH", budget=300)
        self.assertEqual(controller.need_init, False)
        mock_set_interval.assert_called_with(7)
        mock_initialize.assert_called()
        self.assertTrue(isinstance(mock_initialize.call_args_list[0][0][0], UpbitDataProvider))
        self.assertTrue(isinstance(mock_initialize.call_args_list[0][0][1], StrategyBuyAndHold))
        self.assertTrue(isinstance(mock_initialize.call_args_list[0][0][2], UpbitTrader))
        self.assertTrue(isinstance(mock_initialize.call_args_list[0][0][3], Analyzer))
        self.assertEqual(mock_initialize.call_args_list[0][1]["budget"], 300)

        controller.initialize(interval=5, strategy="SMA", budget=700)
        mock_set_interval.assert_called_with(5)
        self.assertTrue(isinstance(mock_initialize.call_args_list[1][0][0], UpbitDataProvider))
        self.assertTrue(isinstance(mock_initialize.call_args_list[1][0][1], StrategySma0))
        self.assertTrue(isinstance(mock_initialize.call_args_list[1][0][2], UpbitTrader))
        self.assertTrue(isinstance(mock_initialize.call_args_list[1][0][3], Analyzer))
        self.assertEqual(mock_initialize.call_args_list[1][1]["budget"], 700)

        controller.initialize(interval=5, strategy="SMA", budget=888, is_bithumb=True)
        mock_set_interval.assert_called_with(5)
        self.assertTrue(isinstance(mock_initialize.call_args_list[2][0][0], BithumbDataProvider))
        self.assertTrue(isinstance(mock_initialize.call_args_list[2][0][1], StrategySma0))
        self.assertTrue(isinstance(mock_initialize.call_args_list[2][0][2], BithumbTrader))
        self.assertTrue(isinstance(mock_initialize.call_args_list[2][0][3], Analyzer))
        self.assertEqual(mock_initialize.call_args_list[2][1]["budget"], 888)

    @patch("smtm.Operator.start")
    def test_start_should_call_operator_start_after_initialized(self, mock_start):
        controller = JptController()
        controller.initialize(interval=5, strategy="SMA", budget=700)
        controller.start()
        mock_start.assert_called_once()

    @patch("smtm.Operator.start")
    def test_start_should_NOT_call_operator_start_before_initialized(self, mock_start):
        controller = JptController()
        controller.start()
        mock_start.assert_not_called()

    @patch("smtm.Operator.stop")
    def test_stop_should_call_operator_stop_after_initialized(self, mock_stop):
        controller = JptController()
        controller.initialize(interval=5, strategy="SMA", budget=700)
        self.assertEqual(controller.need_init, False)
        controller.stop()
        mock_stop.assert_called_once()
        self.assertEqual(controller.need_init, True)

    @patch("smtm.Operator.stop")
    def test_stop_should_NOT_call_operator_stop_before_initialized(self, mock_stop):
        controller = JptController()
        controller.start()
        mock_stop.assert_not_called()

    @patch("builtins.print")
    def test_get_state_print_state_with_upper_case(self, mock_print):
        controller = JptController()
        controller.operator = MagicMock()
        controller.operator.state = "mango"
        controller.get_state()
        mock_print.assert_called_once_with("현재 시스템 상태: MANGO")

    def test_get_score_call_operator_get_score(self):
        controller = JptController()
        controller.operator = MagicMock()
        controller.get_score()
        controller.operator.get_score.assert_called_once()

    @patch("builtins.print")
    def test_get_trading_record_call_operator_get_trading_results(self, mock_print):
        controller = JptController()
        controller.operator = MagicMock()
        controller.operator.get_trading_results.return_value = [
            {"date_time": "today", "type": "buy", "price": 555, "amount": 0.000123}
        ]
        controller.get_trading_record()
        controller.operator.get_trading_results.assert_called_once()
        self.assertEqual(mock_print.call_args_list[-2][0][0], "@today, buy")
        self.assertEqual(mock_print.call_args_list[-1][0][0], "555 x 0.000123")

    @patch("smtm.LogManager.set_stream_level")
    def test_set_log_level_should_call_Logmanager_set_stream_level(self, mock_log):
        controller = JptController()
        controller.set_log_level(72)
        mock_log.assert_called_once_with(72)
