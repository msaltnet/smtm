import os
import unittest
from smtm import UpbitTrader
from unittest.mock import *


class UpditTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch.dict(os.environ, {"UPBIT_OPEN_API_ACCESS_KEY": "mango"})
    @patch.dict(os.environ, {"UPBIT_OPEN_API_SECRET_KEY": "orange"})
    @patch.dict(os.environ, {"UPBIT_OPEN_API_SERVER_URL": "apple"})
    def test_init_update_os_environ_value(self):
        trader = UpbitTrader()
        self.assertEqual(trader.ACCESS_KEY, "mango")
        self.assertEqual(trader.SECRET_KEY, "orange")
        self.assertEqual(trader.SERVER_URL, "apple")

    def test_send_request_should_call_worker_post_task_correctly(self):
        trader = UpbitTrader()
        trader.worker = MagicMock()
        trader.send_request("mango", "banana")
        trader.worker.post_task.assert_called_once()
        called_arg = trader.worker.post_task.call_args[0][0]
        self.assertEqual(called_arg["runnable"], trader._excute_order)
        self.assertEqual(called_arg["request"], "mango")
        self.assertEqual(called_arg["callback"], "banana")

    def test_send_account_info_request_should_call_worker_post_task_correctly(self):
        trader = UpbitTrader()
        trader.worker = MagicMock()
        trader.send_account_info_request("banana")
        trader.worker.post_task.assert_called_once()
        called_arg = trader.worker.post_task.call_args[0][0]
        self.assertEqual(called_arg["runnable"], trader._excute_query)
        self.assertEqual(called_arg["callback"], "banana")

    def test__excute_order_handle_task_correctly(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": "kiwi",
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock(return_value={"uuid": "mango"})
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader._excute_order(dummy_task)
        trader._send_order.assert_called_once_with(trader.MARKET, True, 500, 0.0001)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.request_map["apple"]["uuid"], "mango")
        self.assertEqual(trader.request_map["apple"]["callback"], "kiwi")
        self.assertEqual(trader.request_map["apple"]["result"], "banana")

    def test__excute_order_should_call_callback_with_error_when__send_order_return_None(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock(return_value=None)
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader._excute_order(dummy_task)
        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_order.assert_called_once_with(trader.MARKET, True, 500, 0.0001)
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        self.assertEqual(len(trader.request_map), 0)

    def test__excute_query_handle_task_correctly(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        dummy_respone = [
            {"currency": "KRW", "balance": 123456789},
            {"currency": "APPLE", "balance": 500, "avg_buy_price": 23456},
        ]
        trader = UpbitTrader()
        trader._query_account = MagicMock(return_value=dummy_respone)
        trader._excute_query(dummy_task)
        trader._query_account.assert_called_once()
        dummy_task["callback"].assert_called_once_with(
            {"balance": 123456789, "asset": {"APPLE": (23456, 500)}}
        )

    def test__excute_query_handle_None_response(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        dummy_respone = None
        trader = UpbitTrader()
        trader._query_account = MagicMock(return_value=dummy_respone)
        trader._excute_query(dummy_task)
        trader._query_account.assert_called_once()
        dummy_task["callback"].assert_called_once_with("error!")

    def test__create_success_result_return_correct_result(self):
        dummy_request = {"id": "mango", "type": "banana", "price": 500, "amount": 0.12345}
        trader = UpbitTrader()
        success_result = trader._create_success_result(dummy_request)
        self.assertEqual(success_result["request"]["id"], dummy_request["id"])
        self.assertEqual(success_result["type"], dummy_request["type"])
        self.assertEqual(success_result["price"], dummy_request["price"])
        self.assertEqual(success_result["amount"], dummy_request["amount"])
        self.assertEqual(success_result["msg"], "success")

    @patch("threading.Timer")
    def test_start_timer_should_start_Timer(self, mock_timer):
        trader = UpbitTrader()
        trader.worker = MagicMock()
        trader._start_timer()
        mock_timer.assert_called_once_with(trader.RESULT_CHECKING_INTERVAL, ANY)
        callback = mock_timer.call_args[0][1]
        callback()
        trader.worker.post_task.assert_called_once_with({"runnable": trader._query_order_result})

    def test_stop_timer_should_call_cancel(self):
        trader = UpbitTrader()
        timer_mock = MagicMock()
        trader.timer = timer_mock
        trader._stop_timer()
        timer_mock.cancel.assert_called_once()
        self.assertEqual(trader.timer, None)

    def test__query_order_result(self):
        dummy_result = [
            {"uuid": "mango", "state": "done", "created_at": "today"},
            {"uuid": "banana", "state": "wait", "created_at": "tomorrow"},
            {"uuid": "apple", "state": "cancel", "created_at": "yesterday"},
        ]
        dummy_request_mango = {
            "uuid": "mango",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"id": "mango_result"},
        }
        dummy_request_banana = {
            "uuid": "banana",
            "request": {"id": "banana_id"},
            "callback": MagicMock(),
            "result": {"id": "banana_result"},
        }
        dummy_request_apple = {
            "uuid": "apple",
            "request": {"id": "apple_id"},
            "callback": MagicMock(),
            "result": {"id": "apple_result"},
        }
        trader = UpbitTrader()
        trader._query_order_list = MagicMock(return_value=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.request_map["mango"] = dummy_request_mango
        trader.request_map["banana"] = dummy_request_banana
        trader.request_map["apple"] = dummy_request_apple
        trader._query_order_result(None)
        mango_result = dummy_request_mango["callback"].call_args[0][0]
        self.assertEqual(mango_result["date_time"], "today")
        self.assertEqual(mango_result["id"], "mango_result")
        dummy_request_mango["callback"].assert_called_once()

        apple_result = dummy_request_apple["callback"].call_args[0][0]
        self.assertEqual(apple_result["date_time"], "yesterday")
        self.assertEqual(apple_result["id"], "apple_result")
        dummy_request_mango["callback"].assert_called_once()

        self.assertEqual(len(trader.request_map), 1)
        self.assertEqual(trader.request_map["banana"]["request"]["id"], "banana_id")
        trader._stop_timer.assert_called_once()
        trader._start_timer.assert_called_once()
