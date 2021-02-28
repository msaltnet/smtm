import unittest
from smtm import SimulationOperator
from unittest.mock import *
import requests
import threading


class SimulationOperatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_simulation_keep_object_correctly(self):
        operator = SimulationOperator()
        operator.initialize_simulation("apple", "kiwi", "mango", "banana", "orange", "grape")
        self.assertEqual(operator.http, "apple")
        self.assertEqual(operator.threading, "kiwi")
        self.assertEqual(operator.data_provider, "mango")
        self.assertEqual(operator.strategy, "banana")
        self.assertEqual(operator.trader, "orange")
        self.assertEqual(operator.analyzer, "grape")

    def test_initialize_simulation_call_simulator_trader_initialize_with_config(self):
        sop = SimulationOperator()
        trader = Mock()
        trader.initialize = MagicMock()
        trader.send_account_info_request = MagicMock()
        strategy = Mock()
        data_provider = Mock()
        analyzer = Mock()
        analyzer.intialize = MagicMock()
        self.assertEqual(sop.turn, 0)
        self.assertEqual(sop.end, None)
        self.assertEqual(sop.count, 0)
        self.assertEqual(sop.budget, 0)
        sop.initialize_simulation(
            "apple", "kiwi", data_provider, strategy, trader, analyzer, "papaya", "pear", "grape"
        )
        trader.initialize.assert_called_once_with(
            "apple", end="papaya", count="pear", budget="grape"
        )
        analyzer.initialize.assert_called_once_with(ANY, True)
        update_info_func = analyzer.initialize.call_args[0][0]
        update_info_func("asset", "applemango")
        trader.send_account_info_request.assert_called_once_with("applemango")
        update_info_func("mango", "applemango")
        trader.send_account_info_request.assert_called_once()
        self.assertEqual(sop.end, "papaya")
        self.assertEqual(sop.count, "pear")
        self.assertEqual(sop.budget, "grape")

    def test_initialize_simulation_call_strategy_initialize_with_config(self):
        sop = SimulationOperator()
        trader = Mock()
        strategy = Mock()
        strategy.initialize = MagicMock()
        data_provider = Mock()
        analyzer = Mock()
        data_provider.initialize_from_server = MagicMock()
        sop.initialize_simulation(
            "apple", "kiwi", data_provider, strategy, trader, analyzer, "papaya", "pear", "grape"
        )
        strategy.initialize.assert_called_once_with("grape")

    def test_initialize_simulation_set_state_None_when_AttributeError_occur(self):
        sop = SimulationOperator()
        trader = Mock()
        strategy = Mock()
        data_provider = "make_exception"
        sop.initialize_simulation(
            "apple", "kiwi", data_provider, strategy, trader, "papaya", "pear", "grape"
        )
        self.assertEqual(sop.state, None)

    def test_initialize_call_simulator_dataProvider_initialize_from_server_correctly(self):
        sop = SimulationOperator()
        trader = Mock()
        strategy = Mock()
        data_provider = Mock()
        analyzer = Mock()
        data_provider.initialize_from_server = MagicMock()
        sop.initialize_simulation(
            "apple", "kiwi", data_provider, strategy, trader, analyzer, "papaya", "pear", "grape"
        )
        data_provider.initialize_from_server.assert_called_once_with(
            "apple", end="papaya", count="pear"
        )

    @patch("smtm.Operator.set_interval")
    def test_setup_call_super_setup(self, OperatorSetup):
        sop = SimulationOperator()
        sop.set_interval(10)
        OperatorSetup.assert_called_once_with(10)

    @patch("smtm.Operator.start")
    def test_start_call_super_start(self, OperatorStart):
        sop = SimulationOperator()
        sop.start()
        OperatorStart.assert_called_once()

    @patch("smtm.Operator.start")
    def test_start_should_call_analyzer_make_start_point(self, OperatorStart):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)
        operator = SimulationOperator()
        analyzer_mock = Mock()
        analyzer_mock.make_start_point = MagicMock()
        trader_mock = Mock()
        dp_mock = Mock()
        strategy_mock = Mock()
        operator.initialize(
            "apple", threading_mock, dp_mock, strategy_mock, trader_mock, analyzer_mock
        )
        operator.start()
        OperatorStart.assert_called_once()
        analyzer_mock.make_start_point.assert_called_once()

    @patch("smtm.Operator.stop")
    def test_stop_call_super_stop(self, OperatorStop):
        sop = SimulationOperator()
        sop.stop()
        OperatorStop.assert_called_once()

    def test_excute_trading_should_call_get_info_and_set_timer(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)

        operator = SimulationOperator()
        self.assertEqual(operator.turn, 0)
        analyzer_mock = Mock()
        analyzer_mock.put_trading_info = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()
        operator.initialize_simulation(
            "apple", threading_mock, dp_mock, strategy_mock, trader_mock, analyzer_mock
        )
        operator.set_interval(27)
        operator.state = "running"
        operator._excute_trading(None)
        threading_mock.Timer.assert_called_once_with(27, ANY)
        timer_mock.start.assert_called_once()
        dp_mock.get_info.assert_called_once()
        self.assertEqual(operator.turn, 1)
        analyzer_mock.put_trading_info.assert_called_once_with("mango")

    def test_excute_trading_should_call_trader_send_request_and_strategy_update_result(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)
        operator = SimulationOperator()
        analyzer_mock = Mock()
        analyzer_mock.put_request = MagicMock()
        analyzer_mock.put_result = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.update_result = MagicMock()
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()
        operator.initialize_simulation(
            "apple", threading_mock, dp_mock, strategy_mock, trader_mock, analyzer_mock
        )
        operator.set_interval(27)
        operator._excute_trading(None)

        dummy_result = {"name": "mango", "type": "buy", "msg": "success"}
        analyzer_mock.put_request.assert_called_once_with(dummy_request)
        strategy_mock.update_trading_info.assert_called_once_with(ANY)
        trader_mock.send_request.assert_called_once_with(ANY, ANY)
        trader_mock.send_request.call_args[0][1](dummy_result)
        strategy_mock.update_result.assert_called_once_with(dummy_result)
        analyzer_mock.put_result.assert_called_once_with(dummy_result)

    def test_excute_trading_should_call_creat_report_and_call_stop_when_result_msg_game_over(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)
        operator = SimulationOperator()
        operator.stop = MagicMock()
        analyzer_mock = Mock()
        analyzer_mock.put_request = MagicMock()
        analyzer_mock.put_result = MagicMock()
        analyzer_mock.create_report = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.update_result = MagicMock()
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()
        operator.initialize_simulation(
            "apple", threading_mock, dp_mock, strategy_mock, trader_mock, analyzer_mock
        )
        operator.set_interval(27)
        operator._excute_trading(None)
        analyzer_mock.put_request.assert_called_once_with(dummy_request)
        strategy_mock.update_trading_info.assert_called_once_with(ANY)
        trader_mock.send_request.assert_called_once_with(ANY, ANY)

        dummy_result = {"msg": "game-over"}
        trader_mock.send_request.call_args[0][1](dummy_result)
        strategy_mock.update_result.assert_not_called()
        analyzer_mock.put_result.assert_not_called()
        analyzer_mock.create_report.assert_called_once()
        operator.stop.assert_called_once()

    def test_excute_trading_should_NOT_call_trader_send_request_when_request_is_None(self):
        timer_mock = Mock()
        threading_mock = Mock()
        threading_mock.Timer = MagicMock(return_value=timer_mock)

        operator = SimulationOperator()
        analyzer_mock = Mock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")
        strategy_mock = Mock()
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value=None)
        trader_mock = Mock()
        trader_mock.send_request = MagicMock()
        operator.initialize_simulation(
            "apple", threading_mock, dp_mock, strategy_mock, trader_mock, analyzer_mock
        )
        operator.set_interval(27)
        operator._excute_trading(None)
        trader_mock.send_request.assert_not_called()
