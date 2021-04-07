import unittest
from smtm import SimulationOperator
from unittest.mock import *
import requests
import threading


class SimulationInitializeOperatorTests(unittest.TestCase):
    def setUp(self):
        self.sop = SimulationOperator()
        self.strategy_mock = MagicMock()
        self.trader_mock = MagicMock()
        self.analyzer_mock = MagicMock()
        self.data_provider_mock = MagicMock()

    def tearDown(self):
        pass

    def test_initialize_simulation_keep_object_correctly(self):
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
        )
        self.assertEqual(self.sop.data_provider, self.data_provider_mock)
        self.assertEqual(self.sop.strategy, self.strategy_mock)
        self.assertEqual(self.sop.trader, self.trader_mock)
        self.assertEqual(self.sop.analyzer, self.analyzer_mock)
        self.strategy_mock.initialize.assert_called_once_with(500)

    def test_initialize_simulation_call_simulator_trader_initialize_with_config(self):
        self.assertEqual(self.sop.turn, 0)
        self.assertEqual(self.sop.end, "2020-12-20T16:23:00")
        self.assertEqual(self.sop.count, 0)
        self.assertEqual(self.sop.budget, 0)
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
            "papaya",
            "pear",
            "grape",
        )
        self.trader_mock.initialize.assert_called_once_with(
            end="papaya", count="pear", budget="grape"
        )
        self.analyzer_mock.initialize.assert_called_once_with(ANY, True)
        update_info_func = self.analyzer_mock.initialize.call_args[0][0]
        update_info_func("asset")
        self.trader_mock.send_account_info_request.assert_called_once_with(ANY)
        update_info_func("mango")
        self.trader_mock.send_account_info_request.assert_called_once()
        self.assertEqual(self.sop.end, "papaya")
        self.assertEqual(self.sop.count, "pear")
        self.assertEqual(self.sop.budget, "grape")

    def test_initialize_simulation_call_strategy_initialize_with_config(self):
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
            "papaya",
            "pear",
            "grape",
        )
        self.strategy_mock.initialize.assert_called_once_with("grape")

    def test_initialize_simulation_set_state_None_when_UserWarning_occur(self):
        self.data_provider_mock.initialize_from_server = MagicMock(
            side_effect=UserWarning("TEST Exception")
        )
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
            "papaya",
            "pear",
            "grape",
        )
        self.data_provider_mock.initialize_from_server.assert_called_once()
        self.assertEqual(self.sop.state, None)

    def test_initialize_call_simulator_dataProvider_initialize_from_server_correctly(self):
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
            "papaya",
            "pear",
            "grape",
        )
        self.data_provider_mock.initialize_from_server.assert_called_once_with(
            end="papaya", count="pear"
        )

    def test_initialize_simulation_update_tag_correctly(self):
        target_end = "2020-10-01 13:12:00"
        expected_tag = "2020-10-01T131200-35-BTC-"
        self.sop.initialize_simulation(
            self.data_provider_mock,
            self.strategy_mock,
            self.trader_mock,
            self.analyzer_mock,
            target_end,
            35,
            "papaya",
        )
        self.assertEqual(self.sop.tag[: len(expected_tag)], expected_tag)


class SimulationOperatorStartTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("smtm.Operator.set_interval")
    def test_setup_call_super_setup(self, OperatorSetup):
        sop = SimulationOperator()
        sop.set_interval(10)
        OperatorSetup.assert_called_once_with(10)

    @patch("smtm.Operator.start")
    def test_start_call_super_start(self, OperatorStart):
        sop = SimulationOperator()
        sop.state = "mango"
        sop.start()
        OperatorStart.assert_not_called()
        sop.state = "ready"
        sop.start()
        OperatorStart.assert_called_once()

    @patch("smtm.Operator.start")
    def test_start_should_call_analyzer_make_start_point(self, OperatorStart):
        operator = SimulationOperator()
        analyzer_mock = Mock()
        analyzer_mock.make_start_point = MagicMock()
        trader_mock = Mock()
        dp_mock = Mock()
        strategy_mock = Mock()
        operator.initialize(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.start()
        OperatorStart.assert_called_once()
        analyzer_mock.make_start_point.assert_called_once()

    @patch("smtm.Operator.stop")
    def test_stop_call_super_stop(self, OperatorStop):
        sop = SimulationOperator()
        sop.stop()
        OperatorStop.assert_called_once()


class SimulationOperatorTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.threading_mock = self.patcher.start()
        self.timer_mock = Mock()
        self.threading_mock.return_value = self.timer_mock

    def tearDown(self):
        self.patcher.stop()

    def test_excute_trading_should_call_get_info_and_set_timer(self):
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
        operator.initialize_simulation(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator.state = "running"
        operator._excute_trading(None)
        dp_mock.get_info.assert_called_once()
        self.assertEqual(operator.turn, 1)
        analyzer_mock.put_trading_info.assert_called_once_with("mango")

    def test_excute_trading_should_call_trader_send_request_and_strategy_update_result(self):
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
        operator.initialize_simulation(dp_mock, strategy_mock, trader_mock, analyzer_mock)
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
        operator = SimulationOperator()
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
        operator.initialize_simulation(dp_mock, strategy_mock, trader_mock, analyzer_mock)
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
        self.assertEqual(operator.state, "terminated")

    def test_excute_trading_should_NOT_call_trader_send_request_when_request_is_None(self):
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
        operator.initialize_simulation(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator._excute_trading(None)
        trader_mock.send_request.assert_not_called()

    def test_get_score_should_call_work_post_task_with_correct_task(self):
        operator = SimulationOperator()
        strategy = MagicMock()
        operator.initialize("banana", strategy, "orange", "mango")
        operator.worker = MagicMock()
        operator.state = "running"
        operator.get_score("dummy")
        operator.worker.post_task.assert_called_once_with({"runnable": ANY, "callback": "dummy"})

        operator.analyzer = MagicMock()
        operator.analyzer.get_return_report.return_value = "grape"
        task = {"runnable": MagicMock(), "callback": MagicMock()}
        runnable = operator.worker.post_task.call_args[0][0]["runnable"]
        runnable(task)
        operator.analyzer.get_return_report.assert_called_once()
        task["callback"].assert_called_once_with("grape")

    def test_get_score_call_callback_with_last_report_when_state_is_NOT_running(self):
        operator = SimulationOperator()
        strategy = MagicMock()
        operator.initialize("banana", strategy, "orange", "mango")
        operator.worker = MagicMock()
        operator.state = "pear"
        operator.last_report = {"summary": "apple_report"}
        callback = MagicMock()
        operator.get_score(callback)
        operator.worker.post_task.assert_not_called()
        callback.assert_called_once_with("apple_report")
