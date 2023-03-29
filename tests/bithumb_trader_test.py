import unittest
from smtm import BithumbTrader
from unittest.mock import *


class BithumbTraderBalanceTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test__call_callback_update_balance_correctly_when_buy(self):
        trader = BithumbTrader()
        trader.balance = 550000
        trader.asset = (67000000, 1.000001)
        dummy_result = {
            "request": {
                "id": "mango_request_5678",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "buy",
            "price": "62000000",
            "amount": "0.0012345",
            "msg": "success",
            "state": "done",
        }
        dummy_callback = MagicMock()
        trader._call_callback(dummy_callback, dummy_result)

        self.assertEqual(trader.balance, 473423)
        self.assertEqual(trader.asset, (66993868.57231318, 1.001235))
        dummy_callback.assert_called_once_with(dummy_result)

    def test__call_callback_update_balance_correctly_when_sell(self):
        trader = BithumbTrader()
        trader.balance = 550000
        trader.asset = (67000000, 1.000001)
        dummy_result = {
            "request": {
                "id": "mango_request_5678",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "sell",
            "price": "62000000",
            "amount": "0.0012345",
            "msg": "success",
            "state": "done",
        }
        dummy_callback = MagicMock()
        trader._call_callback(dummy_callback, dummy_result)

        self.assertEqual(trader.balance, 626501)
        self.assertEqual(trader.asset, (67000000, 0.998766))
        dummy_callback.assert_called_once_with(dummy_result)

    def test__call_callback_NOT_update_when_type_is_not_done(self):
        trader = BithumbTrader()
        trader.balance = 550000
        trader.asset = (67000000, 1.000001)
        dummy_result = {
            "request": {
                "id": "mango_request_5678",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "sell",
            "price": "62000000",
            "amount": "0.0012345",
            "msg": "success",
            "state": "requested",
        }
        dummy_callback = MagicMock()
        trader._call_callback(dummy_callback, dummy_result)

        self.assertEqual(trader.balance, 550000)
        self.assertEqual(trader.asset, (67000000, 1.000001))
        dummy_callback.assert_called_once_with(dummy_result)


class BithumbTraderCancelRequestTests(unittest.TestCase):
    def setUp(self):
        self.patcher_delete = patch("requests.delete")
        self.patcher_get = patch("requests.get")
        self.delete_mock = self.patcher_delete.start()
        self.get_mock = self.patcher_get.start()

    def tearDown(self):
        self.patcher_delete.stop()
        self.patcher_get.stop()

    def test_cancel_request_should_call__call_callback_when_order_is_traded_already(self):
        trader = BithumbTrader()
        trader._call_callback = MagicMock()
        dummy_request = {
            "order_id": "mango_id",
            "callback": MagicMock(),
            "result": {
                "state": "requested",
                "request": {
                    "id": "mango_request_1234",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": 888000.0,
                "amount": 0.0001234,
                "msg": "success",
            },
        }
        trader.order_map["mango_request_1234"] = dummy_request

        _cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(
            return_value={
                "data": {
                    "order_status": "Completed",
                    "order_id": "mango_id",
                    "state": "done",
                    "transaction_date": "1572497603668315",
                    "order_price": 888000,
                    "order_qty": 0.007,
                },
            }
        )
        trader.cancel_request("mango_request_1234")
        trader._query_order.assert_called_once_with("mango_id")

        self.assertEqual(trader._call_callback.call_args_list[0][0][0], dummy_request["callback"])
        mango_result = trader._call_callback.call_args_list[0][0][1]
        self.assertEqual(mango_result["date_time"], "2019-10-31T13:53:23")
        self.assertEqual(mango_result["price"], 888000)
        self.assertEqual(mango_result["type"], "buy")
        self.assertEqual(mango_result["state"], "done")
        self.assertEqual(mango_result["amount"], 0.007)

    def test_cancel_request_should_remove_request_even_when_cancel_nothing(self):
        trader = BithumbTrader()
        trader._call_callback = MagicMock()
        dummy_request = {
            "order_id": "mango_id",
            "callback": MagicMock(),
            "result": {
                "state": "requested",
                "request": {
                    "id": "mango_request_1234",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": 888000.0,
                "amount": 0.0001234,
                "msg": "success",
            },
        }
        trader.order_map["mango_request_1234"] = dummy_request

        _cancel_order = MagicMock(return_value="done")
        self.assertTrue("mango_id" not in trader.order_map)

    def test_cancel_all_requests_should_call_cancel_request_correctly(self):
        trader = BithumbTrader()
        dummy_request = "mango_request"
        trader.order_map["mango_request_1234"] = dummy_request
        trader.order_map["mango_request_5678"] = dummy_request
        trader.cancel_request = MagicMock()

        trader.cancel_all_requests()

        trader.cancel_request.assert_called()
        self.assertEqual(trader.cancel_request.call_args_list[0][0][0], "mango_request_1234")
        self.assertEqual(trader.cancel_request.call_args_list[1][0][0], "mango_request_5678")

    def test__cancel_order_should_call_bithumb_api_call_correctly(self):
        trader = BithumbTrader("BTC")
        trader.bithumb_api_call = MagicMock()
        expected_query = {
            "order_currency": trader.market,
            "payment_currency": trader.market_currency,
            "order_id": "mango_id",
        }

        trader._cancel_order("mango_id")

        trader.bithumb_api_call.assert_called_once_with("/trade/cancel", expected_query)


class BithumbTraderBasicTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test__create_success_result_return_correct_result(self):
        dummy_request = {"id": "mango", "type": "banana", "price": 500, "amount": 0.12345}
        success_result = BithumbTrader._create_success_result(dummy_request)

        self.assertEqual(success_result["request"]["id"], dummy_request["id"])
        self.assertEqual(success_result["type"], dummy_request["type"])
        self.assertEqual(success_result["price"], dummy_request["price"])
        self.assertEqual(success_result["amount"], dummy_request["amount"])
        self.assertEqual(success_result["msg"], "success")

    def test__convert_timestamp_return_correct_result(self):
        self.assertEqual(
            BithumbTrader._convert_timestamp("1572497603668315"), "2019-10-31T13:53:23"
        )
        self.assertEqual(
            BithumbTrader._convert_timestamp("1572797603668315"), "2019-11-04T01:13:23"
        )

    def test_send_request_should_call_worker_post_task_correctly(self):
        trader = BithumbTrader()
        trader.worker = MagicMock()

        trader.send_request(["mango", "orange"], "banana")

        trader.worker.post_task.assert_called()
        called_arg = trader.worker.post_task.call_args_list[0][0][0]
        self.assertEqual(called_arg["runnable"], trader._execute_order)
        self.assertEqual(called_arg["request"], "mango")
        self.assertEqual(called_arg["callback"], "banana")

        called_arg = trader.worker.post_task.call_args_list[1][0][0]
        self.assertEqual(called_arg["runnable"], trader._execute_order)
        self.assertEqual(called_arg["request"], "orange")
        self.assertEqual(called_arg["callback"], "banana")

    def test_get_account_info_should_return_correct_info(self):
        dummy_respone = [
            {"currency": "KRW", "balance": 123456789},
            {"currency": "APPLE", "balance": 500, "avg_buy_price": 23456},
        ]
        trader = BithumbTrader()
        trader.balance = 123456789
        trader.asset = (23456, 500)
        trader.market = "APPLE"
        trader.worker = MagicMock()
        trader.get_trade_tick = MagicMock(return_value={"status": "0000", "data": [{"price": 777}]})
        result = trader.get_account_info()

        self.assertEqual(result["balance"], 123456789)
        self.assertEqual(result["asset"], {"APPLE": (23456, 500)})
        self.assertEqual(result["quote"], {"APPLE": 777})
        self.assertEqual("date_time" in result, True)
        trader.get_trade_tick.assert_called_once_with()

    def test__execute_order_call__send_limit_order_correctly(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_limit_order.assert_called_once_with(True, 500, 0.0001)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.order_map["apple"]["order_id"], "apple_order_id")
        self.assertEqual(trader.order_map["apple"]["callback"], dummy_task["callback"])
        self.assertEqual(trader.order_map["apple"]["result"], "banana")
        dummy_task["callback"].assert_called_once_with("banana")

    def test__execute_order_call_cancel_request_correctly(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "cancel"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.cancel_request = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_limit_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        dummy_task["callback"].assert_not_called()

    def test__execute_order_call_callback_with_error_when_try_to_buy_over_balance(self):
        dummy_task = {
            "request": {"id": "apple", "price": 50000000, "amount": 0.01, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.cancel_request = MagicMock()

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_limit_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()

    def test__execute_order_call_callback_with_error_when_try_to_sell_over_balance(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500000, "amount": 0.0001, "type": "sell"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.cancel_request = MagicMock()

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_limit_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()

    def test__execute_order_call_callback_with_error_when__send_limit_order_return_None(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500000, "amount": 0.0001, "type": "sell"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(return_value=None)
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.cancel_request = MagicMock()

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_limit_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()

    def test__execute_order_ignore_when_price_is_zero(self):
        dummy_task = {
            "request": {"id": "apple", "price": 0, "amount": 0.0001, "type": "sell"},
            "callback": MagicMock(),
        }
        trader = BithumbTrader()
        trader._send_limit_order = MagicMock(
            return_value={"status": "0000", "order_id": "apple_order_id"}
        )
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()
        trader.cancel_request = MagicMock()

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_not_called()
        trader._send_limit_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()

    @patch("threading.Timer")
    def test_start_timer_should_start_Timer(self, mock_timer):
        trader = BithumbTrader()
        trader.worker = MagicMock()

        trader._start_timer()

        mock_timer.assert_called_once_with(trader.RESULT_CHECKING_INTERVAL, ANY)
        callback = mock_timer.call_args[0][1]
        callback()
        trader.worker.post_task.assert_called_once_with({"runnable": trader._update_order_result})

    def test_stop_timer_should_call_cancel(self):
        trader = BithumbTrader()
        timer_mock = MagicMock()
        trader.timer = timer_mock

        trader._stop_timer()

        timer_mock.cancel.assert_called_once()
        self.assertEqual(trader.timer, None)

    def test__update_order_result_should_call__call_callback_and_keep_waiting_request(self):
        dummy_result = [
            {
                "data": {
                    "order_status": "Completed",
                    "order_id": "mango",
                    "state": "done",
                    "transaction_date": "1572497603668315",
                    "order_price": 500,
                    "order_qty": 0.007,
                    "contract": [
                        {
                            "transaction_date": "1572497603668315",
                        }
                    ],
                },
            },
            {
                "data": {
                    "order_status": "Waiting",
                    "order_id": "banana",
                    "state": "cancel",
                    "transaction_date": "1572498603668315",
                    "order_price": 1500,
                    "order_qty": 0.54321,
                    "contract": [
                        {
                            "transaction_date": "1572498603668315",
                        }
                    ],
                },
            },
            {
                "data": {
                    "order_status": "Completed",
                    "order_id": "apple",
                    "state": "cancel",
                    "transaction_date": "1572498603668315",
                    "order_price": 1500,
                    "order_qty": 0.54321,
                    "contract": [
                        {
                            "transaction_date": "1572498603668315",
                        }
                    ],
                },
            },
        ]
        dummy_request_mango = {
            "order_id": "mango_order",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"state": "done", "type": "buy"},
        }
        dummy_request_banana = {
            "order_id": "banana_order",
            "request": {"id": "banana_id"},
            "callback": MagicMock(),
            "result": {"state": "done", "type": "sell"},
        }
        dummy_request_apple = {
            "order_id": "apple_order",
            "request": {"id": "apple_id"},
            "callback": MagicMock(),
            "result": {"state": "done", "type": "buy"},
        }
        trader = BithumbTrader()
        trader._call_callback = MagicMock()
        trader._query_order = MagicMock(side_effect=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.order_map["mango"] = dummy_request_mango
        trader.order_map["banana"] = dummy_request_banana
        trader.order_map["apple"] = dummy_request_apple

        trader._update_order_result(None)

        self.assertEqual(
            trader._query_order.call_args_list,
            [call("mango_order"), call("banana_order"), call("apple_order")],
        )

        trader._call_callback.assert_called()

        mango_result = trader._call_callback.call_args_list[0][0][1]
        self.assertEqual(mango_result["date_time"], "2019-10-31T13:53:23")
        self.assertEqual(mango_result["price"], 500)
        self.assertEqual(mango_result["type"], "buy")
        self.assertEqual(mango_result["state"], "done")
        self.assertEqual(mango_result["amount"], 0.007)
        self.assertEqual(
            trader._call_callback.call_args_list[0][0][0], dummy_request_mango["callback"]
        )

        apple_result = trader._call_callback.call_args_list[1][0][1]
        self.assertEqual(apple_result["date_time"], "2019-10-31T14:10:03")
        self.assertEqual(apple_result["price"], 1500)
        self.assertEqual(mango_result["type"], "buy")
        self.assertEqual(mango_result["state"], "done")
        self.assertEqual(apple_result["amount"], 0.54321)
        self.assertEqual(
            trader._call_callback.call_args_list[1][0][0], dummy_request_apple["callback"]
        )

        self.assertEqual(len(trader.order_map), 1)
        self.assertEqual(trader.order_map["banana"]["request"]["id"], "banana_id")
        trader._stop_timer.assert_called_once()
        trader._start_timer.assert_called_once()

    def test__update_order_result_should_NOT_start_timer_when_no_request_remains(self):
        dummy_result = [
            {
                "data": {
                    "order_status": "Completed",
                    "order_id": "mango",
                    "state": "done",
                    "transaction_date": "1572497603668315",
                    "order_price": 500,
                    "order_qty": 0.007,
                },
            },
            {
                "data": {
                    "order_status": "Completed",
                    "order_id": "apple",
                    "state": "cancel",
                    "transaction_date": "1572498603668315",
                    "order_price": 1500,
                    "order_qty": 0.54321,
                },
            },
        ]
        dummy_request_mango = {
            "order_id": "mango_order",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"id": "mango_result", "state": "done", "type": "buy"},
        }
        dummy_request_apple = {
            "order_id": "apple_order",
            "request": {"id": "apple_id"},
            "callback": MagicMock(),
            "result": {"id": "apple_result", "state": "done", "type": "buy"},
        }
        trader = BithumbTrader()
        trader._call_callback = MagicMock()
        trader._query_order = MagicMock(side_effect=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.order_map["mango"] = dummy_request_mango
        trader.order_map["apple"] = dummy_request_apple

        trader._update_order_result(None)

        self.assertEqual(
            trader._query_order.call_args_list,
            [call("mango_order"), call("apple_order")],
        )

        self.assertEqual(len(trader.order_map), 0)
        trader._stop_timer.assert_called_once()
        trader._start_timer.assert_not_called()

    def test__send_limit_order_should_call_bithumb_api_call_with_correct_query(self):
        trader = BithumbTrader("BTC")
        expected_query = {
            "order_currency": trader.market,
            "payment_currency": trader.market_currency,
            "type": "bid",
            "units": "0.0051",
            "price": "500",
        }
        trader.bithumb_api_call = MagicMock()
        trader._send_limit_order(True, 500, 0.00512)
        trader.bithumb_api_call.assert_called_once_with("/trade/place", expected_query)

    def test__query_order_should_call_bithumb_api_call_with_correct_query(self):
        trader = BithumbTrader("BTC")
        expected_query = {
            "order_currency": trader.market,
            "payment_currency": trader.market_currency,
            "order_id": "apple-007",
        }
        trader.bithumb_api_call = MagicMock()
        trader._query_order()
        trader.bithumb_api_call.assert_not_called()

        trader.bithumb_api_call = MagicMock()
        trader._query_order("apple-007")
        trader.bithumb_api_call.assert_called_once_with("/info/order_detail", expected_query)

    def test__query_balance_should_call_bithumb_api_call_with_correct_query(self):
        trader = BithumbTrader()
        expected_query = {
            "order_currency": "apple",
            "payment_currency": "KRW",
        }
        trader.bithumb_api_call = MagicMock()
        trader._query_balance("apple")
        trader.bithumb_api_call.assert_called_once_with("/info/balance", expected_query)

    @patch("requests.get")
    def test_get_trade_tick_should_send_http_request_correctly(self, mock_get):
        trader = BithumbTrader("BTC")
        expected_url = (
            trader.SERVER_URL
            + f"/public/transaction_history/{trader.market}_{trader.market_currency}"
        )

        trader.get_trade_tick()
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
