import unittest
from datetime import datetime, timedelta
from smtm import Operator
from unittest.mock import *


class OperatorInitializeTests(unittest.TestCase):
    def setUp(self):
        self.operator = Operator()
        self.strategy_mock = MagicMock()
        self.trader_mock = MagicMock()
        self.analyzer_mock = MagicMock()

    def tearDown(self):
        pass

    def test_initialize_keep_object_correctly(self):
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )
        self.assertEqual(self.operator.data_provider, "mango")
        self.assertEqual(self.operator.strategy, self.strategy_mock)
        self.assertEqual(self.operator.trader, self.trader_mock)
        self.assertEqual(self.operator.analyzer, self.analyzer_mock)
        self.strategy_mock.initialize.assert_called_once_with("banana", add_spot_callback=ANY)

    def test_initialize_should_call_analyzer_initialize_with_trader(self):
        self.trader_mock.get_account_info = "orange"
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )
        self.analyzer_mock.initialize.assert_called_once_with("orange")
        self.strategy_mock.initialize.assert_called_once_with("banana", add_spot_callback=ANY)

    def test_initialize_should_call_strategy_initialize_with_add_spot_callback(self):
        self.trader_mock.get_account_info = "orange"
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )
        self.strategy_mock.initialize.assert_called_once_with("banana", add_spot_callback=ANY)
        self.strategy_mock.initialize.call_args[1]["add_spot_callback"]("spot_date_time", 777)
        self.analyzer_mock.add_drawing_spot.assert_called_once_with("spot_date_time", 777)

    def test_initialize_do_nothing_when_state_is_NOT_None(self):
        self.operator.state = "mango"
        self.operator.initialize("mango", self.strategy_mock, "orange", "grape", "banana")
        self.assertEqual(self.operator.data_provider, None)
        self.assertEqual(self.operator.strategy, None)
        self.assertEqual(self.operator.trader, None)
        self.assertEqual(self.operator.analyzer, None)

    def test_initialize_should_update_tag_correctly(self):
        self.trader_mock.NAME = "mango_tr"
        self.strategy_mock.CODE = "SPR"
        expected_tag = "-mango_tr-SPR"
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )

        self.assertEqual(self.operator.tag[-len(expected_tag) :], expected_tag)

    def test_setup_set_interval_correctly(self):
        self.operator.set_interval(10)
        self.assertEqual(self.operator.interval, 10)

        self.operator.set_interval(39)
        self.assertEqual(self.operator.interval, 39)

    def test_start_return_false_without_initialization(self):
        self.assertEqual(self.operator.start(), False)

    def test_start_should_call_worker_start_and_post_task(self):
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )
        self.operator.worker = MagicMock()
        self.operator.start()
        self.operator.worker.start.assert_called_once()
        self.operator.worker.post_task.assert_called_once_with(ANY)
        called_task = self.operator.worker.post_task.call_args[0][0]
        self.assertEqual(called_task["runnable"], self.operator._execute_trading)

    def test_start_should_call_analyzer_make_start_point(self):
        self.operator.initialize(
            "mango", self.strategy_mock, self.trader_mock, self.analyzer_mock, "banana"
        )
        self.operator.worker = MagicMock()
        self.operator.start()
        self.analyzer_mock.make_start_point.assert_called_once()


class OperatorExecuteTradingTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.threading_mock = self.patcher.start()
        self.timer_mock = Mock()
        self.threading_mock.return_value = self.timer_mock
        self.operator = Operator()
        self.analyzer_mock = MagicMock()
        self.strategy_mock = MagicMock()
        self.trader_mock = MagicMock()
        self.dp_mock = MagicMock()

    def tearDown(self):
        self.patcher.stop()

    def test_execute_trading_should_call_get_info_and_set_timer(self):
        self.dp_mock.get_info = MagicMock(return_value="mango")
        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        self.strategy_mock.get_request = MagicMock(return_value=dummy_request)
        self.trader_mock.send_request = MagicMock()

        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.set_interval(27)
        self.operator.state = "running"
        self.operator._periodic_internal_get_score = MagicMock()
        self.operator._execute_trading(None)

        self.threading_mock.assert_called_once_with(27, ANY)
        self.timer_mock.start.assert_called_once()
        self.dp_mock.get_info.assert_called_once()
        self.analyzer_mock.put_trading_info.assert_called_once_with("mango")
        if self.operator.PERIODIC_RECORD is True:
            self.operator._periodic_internal_get_score.assert_called_once()
        else:
            self.operator._periodic_internal_get_score.assert_not_called()

    def test_execute_trading_should_call_trader_send_request_and_strategy_update_result(self):
        self.dp_mock.get_info = MagicMock(return_value="mango")
        dummy_request = {"id": "mango", "type": "orange", "price": 500, "amount": 10}
        self.strategy_mock.update_result = MagicMock()
        self.strategy_mock.get_request = MagicMock(return_value=dummy_request)

        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.set_interval(27)
        self.operator.state = "running"
        self.operator._execute_trading(None)

        self.analyzer_mock.put_requests.assert_called_once_with(dummy_request)
        self.strategy_mock.update_trading_info.assert_called_once_with(ANY)
        self.trader_mock.send_request.assert_called_once_with(ANY, ANY)
        self.trader_mock.send_request.call_args[0][1]({"id": "mango", "state": "done"})
        self.trader_mock.send_request.call_args[0][1]({"id": "orange", "state": "requested"})
        self.strategy_mock.update_result.assert_called()
        self.analyzer_mock.put_result.assert_called_once_with({"id": "mango", "state": "done"})

    def test_execute_trading_should_NOT_call_trader_send_request_when_request_is_None(self):
        self.strategy_mock.get_request = MagicMock(return_value=None)

        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.set_interval(27)
        self.operator.state = "running"
        self.operator._execute_trading(None)

        self.analyzer_mock.put_requests.assert_not_called()
        self.trader_mock.send_request.assert_not_called()
        self.analyzer_mock.put_result.assert_not_called()

    def test_execute_trading_should_call_on_exception_when_exception_occured(self):
        def make_exception():
            raise Exception("mango")

        self.dp_mock.get_info = make_exception
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.on_exception = MagicMock()

        with self.assertRaises(Exception) as exception:
            self.operator._execute_trading(None)
        self.assertEqual(str(exception.exception), "Something bad happened during trading")

        self.operator.on_exception.assert_called_once_with("Something bad happened during trading")


class OperatorStopTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_stop_should_cancel_timer_and_set_variable_correctly(self):
        operator = Operator()
        operator.analyzer = MagicMock()
        operator.trader = MagicMock()
        operator.state = "running"
        operator.timer = MagicMock()
        operator.data_provider = MagicMock()
        operator.is_timer_running = True
        operator.stop()
        self.assertFalse(operator.is_timer_running)
        self.assertEqual(operator.state, "terminating")
        operator.timer.cancel.assert_called_once()
        operator.analyzer.create_report.assert_called_once_with(tag=operator.tag)
        operator.trader.cancel_all_requests.assert_called_once()

    def test_stop_do_nothing_when_state_is_not_running(self):
        operator = Operator()
        operator.analyzer = MagicMock()
        operator.state = "ready"
        operator.is_timer_running = True
        operator.stop()
        self.assertEqual(operator.state, "ready")
        self.assertTrue(operator.is_timer_running)

    def test_stop_should_call_worker_stop_and_register_on_terminated(self):
        operator = Operator()
        operator.state = "running"
        operator.timer = MagicMock()
        operator.worker = MagicMock()
        operator.analyzer = MagicMock()
        operator.trader = MagicMock()
        operator.data_provider = MagicMock()
        operator.data_provider.get_info.return_value = "mango"
        operator.stop()
        operator.worker.stop.assert_called_once()
        operator.worker.register_on_terminated.assert_called_once_with(ANY)
        operator.data_provider.get_info.assert_called_once_with()
        callback = operator.worker.register_on_terminated.call_args[0][0]
        self.assertEqual(operator.state, "terminating")
        callback()
        self.assertEqual(operator.state, "ready")
        operator.trader.cancel_all_requests.assert_called_once()
        operator.analyzer.put_trading_info.assert_called_once_with("mango")

    def test_stop_should_call_create_report_and_return_result_correctly(self):
        operator = Operator()
        operator.worker = MagicMock()
        operator.data_provider = MagicMock()
        operator.trader = MagicMock()
        operator.analyzer = MagicMock()
        operator.analyzer.create_report.return_value = "mango_result"
        operator.state = "running"
        operator.tag = "mango"
        result = operator.stop()
        operator.analyzer.create_report.assert_called_once_with(tag="mango")
        self.assertEqual(result, "mango_result")


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.threading_mock = self.patcher.start()
        self.timer_mock = Mock()
        self.threading_mock.return_value = self.timer_mock
        self.operator = Operator()
        self.analyzer_mock = MagicMock()
        self.strategy_mock = MagicMock()
        self.trader_mock = MagicMock()
        self.dp_mock = MagicMock()

    def tearDown(self):
        self.patcher.stop()

    def test_start_timer_should_start_Timer(self):
        timer_mock = MagicMock()
        self.threading_mock.return_value = timer_mock
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )

        self.operator.worker = MagicMock()
        self.operator.set_interval(27)
        self.operator.state = "running"
        self.operator._start_timer()

        self.threading_mock.assert_called_once_with(27, ANY)
        timer_mock.start.assert_called_once()
        timer_callback = self.threading_mock.call_args[0][1]
        timer_callback()
        self.operator.worker.post_task.assert_called_once_with(ANY)
        self.assertEqual(
            self.operator.worker.post_task.call_args[0][0]["runnable"],
            self.operator._execute_trading,
        )

    def test_start_timer_should_NOT_start_Timer_when_state_is_NOT_running(self):
        timer_mock = MagicMock()
        self.threading_mock.return_value = timer_mock
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.set_interval(27)
        self.operator.state = "ready"
        self.operator._start_timer()

        self.threading_mock.assert_not_called()
        timer_mock.start.assert_not_called()

    def test_start_timer_should_set_is_timer_running_true(self):
        timer_mock = MagicMock()
        self.threading_mock.return_value = timer_mock
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.state = "running"
        self.operator._start_timer()
        self.assertEqual(self.operator.is_timer_running, True)

    def test_get_score_should_call_work_post_task_with_correct_task(self):
        timer_mock = MagicMock()
        self.threading_mock.return_value = timer_mock
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.worker = MagicMock()
        self.operator.state = "running"
        self.operator.get_score("dummy", index_info=7)
        self.operator.worker.post_task.assert_called_once_with(
            {"runnable": ANY, "callback": "dummy", "index_info": 7}
        )

        self.analyzer_mock.get_return_report.return_value = "grape"
        task = {"runnable": MagicMock(), "callback": MagicMock(), "index_info": 5}
        runnable = self.operator.worker.post_task.call_args[0][0]["runnable"]
        runnable(task)
        self.analyzer_mock.get_return_report.assert_called_once_with(
            graph_filename=ANY, index_info=5
        )
        task["callback"].assert_called_once_with("grape")

    def test_get_score_do_nothing_when_state_is_NOT_running(self):
        timer_mock = MagicMock()
        self.threading_mock.return_value = timer_mock
        self.operator.initialize(
            self.dp_mock, self.strategy_mock, self.trader_mock, self.analyzer_mock, 100
        )
        self.operator.worker = MagicMock()
        self.operator.state = "pear"
        self.operator.get_score("dummy")
        self.operator.worker.post_task.assert_not_called()

    def test__periodic_internal_get_score_should_call_get_score_correctlye(self):
        operator = Operator()
        operator.get_score = MagicMock()
        operator.last_periodic_time = datetime.now()
        operator._periodic_internal_get_score()
        operator.get_score.assert_not_called()

        operator.last_periodic_time = datetime.now() - timedelta(
            seconds=operator.PERIODIC_RECORD_INTERVAL_SEC + 1
        )
        operator._periodic_internal_get_score()
        operator.get_score.assert_called_with(
            ANY, index_info=operator.PERIODIC_RECORD_INFO, graph_tag=ANY
        )

    def test_get_trading_results_return_result_of_analyzer_get_trading_results(self):
        operator = Operator()
        operator.analyzer = MagicMock()
        operator.analyzer.get_trading_results.return_value = "orange"
        self.assertEqual(operator.get_trading_results(), "orange")
        operator.analyzer.get_trading_results.assert_called_once()
