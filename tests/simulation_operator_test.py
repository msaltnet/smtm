import unittest
from smtm import SimulationOperator
from unittest.mock import *


class SimulationOperatorTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.threading_mock = self.patcher.start()
        self.timer_mock = Mock()
        self.threading_mock.return_value = self.timer_mock

    def tearDown(self):
        self.patcher.stop()

    def test_execute_trading_should_call_get_info_and_set_timer(self):
        operator = SimulationOperator()
        self.assertEqual(operator.turn, 0)
        analyzer_mock = Mock()
        analyzer_mock.put_trading_info = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.CODE = "MAG"
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.NAME = "orange_tr"
        trader_mock.send_request = MagicMock()
        operator.initialize(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator.state = "running"
        operator._execute_trading(None)
        dp_mock.get_info.assert_called_once()
        self.assertEqual(operator.turn, 1)
        analyzer_mock.put_trading_info.assert_called_once_with("mango")

    def test_execute_trading_should_call_trader_send_request_and_strategy_update_result(self):
        operator = SimulationOperator()
        analyzer_mock = Mock()
        analyzer_mock.put_requests = MagicMock()
        analyzer_mock.put_result = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.CODE = "MAG"
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.update_result = MagicMock()
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.NAME = "orange_tr"
        trader_mock.send_request = MagicMock()
        operator.initialize(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator._execute_trading(None)

        dummy_result = {"name": "mango", "type": "buy", "msg": "success"}
        analyzer_mock.put_requests.assert_called_once_with(dummy_request)
        strategy_mock.update_trading_info.assert_called_once_with(ANY)
        trader_mock.send_request.assert_called_once_with(ANY, ANY)
        trader_mock.send_request.call_args[0][1](dummy_result)
        strategy_mock.update_result.assert_called_once_with(dummy_result)
        analyzer_mock.put_result.assert_called_once_with(dummy_result)

    def test_execute_trading_should_call_creat_report_and_call_stop_when_result_msg_game_over(self):
        operator = SimulationOperator()
        analyzer_mock = Mock()
        analyzer_mock.put_requests = MagicMock()
        analyzer_mock.put_result = MagicMock()
        analyzer_mock.create_report = MagicMock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")

        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        strategy_mock = Mock()
        strategy_mock.CODE = "MAG"
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.update_result = MagicMock()
        strategy_mock.get_request = MagicMock(return_value=dummy_request)
        trader_mock = Mock()
        trader_mock.NAME = "orange_tr"
        trader_mock.send_request = MagicMock()
        operator.initialize(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator._execute_trading(None)
        analyzer_mock.put_requests.assert_called_once_with(dummy_request)
        strategy_mock.update_trading_info.assert_called_once_with(ANY)
        trader_mock.send_request.assert_called_once_with(ANY, ANY)

        dummy_result = {"msg": "game-over"}
        trader_mock.send_request.call_args[0][1](dummy_result)
        strategy_mock.update_result.assert_not_called()
        analyzer_mock.put_result.assert_not_called()
        analyzer_mock.create_report.assert_called_once()
        self.assertEqual(operator.state, "simulation_terminated")

    def test_execute_trading_should_NOT_call_trader_send_request_when_request_is_None(self):
        operator = SimulationOperator()
        analyzer_mock = Mock()
        dp_mock = Mock()
        dp_mock.initialize = MagicMock(return_value="")
        dp_mock.get_info = MagicMock(return_value="mango")
        strategy_mock = Mock()
        strategy_mock.CODE = "MAG"
        strategy_mock.update_trading_info = MagicMock(return_value="orange")
        strategy_mock.get_request = MagicMock(return_value=None)
        trader_mock = Mock()
        trader_mock.NAME = "orange_tr"
        trader_mock.send_request = MagicMock()
        operator.initialize(dp_mock, strategy_mock, trader_mock, analyzer_mock)
        operator.set_interval(27)
        operator._execute_trading(None)
        trader_mock.send_request.assert_not_called()

    def test_get_score_should_call_work_post_task_with_correct_task(self):
        operator = SimulationOperator()
        strategy = MagicMock()
        trader = MagicMock()
        analyzer = MagicMock()
        operator.initialize("banana", strategy, trader, analyzer)
        operator.worker = MagicMock()
        operator.state = "running"
        operator.get_score("dummy", index_info=7)
        operator.worker.post_task.assert_called_once_with(
            {"runnable": ANY, "callback": "dummy", "index_info": 7}
        )

        operator.analyzer = MagicMock()
        operator.analyzer.get_return_report.return_value = "grape"
        task = {"runnable": MagicMock(), "callback": MagicMock(), "index_info": 10}
        runnable = operator.worker.post_task.call_args[0][0]["runnable"]
        runnable(task)
        operator.analyzer.get_return_report.assert_called_once_with(
            graph_filename=ANY, index_info=10
        )
        task["callback"].assert_called_once_with("grape")

    def test_get_score_call_callback_with_last_report_when_state_is_NOT_running(self):
        operator = SimulationOperator()
        strategy = MagicMock()
        trader = MagicMock()
        analyzer = MagicMock()
        operator.initialize("banana", strategy, trader, analyzer)
        operator.worker = MagicMock()
        operator.state = "pear"
        operator.last_report = {"summary": "apple_report"}
        callback = MagicMock()
        operator.get_score(callback)
        operator.worker.post_task.assert_not_called()
        callback.assert_called_once_with("apple_report")

    def test__periodic_internal_get_score_should_call_get_score_correctlye(self):
        operator = SimulationOperator()
        operator.get_score = MagicMock()
        operator.last_periodic_turn = operator.current_turn
        operator._periodic_internal_get_score()
        operator.get_score.assert_not_called()

        operator.current_turn = operator.last_periodic_turn + operator.PERIODIC_RECORD_INTERVAL_TURN
        operator._periodic_internal_get_score()
        operator.get_score.assert_called_with(
            ANY, index_info=operator.PERIODIC_RECORD_INFO, graph_tag=ANY
        )
