import os
import unittest
from smtm import BithumbTrader
from unittest.mock import *


class BithumbTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_send_request_should_call_worker_post_task_correctly(self):
        trader = BithumbTrader()
        trader.worker = MagicMock()

        trader.send_request("mango", "banana")

        trader.worker.post_task.assert_called_once()
        called_arg = trader.worker.post_task.call_args[0][0]
        self.assertEqual(called_arg["runnable"], trader._execute_order)
        self.assertEqual(called_arg["request"], "mango")
        self.assertEqual(called_arg["callback"], "banana")

    def test_get_account_info_should_return_correct_result(self):
        trader = BithumbTrader()
        dummy_respone = {"data": {"total_krw": 123456789}}
        dummy_respone["data"][trader.MARKET_KEY] = 789
        expected_result = {"balance": 123456789.0, "asset": {}, "date_time": ANY}
        expected_result["asset"][trader.MARKET] = (800.0, 789.0)
        trader.query_latest_trade = MagicMock(
            return_value={
                "status": "0000",
                "data": [
                    {
                        "transaction_date": "2018-04-10 17:47:46",
                        "type": "bid",
                        "units_traded": "1.0",
                        "price": "800",
                        "total": "6779000",
                    }
                ],
            }
        )
        trader._query_balance = MagicMock(return_value=dummy_respone)

        result = trader.get_account_info()

        trader._query_balance.assert_called_once_with(trader.MARKET)
        self.assertEqual(result, expected_result)

    def test_get_account_info_should_raise_UserWarning_when_retreive_failed(self):
        trader = BithumbTrader()
        dummy_respone = {"data": {"total_krw": 123456789}}
        dummy_respone["data"][trader.MARKET_KEY] = 789
        expected_result = {"balance": 123456789, "asset": {}}
        expected_result["asset"][trader.MARKET] = ("800", 789)
        trader.query_latest_trade = MagicMock()
        trader._query_balance = MagicMock(return_value=None)

        with self.assertRaises(UserWarning):
            result = trader.get_account_info()

    def test__execute_order_handle_task_correctly_with_limit_order(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": "kiwi",
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_limit_order.assert_called_once_with(trader.MARKET, True, 500, 0.0001)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.request_map["apple"]["order_id"], "apple_order_id")
        self.assertEqual(trader.request_map["apple"]["callback"], "kiwi")
        self.assertEqual(trader.request_map["apple"]["result"], "banana")

    def test__execute_orderr_handle_task_correctly_with_market_price_sell_order(self):
        dummy_task = {
            "request": {"id": "apple", "price": None, "amount": 0.0001, "type": "sell"},
            "callback": "kiwi",
        }
        trader = BithumbTrader()
        trader._send_market_price_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_market_price_order.assert_called_once_with(trader.MARKET, False, 0.0001)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.request_map["apple"]["order_id"], "apple_order_id")
        self.assertEqual(trader.request_map["apple"]["callback"], "kiwi")
        self.assertEqual(trader.request_map["apple"]["result"], "banana")

    def test__execute_order_handle_task_correctly_with_market_price_buy_order(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": None, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_market_price_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.query_latest_trade = MagicMock(
            return_value={
                "status": "0000",
                "data": [
                    {
                        "transaction_date": "2018-04-10 17:47:46",
                        "type": "bid",
                        "units_traded": "1.0",
                        "price": "100",
                        "total": "6779000",
                    }
                ],
            }
        )

        trader._execute_order(dummy_task)
        trader.query_latest_trade.assert_called_once_with(trader.MARKET)
        trader._send_market_price_order.assert_called_once_with(trader.MARKET, True, 5.0)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.request_map["apple"]["order_id"], "apple_order_id")
        self.assertEqual(trader.request_map["apple"]["result"], "banana")

    def test__execute_order_call_callback_with_error_when_market_price_buy_order_return_None(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": None, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_market_price_buy_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.query_latest_trade = MagicMock(return_value=None)

        trader._execute_order(dummy_task)
        trader.query_latest_trade.assert_called_once_with(trader.MARKET)
        trader._send_market_price_buy_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        dummy_task["callback"].assert_called_once_with("error!")

    def test__execute_order_handle_task_correctly_with_invalid_order(self):
        dummy_invalid_task1 = {
            "request": {"id": "apple", "price": None, "amount": None, "type": "buy"},
            "callback": MagicMock(),
        }
        dummy_invalid_task2 = {
            "request": {"id": "apple", "price": None, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        dummy_invalid_task3 = {
            "request": {"id": "apple", "price": 500, "amount": None, "type": "sell"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._create_success_result = MagicMock()
        trader._start_timer = MagicMock()
        trader._execute_order(dummy_invalid_task1)
        trader._execute_order(dummy_invalid_task2)
        trader._execute_order(dummy_invalid_task3)

        dummy_invalid_task1["callback"].assert_called_once_with("error!")
        dummy_invalid_task2["callback"].assert_called_once_with("error!")
        dummy_invalid_task3["callback"].assert_called_once_with("error!")
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()

    def test__create_success_result_return_correct_result(self):
        dummy_request = {"id": "mango", "type": "banana", "price": 500, "amount": 0.12345}
        trader = BithumbTrader()
        success_result = trader._create_success_result(dummy_request)

        self.assertEqual(success_result["request"]["id"], dummy_request["id"])
        self.assertEqual(success_result["type"], dummy_request["type"])
        self.assertEqual(success_result["price"], dummy_request["price"])
        self.assertEqual(success_result["amount"], dummy_request["amount"])
        self.assertEqual(success_result["msg"], "success")

    @patch("threading.Timer")
    def test_start_timer_should_start_Timer(self, mock_timer):
        trader = BithumbTrader()
        trader.worker = MagicMock()

        trader._start_timer()

        mock_timer.assert_called_once_with(trader.RESULT_CHECKING_INTERVAL, ANY)
        callback = mock_timer.call_args[0][1]
        callback()
        trader.worker.post_task.assert_called_once_with({"runnable": trader._query_order_result})

    def test_stop_timer_should_call_cancel(self):
        trader = BithumbTrader()
        timer_mock = MagicMock()
        trader.timer = timer_mock

        trader._stop_timer()

        timer_mock.cancel.assert_called_once()
        self.assertEqual(trader.timer, None)

    def test__query_order_result_should_call_callback_and_keep_waiting_request(self):
        dummy_result = [
            {
                "status": "0000",
                "data": {
                    "order_id": "mango",
                    "order_status": "Completed",
                    "order_qty": 0.005,
                    "order_date": 1234567890,
                    "contract": "contract_mango",
                },
            },
            {
                "status": "0000",
                "data": {
                    "order_id": "banana",
                    "order_status": "wait",
                    "order_qty": 0.007,
                    "order_date": 1234567890,
                },
            },
            {
                "status": "0000",
                "data": {
                    "order_id": "apple",
                    "order_status": "cancel",
                    "order_qty": 0.00009,
                    "order_date": 1234567890,
                },
            },
        ]
        dummy_request_mango = {
            "order_id": "mango",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"id": "mango_result", "price": None},
        }
        dummy_request_banana = {
            "order_id": "banana",
            "request": {"id": "banana_id"},
            "callback": MagicMock(),
            "result": {"id": "banana_result", "price": None},
        }
        dummy_request_apple = {
            "order_id": "apple",
            "request": {"id": "apple_id"},
            "callback": MagicMock(),
            "result": {"id": "apple_result", "price": None},
        }
        trader = BithumbTrader()
        trader._query_order = MagicMock(side_effect=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.request_map["mango"] = dummy_request_mango
        trader.request_map["banana"] = dummy_request_banana
        trader.request_map["apple"] = dummy_request_apple
        trader._convert_timestamp = MagicMock(return_value="today")
        trader._get_total_trading_price = MagicMock(return_value=777)

        trader._query_order_result(None)

        mango_result = dummy_request_mango["callback"].call_args[0][0]
        self.assertEqual(mango_result["date_time"], "today")
        self.assertEqual(mango_result["id"], "mango_result")
        self.assertEqual(mango_result["price"], 777)
        dummy_request_mango["callback"].assert_called_once()

        self.assertEqual(len(trader.request_map), 2)
        self.assertEqual(trader.request_map["banana"]["request"]["id"], "banana_id")
        self.assertEqual(trader.request_map["apple"]["request"]["id"], "apple_id")
        trader._stop_timer.assert_called_once()
        trader._start_timer.assert_called_once()
        trader._query_order.assert_called()

    def test__send_limit_order_should_call_bithumbApiCall_with_correct_query(self):
        trader = BithumbTrader()
        expected_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
            "type": "bid",
            "units": "0.0051",
            "price": "500",
        }
        trader.bithumb_api_call = MagicMock()
        trader._send_limit_order("apple", True, 500, 0.00512)
        trader.bithumb_api_call.assert_called_once_with("/trade/place", expected_query)

    def test__send_market_price_order_should_call_bithumbApiCall_with_correct_query(self):
        trader = BithumbTrader()
        expected_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
            "units": "0.0051",
        }
        trader.bithumb_api_call = MagicMock()
        trader._send_market_price_order("apple", True, 0.00512)
        trader.bithumb_api_call.assert_called_once_with("/trade/market_buy", expected_query)

        trader.bithumb_api_call = MagicMock()
        trader._send_market_price_order("apple", False, 0.00512)
        trader.bithumb_api_call.assert_called_once_with("/trade/market_sell", expected_query)

    def test__query_order_should_call_bithumbApiCall_with_correct_query(self):
        trader = BithumbTrader()
        expected_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
            "order_id": "apple-007",
        }
        trader.bithumb_api_call = MagicMock()
        trader._query_order("apple")
        trader.bithumb_api_call.assert_not_called()

        trader.bithumb_api_call = MagicMock()
        trader._query_order("apple", "apple-007")
        trader.bithumb_api_call.assert_called_once_with("/info/order_detail", expected_query)

    def test__query_balance_should_call_bithumbApiCall_with_correct_query(self):
        trader = BithumbTrader()
        expected_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
        }
        trader.bithumb_api_call = MagicMock()
        trader._query_balance("apple")
        trader.bithumb_api_call.assert_called_once_with("/info/balance", expected_query)

    @patch("requests.get")
    def test_query_latest_trade_should_send_http_request_correctly(self, mock_get):
        trader = BithumbTrader()
        expected_url = trader.SERVER_URL + "/public/transaction_history/apple"

        trader.query_latest_trade("apple")
        mock_get.assert_called_once_with(expected_url, params={"count": "1"})

    @patch("requests.post")
    def test_bithumb_api_call_should_send_http_request_correctly(self, mock_post):
        dummy_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
        }
        trader = BithumbTrader()
        expected_url = trader.SERVER_URL + "get/apple"
        expected_data = "endpoint=get%2Fapple&order_currency=apple&payment_currency=KRW"
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value="apple_result")
        mock_post.return_value = mock_response

        self.assertEqual(trader.bithumb_api_call("get/apple", dummy_query), "apple_result")
        mock_response.raise_for_status.assert_called_once()
        mock_post.assert_called_once_with(expected_url, headers=ANY, data=expected_data)
        called_headers = mock_post.call_args[1]["headers"]
        self.assertEqual(called_headers["Api-Key"], trader.ACCESS_KEY)
        self.assertIsNotNone(called_headers["Api-Sign"])
        self.assertIsNotNone(called_headers["Api-Nonce"])
        self.assertEqual(called_headers["Content-Type"], "application/x-www-form-urlencoded")

    @patch("requests.post")
    def test_bithumb_api_call_return_None_when_invalid_data_received_from_server(self, mock_post):
        def raise_exception():
            raise ValueError("RequestException dummy exception")

        class DummyResponse:
            pass

        mock_response = DummyResponse()
        mock_response.raise_for_status = raise_exception
        mock_response.json = MagicMock(return_value="apple_result")
        mock_post.return_value = mock_response

        dummy_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
        }
        trader = BithumbTrader()
        expected_url = trader.SERVER_URL + "get/apple"
        expected_data = "endpoint=get%2Fapple&order_currency=apple&payment_currency=KRW"

        self.assertEqual(trader.bithumb_api_call("get/apple", dummy_query), None)
