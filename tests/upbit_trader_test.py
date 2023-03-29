import unittest
import requests
from urllib.parse import urlencode
from smtm import UpbitTrader
from unittest.mock import *


class UpditTraderTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test__execute_order_handle_task_correctly(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock(return_value={"uuid": "mango"})
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_order.assert_called_once_with(trader.market, True, 500, 0.0001)
        trader._create_success_result.assert_called_once_with(dummy_task["request"])
        trader._start_timer.assert_called_once()
        self.assertEqual(trader.order_map["apple"]["uuid"], "mango")
        self.assertEqual(trader.order_map["apple"]["callback"], dummy_task["callback"])
        self.assertEqual(trader.order_map["apple"]["result"], "banana")
        dummy_task["callback"].assert_called_once()

    def test__execute_order_call_cancel_request_when_request_type_is_cancel(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "cancel"},
            "callback": "kiwi",
        }
        trader = UpbitTrader()
        trader.cancel_request = MagicMock()
        trader._send_order = MagicMock()
        trader._create_success_result = MagicMock()
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        trader._send_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        trader.cancel_request.assert_called_once_with("apple")

    def test__execute_order_should_call_callback_with_error_when__send_order_return_None(self):
        dummy_task = {
            "request": {"id": "apple", "price": 500, "amount": 0.0001, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock(return_value=None)
        trader._create_success_result = MagicMock(return_value="banana")
        trader._start_timer = MagicMock()

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_order.assert_called_once_with(trader.market, True, 500, 0.0001)
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        self.assertEqual(len(trader.order_map), 0)

    def test__execute_order_should_call_callback_with_error_at_balance_lack(self):
        dummy_task = {
            "request": {"id": "apple", "price": 50000, "amount": 0.01, "type": "buy"},
            "callback": MagicMock(),
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock()
        trader._create_success_result = MagicMock()
        trader._start_timer = MagicMock()
        trader.balance = 450

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        self.assertEqual(len(trader.order_map), 0)

    def test__execute_order_should_call_callback_with_error_at_asset_lack(self):
        dummy_task = {
            "request": {"id": "apple", "price": 50000, "amount": 0.01, "type": "sell"},
            "callback": MagicMock(),
        }
        trader = UpbitTrader()
        trader._send_order = MagicMock()
        trader._create_success_result = MagicMock()
        trader._start_timer = MagicMock()
        trader.asset = (45000, 0.009)

        trader._execute_order(dummy_task)

        dummy_task["callback"].assert_called_once_with("error!")
        trader._send_order.assert_not_called()
        trader._create_success_result.assert_not_called()
        trader._start_timer.assert_not_called()
        self.assertEqual(len(trader.order_map), 0)

    def test__create_success_result_return_correct_result(self):
        dummy_request = {"id": "mango", "type": "banana", "price": 500, "amount": 0.12345}
        trader = UpbitTrader()
        success_result = trader._create_success_result(dummy_request)

        self.assertEqual(success_result["request"]["id"], dummy_request["id"])
        self.assertEqual(success_result["type"], dummy_request["type"])
        self.assertEqual(success_result["price"], dummy_request["price"])
        self.assertEqual(success_result["amount"], dummy_request["amount"])
        self.assertEqual(success_result["msg"], "success")
        self.assertEqual(success_result["state"], "requested")

    @patch("threading.Timer")
    def test_start_timer_should_start_Timer(self, mock_timer):
        trader = UpbitTrader()
        trader.worker = MagicMock()

        trader._start_timer()

        mock_timer.assert_called_once_with(trader.RESULT_CHECKING_INTERVAL, ANY)
        callback = mock_timer.call_args[0][1]
        callback()
        trader.worker.post_task.assert_called_once_with({"runnable": trader._update_order_result})

    def test_stop_timer_should_call_cancel(self):
        trader = UpbitTrader()
        timer_mock = MagicMock()
        trader.timer = timer_mock

        trader._stop_timer()

        timer_mock.cancel.assert_called_once()
        self.assertEqual(trader.timer, None)

    def test__update_order_result_should_call__call_callback_and_keep_waiting_request(self):
        dummy_result = [
            {
                "uuid": "mango",
                "state": "done",
                "created_at": "today",
                "price": 500,
                "executed_volume": 0.007,
            },
            {
                "uuid": "apple",
                "state": "cancel",
                "created_at": "yesterday",
                "price": 1500,
                "executed_volume": 0.54321,
            },
        ]
        dummy_request_mango = {
            "uuid": "mango",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"id": "mango_result", "state": "done", "type": "buy"},
        }
        dummy_request_banana = {
            "uuid": "banana",
            "request": {"id": "banana_id"},
            "callback": MagicMock(),
            "result": {"id": "banana_result", "state": "done", "type": "sell"},
        }
        dummy_request_apple = {
            "uuid": "apple",
            "request": {"id": "apple_id"},
            "callback": MagicMock(),
            "result": {"id": "apple_result", "state": "done", "type": "buy"},
        }
        trader = UpbitTrader()
        trader._call_callback = MagicMock()
        trader._query_order_list = MagicMock(return_value=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.order_map["mango"] = dummy_request_mango
        trader.order_map["banana"] = dummy_request_banana
        trader.order_map["apple"] = dummy_request_apple

        trader._update_order_result(None)

        mango_result = trader._call_callback.call_args_list[0][0][1]
        self.assertEqual(mango_result["date_time"], "today")
        self.assertEqual(mango_result["id"], "mango_result")
        self.assertEqual(mango_result["price"], 500)
        self.assertEqual(mango_result["type"], "buy")
        self.assertEqual(mango_result["state"], "done")
        self.assertEqual(mango_result["amount"], 0.007)
        self.assertEqual(
            trader._call_callback.call_args_list[0][0][0], dummy_request_mango["callback"]
        )

        apple_result = trader._call_callback.call_args_list[1][0][1]
        self.assertEqual(apple_result["date_time"], "yesterday")
        self.assertEqual(apple_result["id"], "apple_result")
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
        trader._query_order_list.assert_called_once_with(["mango", "banana", "apple"])

    def test__update_order_result_should_NOT_start_timer_when_no_request_remains(self):
        dummy_result = [
            {
                "uuid": "mango",
                "state": "done",
                "type": "buy",
                "created_at": "today",
                "price": 5000,
                "executed_volume": 0.00001,
            },
            {
                "uuid": "orange",
                "type": "sell",
                "state": "cancel",
                "created_at": "yesterday",
                "price": 2000,
                "executed_volume": 0.1234,
            },
        ]
        dummy_request_mango = {
            "uuid": "mango",
            "request": {"id": "mango_id"},
            "callback": MagicMock(),
            "result": {"id": "mango_result", "state": "done", "type": "buy"},
        }
        dummy_request_orange = {
            "uuid": "orange",
            "request": {"id": "orange_id"},
            "callback": MagicMock(),
            "result": {"id": "orange_result", "state": "done", "type": "sell"},
        }
        trader = UpbitTrader()
        trader._call_callback = MagicMock()
        trader._query_order_list = MagicMock(return_value=dummy_result)
        trader._stop_timer = MagicMock()
        trader._start_timer = MagicMock()
        trader.order_map["mango"] = dummy_request_mango
        trader.order_map["orange"] = dummy_request_orange

        trader._update_order_result(None)

        mango_result = trader._call_callback.call_args_list[0][0][1]
        self.assertEqual(mango_result["date_time"], "today")
        self.assertEqual(mango_result["id"], "mango_result")
        self.assertEqual(mango_result["price"], 5000)
        self.assertEqual(mango_result["type"], "buy")
        self.assertEqual(mango_result["state"], "done")
        self.assertEqual(mango_result["amount"], 0.00001)
        self.assertEqual(
            trader._call_callback.call_args_list[0][0][0], dummy_request_mango["callback"]
        )

        orange_result = trader._call_callback.call_args_list[1][0][1]
        self.assertEqual(orange_result["date_time"], "yesterday")
        self.assertEqual(orange_result["id"], "orange_result")
        self.assertEqual(orange_result["price"], 2000)
        self.assertEqual(orange_result["type"], "sell")
        self.assertEqual(orange_result["state"], "done")
        self.assertEqual(orange_result["amount"], 0.1234)
        self.assertEqual(
            trader._call_callback.call_args_list[1][0][0], dummy_request_orange["callback"]
        )

        self.assertEqual(len(trader.order_map), 0)
        trader._stop_timer.assert_called_once()
        trader._start_timer.assert_not_called()
        trader._query_order_list.assert_called_once_with(["mango", "orange"])

    def test__create_limit_order_query_return_correct_query(self):
        expected_query = {
            "market": "mango",
            "side": "bid",
            "volume": "0.76",
            "price": "500",
            "ord_type": "limit",
        }
        expected_query = urlencode(expected_query).encode()
        trader = UpbitTrader()

        query = trader._create_limit_order_query("mango", True, 500, 0.76)

        self.assertEqual(query, expected_query)

    def test__create_market_price_order_query_query_return_correct_query(self):
        expected_buy_query = {
            "market": "mango",
            "side": "bid",
            "price": "500",
            "ord_type": "price",
        }
        expected_buy_query = urlencode(expected_buy_query).encode()
        expected_sell_query = {
            "market": "mango",
            "side": "ask",
            "volume": "0.76",
            "ord_type": "market",
        }
        expected_sell_query = urlencode(expected_sell_query).encode()

        trader = UpbitTrader()

        query = trader._create_market_price_order_query("mango", price=500)

        self.assertEqual(query, expected_buy_query)

        query = trader._create_market_price_order_query("mango", volume=0.76)

        self.assertEqual(query, expected_sell_query)

        query = trader._create_market_price_order_query("mango", 500, 0.76)

        self.assertEqual(query, None)

    @patch("requests.get")
    def test__query_order_list_should_get_correctly_when_is_done_state_True(self, mock_requests):
        query_states = ["done", "cancel"]
        uuids = ["mango", "orange"]
        expected_query_string = (
            "states[]=done&states[]=cancel&uuids[]=mango&uuids[]=orange".encode()
        )

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        mock_requests.return_value = dummy_response
        trader = UpbitTrader()
        trader._create_jwt_token = MagicMock(return_value="mango_token")

        response = trader._query_order_list(uuids)

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, expected_query_string
        )
        mock_requests.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params=expected_query_string,
            headers={"Authorization": "Bearer mango_token"},
        )

    @patch("requests.get")
    def test__query_order_list_should_get_correctly_when_is_done_state_False(self, mock_requests):
        query_states = ["wait", "watch"]
        uuids = ["banana", "orange"]
        expected_query_string = (
            "states[]=wait&states[]=watch&uuids[]=banana&uuids[]=orange".encode()
        )

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        mock_requests.return_value = dummy_response
        trader = UpbitTrader()
        trader._create_jwt_token = MagicMock(return_value="mango_token")

        response = trader._query_order_list(uuids, False)

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, expected_query_string
        )
        mock_requests.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params=expected_query_string,
            headers={"Authorization": "Bearer mango_token"},
        )

    @patch("requests.get")
    def test__query_account_should_send_correct_request(self, mock_requests):
        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        mock_requests.return_value = dummy_response
        trader = UpbitTrader()
        trader._create_jwt_token = MagicMock(return_value="mango_token")

        response = trader._query_account()

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_jwt_token.assert_called_once_with(trader.ACCESS_KEY, trader.SECRET_KEY)
        mock_requests.assert_called_once_with(
            trader.SERVER_URL + "/v1/accounts",
            headers={"Authorization": "Bearer mango_token"},
        )

    @patch("uuid.uuid4")
    @patch("jwt.encode")
    @patch("hashlib.sha512")
    def test__create_jwt_token_should_return_correct_token(self, mock_hash, mock_jwt, mock_uuid):
        trader = UpbitTrader()
        mock_m = MagicMock()
        mock_hash.return_value = mock_m
        mock_uuid.return_value = "uuid_mango"
        mock_m.hexdigest.return_value = "hash_mango"
        trader._create_jwt_token("ak", "sk", "mango_query")

        mock_hash.assert_called_once()
        mock_m.update.assert_called_once_with("mango_query")
        mock_m.hexdigest.assert_called_once()
        mock_jwt.assert_called_once_with(
            {
                "access_key": "ak",
                "nonce": "uuid_mango",
                "query_hash": "hash_mango",
                "query_hash_alg": "SHA512",
            },
            "sk",
        )

    @patch("uuid.uuid4")
    @patch("jwt.encode")
    @patch("hashlib.sha512")
    def test__create_jwt_token_should_return_correct_token_without_payload(
        self, mock_hash, mock_jwt, mock_uuid
    ):
        trader = UpbitTrader()
        mock_uuid.return_value = "uuid_mango"
        trader._create_jwt_token("ak", "sk")

        mock_jwt.assert_called_once_with({"access_key": "ak", "nonce": "uuid_mango"}, "sk")

    @patch("requests.get")
    def test__request_get_should_send_http_request_correctly(self, mock_get):
        trader = UpbitTrader()
        expected_url = "get/apple"
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value="apple_result")
        mock_get.return_value = mock_response
        dummy_headers = "apple_headers"

        self.assertEqual(trader._request_get("get/apple", headers=dummy_headers), "apple_result")
        mock_response.raise_for_status.assert_called_once()
        mock_get.assert_called_once_with(expected_url, headers=dummy_headers)

    @patch("requests.get")
    def test__request_get_return_None_when_invalid_data_received_from_server(self, mock_get):
        def raise_exception():
            raise ValueError("RequestException dummy exception")

        class DummyResponse:
            pass

        mock_response = DummyResponse()
        mock_response.raise_for_status = raise_exception
        mock_response.json = MagicMock(return_value="apple_result")
        mock_get.return_value = mock_response
        dummy_headers = "apple_headers"

        trader = UpbitTrader()
        expected_url = "get/apple"

        self.assertEqual(trader._request_get("get/apple", headers=dummy_headers), None)
        mock_get.assert_called_once_with(expected_url, headers=dummy_headers)


class UpditTraderSendOrderTests(unittest.TestCase):
    def setUp(self):
        self.post_patcher = patch("requests.post")
        self.post_mock = self.post_patcher.start()
        self.get_patcher = patch("requests.get")
        self.get_mock = self.get_patcher.start()

    def tearDown(self):
        self.post_patcher.stop()
        self.get_patcher.stop()

    def test_send_request_should_call_worker_post_task_correctly(self):
        trader = UpbitTrader()
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

    def test__send_order_should_send_correct_limit_order(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        trader.is_opt_mode = False
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_limit_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", True, 500, 0.555)

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_limit_order_query.assert_called_once_with("mango", True, 500, 0.555)
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, "mango_query"
        )
        self.post_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params="mango_query",
            headers={"Authorization": "Bearer mango_token"},
        )

    def test__send_order_should_send_correct_limit_order_with_opt_mode(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        dummy_get_response = DummyResponse()
        dummy_get_response.raise_for_status = MagicMock()
        dummy_get_response.json = MagicMock(return_value=[{"trade_price": 450}])
        self.get_mock.return_value = dummy_get_response

        trader.is_opt_mode = True
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_limit_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", True, 500, 0.555)

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_limit_order_query.assert_called_once_with("mango", True, 450, 0.555)
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, "mango_query"
        )
        self.post_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params="mango_query",
            headers={"Authorization": "Bearer mango_token"},
        )

    def test__send_order_should_send_correct_limit_order_with_opt_mode_when_query_failed(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        self.get_mock.side_effect = requests.exceptions.RequestException()

        trader.is_opt_mode = True
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_limit_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", True, 500, 0.555)

        self.assertEqual(response, "mango_response")
        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_limit_order_query.assert_called_once_with("mango", True, 500, 0.555)
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, "mango_query"
        )
        self.post_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params="mango_query",
            headers={"Authorization": "Bearer mango_token"},
        )

    def test__send_order_should_send_correct_market_price_buy_order(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", True, 500)

        self.assertEqual(response, "mango_response")
        trader._create_market_price_order_query.assert_called_once_with("mango", price=500)

    def test__send_order_should_send_correct_market_sell_order(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", False, volume=0.55)

        self.assertEqual(response, "mango_response")
        trader._create_market_price_order_query.assert_called_once_with("mango", volume=0.55)

    def test__send_order_should_return_None_when_receive_error_from_server(self):
        trader = UpbitTrader()

        self.post_mock.side_effect = requests.exceptions.HTTPError()
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", False, volume=0.55)

        self.assertEqual(response, None)

    def test__send_order_should_return_None_when_RequestException_occured(self):
        trader = UpbitTrader()

        self.post_mock.side_effect = requests.exceptions.RequestException()
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", False, volume=0.55)

        self.assertEqual(response, None)

    def test__send_order_should_return_None_when_receive_invalid_data(self):
        trader = UpbitTrader()

        self.post_mock.side_effect = ValueError()
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", False, volume=0.55)

        self.assertEqual(response, None)

    def test__send_order_should_NOT_send_invaild_order(self):
        trader = UpbitTrader()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.raise_for_status = MagicMock()
        dummy_response.json = MagicMock(return_value="mango_response")
        self.post_mock.return_value = dummy_response
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        trader._create_market_price_order_query = MagicMock(return_value="mango_query")

        response = trader._send_order("mango", True, volume=0.55)
        self.assertEqual(response, None)

        response = trader._send_order("mango", False, price=500)
        self.assertEqual(response, None)

        response = trader._send_order("mango", True)
        self.assertEqual(response, None)
        trader._create_market_price_order_query.assert_not_called()


class UpditTraderGetAccountTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_account_info_should_return_correct_info(self):
        dummy_respone = [
            {"currency": "KRW", "balance": 123456789},
            {"currency": "APPLE", "balance": 500, "avg_buy_price": 23456},
        ]
        trader = UpbitTrader()
        trader.balance = 123456789
        trader.asset = (23456, 500)
        trader.market_currency = "APPLE"
        trader.market = "APPLE"
        trader.worker = MagicMock()
        trader.get_trade_tick = MagicMock(return_value=[{"trade_price": 777}])
        result = trader.get_account_info()

        self.assertEqual(result["balance"], 123456789)
        self.assertEqual(result["asset"], {"APPLE": (23456, 500)})
        self.assertEqual(result["quote"], {"APPLE": 777})
        self.assertEqual("date_time" in result, True)
        trader.get_trade_tick.assert_called_once_with()


class UpditTraderCancelRequestTests(unittest.TestCase):
    def setUp(self):
        self.patcher_delete = patch("requests.delete")
        self.patcher_get = patch("requests.get")
        self.delete_mock = self.patcher_delete.start()
        self.get_mock = self.patcher_get.start()

    def tearDown(self):
        self.patcher_delete.stop()
        self.patcher_get.stop()

    def test_cancel_request_should_call__call_callback_when_cancel_order_return_info(self):
        trader = UpbitTrader()
        trader._call_callback = MagicMock()
        dummy_request = {
            "uuid": "mango_uuid",
            "callback": MagicMock(),
            "result": {
                "request": {
                    "id": "mango_request_1234",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
                "msg": "success",
            },
        }
        trader.order_map["mango_request_1234"] = dummy_request

        dummy_response = MagicMock()
        dummy_response.json.return_value = {
            "created_at": "2018-04-10T15:42:23+09:00",
            "type": "buy",
            "price": "887000",
            "executed_volume": "0.0000034",
            "msg": "success",
        }
        expected_result = {
            "request": {
                "id": "mango_request_1234",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "buy",
            "price": 887000.0,
            "amount": 0.0000034,
            "msg": "success",
            "date_time": "2018-04-10T15:42:23",
            "state": "done",
        }
        self.delete_mock.return_value = dummy_response
        trader._create_jwt_token = MagicMock(return_value="mango_token")
        expected_query_string = "uuid=mango_uuid".encode()

        trader.cancel_request("mango_request_1234")

        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        trader._create_jwt_token.assert_called_once_with(
            trader.ACCESS_KEY, trader.SECRET_KEY, expected_query_string
        )
        self.delete_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/order",
            params=expected_query_string,
            headers={"Authorization": "Bearer mango_token"},
        )
        trader._call_callback.assert_called_once_with(dummy_request["callback"], expected_result)
        self.assertFalse("mango_request_1234" in trader.order_map)

    def test_cancel_request_should_call__call_callback_when_cancel_order_return_None(self):
        trader = UpbitTrader()
        trader._call_callback = MagicMock()
        dummy_request = {
            "uuid": "mango_uuid",
            "callback": MagicMock(),
            "result": {
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

        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        expected_query_string_delete = "uuid=mango_uuid".encode()
        expected_result = {
            "request": {
                "id": "mango_request_1234",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "buy",
            "price": 887000.0,
            "amount": 0.0000034,
            "msg": "success",
            "date_time": "2018-04-10T15:42:23",
            "state": "done",
        }
        self.delete_mock.return_value = dummy_response

        expected_query_string_get = "states[]=done&states[]=cancel&uuids[]=mango_uuid".encode()
        dummy_response_get = MagicMock()
        dummy_response_get.json.return_value = [
            {
                "created_at": "2018-04-10T15:42:23+09:00",
                "type": "buy",
                "price": "887000",
                "executed_volume": "0.0000034",
                "msg": "success",
            }
        ]
        self.get_mock.return_value = dummy_response_get
        trader._create_jwt_token = MagicMock(return_value="mango_token")

        trader.cancel_request("mango_request_1234")

        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        self.assertEqual(trader._create_jwt_token.call_args_list[0][0][0], trader.ACCESS_KEY)
        self.assertEqual(trader._create_jwt_token.call_args_list[0][0][1], trader.SECRET_KEY)
        self.assertEqual(
            trader._create_jwt_token.call_args_list[0][0][2], expected_query_string_delete
        )
        self.delete_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/order",
            params=expected_query_string_delete,
            headers={"Authorization": "Bearer mango_token"},
        )

        dummy_response_get.raise_for_status.assert_called_once()
        dummy_response_get.json.assert_called_once()
        self.assertEqual(trader._create_jwt_token.call_args_list[1][0][0], trader.ACCESS_KEY)
        self.assertEqual(trader._create_jwt_token.call_args_list[1][0][1], trader.SECRET_KEY)
        self.assertEqual(
            trader._create_jwt_token.call_args_list[1][0][2], expected_query_string_get
        )
        self.get_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params=expected_query_string_get,
            headers={"Authorization": "Bearer mango_token"},
        )

        trader._call_callback.assert_called_once_with(dummy_request["callback"], expected_result)
        self.assertFalse("mango_request_1234" in trader.order_map)

    def test_cancel_request_should_remove_request_even_when_cancel_nothing(self):
        trader = UpbitTrader()
        dummy_request = {
            "uuid": "mango_uuid",
            "callback": MagicMock(),
            "result": {
                "request": {
                    "id": "mango_request_1234",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
                "msg": "success",
            },
        }
        trader.order_map["mango_request_1234"] = dummy_request

        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        expected_query_string_delete = "uuid=mango_uuid".encode()
        expected_result = {
            "request": {
                "id": "mango_request_1234",
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
            },
            "type": "buy",
            "price": "887000",
            "amount": "0.0000034",
            "msg": "success",
        }
        self.delete_mock.return_value = dummy_response

        expected_query_string_get = "states[]=done&states[]=cancel&uuids[]=mango_uuid".encode()
        dummy_response_get = MagicMock()
        dummy_response_get.json.return_value = []
        self.get_mock.return_value = dummy_response_get
        trader._create_jwt_token = MagicMock(return_value="mango_token")

        trader.cancel_request("mango_request_1234")

        dummy_response.raise_for_status.assert_called_once()
        dummy_response.json.assert_called_once()
        self.assertEqual(trader._create_jwt_token.call_args_list[0][0][0], trader.ACCESS_KEY)
        self.assertEqual(trader._create_jwt_token.call_args_list[0][0][1], trader.SECRET_KEY)
        self.assertEqual(
            trader._create_jwt_token.call_args_list[0][0][2], expected_query_string_delete
        )
        self.delete_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/order",
            params=expected_query_string_delete,
            headers={"Authorization": "Bearer mango_token"},
        )

        dummy_response_get.raise_for_status.assert_called_once()
        dummy_response_get.json.assert_called_once()
        self.assertEqual(trader._create_jwt_token.call_args_list[1][0][0], trader.ACCESS_KEY)
        self.assertEqual(trader._create_jwt_token.call_args_list[1][0][1], trader.SECRET_KEY)
        self.assertEqual(
            trader._create_jwt_token.call_args_list[1][0][2], expected_query_string_get
        )
        self.get_mock.assert_called_once_with(
            trader.SERVER_URL + "/v1/orders",
            params=expected_query_string_get,
            headers={"Authorization": "Bearer mango_token"},
        )

        dummy_request["callback"].assert_not_called()
        self.assertFalse("mango_request_1234" in trader.order_map)

    def test_cancel_all_requests_should_call_cancel_request_correctly(self):
        trader = UpbitTrader()
        dummy_request = {
            "uuid": "mango_uuid",
            "callback": MagicMock(),
            "result": {
                "request": {
                    "id": "mango_request_1234",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
                "msg": "success",
            },
        }
        trader.order_map["mango_request_1234"] = dummy_request

        dummy_request2 = {
            "uuid": "mango_uuid2",
            "callback": MagicMock(),
            "result": {
                "request": {
                    "id": "mango_request_5678",
                    "type": "buy",
                    "price": "888000",
                    "amount": "0.0001234",
                },
                "type": "buy",
                "price": "888000",
                "amount": "0.0001234",
                "msg": "success",
            },
        }
        trader.order_map["mango_request_5678"] = dummy_request2
        trader.cancel_request = MagicMock()

        trader.cancel_all_requests()

        trader.cancel_request.assert_called()
        self.assertEqual(trader.cancel_request.call_args_list[0][0][0], "mango_request_1234")
        self.assertEqual(trader.cancel_request.call_args_list[1][0][0], "mango_request_5678")


class UpditTraderBalanceTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test__call_callback_update_balance_correctly_when_buy(self):
        trader = UpbitTrader()
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
        self.assertEqual(trader.asset, (66993868.572313, 1.001235))
        dummy_callback.assert_called_once_with(dummy_result)

    def test__call_callback_update_balance_correctly_when_sell(self):
        trader = UpbitTrader()
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
        trader = UpbitTrader()
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
