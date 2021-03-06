import os
import unittest
from smtm import VirtualMarket
from unittest.mock import *


class VirtualMarketTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def create_http_mock(self):
        http_mock = Mock()

        class HTTPError(Exception):
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        class RequestException(Exception):
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        http_mock.exceptions.HTTPError = HTTPError
        http_mock.exceptions.RequestException = RequestException
        return http_mock

    def test_intialize_should_download_from_real_market(self):
        market = VirtualMarket()
        http = Mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "test"}]'
        dummy_response.raise_for_status = MagicMock()
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        http.request.assert_called_once_with("GET", market.URL, params=market.QUERY_STRING)

    def test_intialize_should_not_download_again_after_initialized(self):
        market = VirtualMarket()
        http = Mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "test"}]'
        dummy_response.raise_for_status = MagicMock()
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(None, None, None)
        market.initialize(http, None, None)
        market.initialize(http, None, None)
        http.request.assert_called_once_with("GET", market.URL, params=market.QUERY_STRING)

    def test_intialize_update_trading_data(self):
        market = VirtualMarket()
        http = Mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "mango"}, {"market": "banana"}, {"market": "apple"}]'
        dummy_response.raise_for_status = MagicMock()
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        # 서버 데이터가 최신순으로 들어오므로 역순으로 저장
        self.assertEqual(market.data[0]["market"], "apple")
        self.assertEqual(market.data[1]["market"], "banana")
        self.assertEqual(market.data[2]["market"], "mango")

    def test_intialize_NOT_initialize_with_invalid_response_data(self):
        market = VirtualMarket()
        http = Mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = "mango"
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        self.assertEqual(market.is_initialized, False)

    def test_intialize_NOT_initialize_when_receive_error(self):
        market = VirtualMarket()
        http_mock = self.create_http_mock()

        def raise_exception():
            raise http_mock.exceptions.HTTPError("HTTPError dummy exception")

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = "mango"
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)
        market.initialize(http_mock, None, None)
        self.assertEqual(market.is_initialized, False)

    def test_intialize_NOT_initialize_when_connection_fail(self):
        market = VirtualMarket()
        http_mock = self.create_http_mock()

        def raise_exception():
            raise http_mock.exceptions.RequestException("RequestException dummy exception")

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = "mango"
        dummy_response.raise_for_status = raise_exception
        http_mock.request = MagicMock(return_value=dummy_response)
        market.initialize(http_mock, None, None)
        self.assertEqual(market.is_initialized, False)

    def test_initialize_set_default_params(self):
        market = VirtualMarket()
        http_mock = self.create_http_mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "mango"}]'
        dummy_response.raise_for_status = MagicMock()
        http_mock.request = MagicMock(return_value=dummy_response)
        market.initialize(http_mock, None, None)
        dummy_response.raise_for_status.assert_called_once()
        http_mock.request.assert_called_once_with("GET", market.URL, params=market.QUERY_STRING)
        self.assertEqual(market.is_initialized, True)
        self.assertEqual(market.QUERY_STRING["to"], "2020-04-30 00:00:00")
        self.assertEqual(market.QUERY_STRING["count"], 100)

    def test_intialize_from_file_update_trading_data(self):
        market = VirtualMarket()
        market.initialize_from_file("banana_data", None, None)
        self.assertEqual(market.data, None)
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        self.assertEqual(market.data[0]["market"], "mango")

    def test_intialize_from_file_ignore_after_initialized(self):
        market = VirtualMarket()
        http = Mock()

        class DummyResponse:
            pass

        dummy_response = DummyResponse()
        dummy_response.text = '[{"market": "banana"}]'
        dummy_response.raise_for_status = MagicMock()
        http.request = MagicMock(return_value=dummy_response)
        market.initialize(http, None, None)
        self.assertEqual(market.data[0]["market"], "banana")

        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        self.assertEqual(market.data[0]["market"], "banana")

    def test_send_request_return_emtpy_result_when_NOT_initialized(self):
        market = VirtualMarket()

        dummy_request = {"id": "mango", "type": "orange"}
        result = market.send_request(dummy_request)
        self.assertEqual(result, None)

    def test_send_request_return_trading_result_with_same_id_and_type(self):
        market = VirtualMarket()

        dummy_request = {"id": "mango", "type": "orange", "price": 2000, "amount": 10}
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        self.assertEqual(market.data[0]["market"], "mango")

        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "orange")

    def test_send_request_handle_buy_return_result_corresponding_next_data(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["trade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1790)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1800, "amount": 0.1}
        result = market.send_request(dummy_request2)
        self.assertEqual(result["request_id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "not matched")

    def test_send_request_handle_buy_return_error_request_when_data_invalid(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data_invalid_key.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)

        for i in range(3):
            market.data[i]["pening_price"] = 2000.00000000
            market.data[i]["igh_price"] = 2100.00000000
            market.data[i]["ow_price"] = 1900.00000000
            market.data[i]["rade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], -1)
        self.assertEqual(result["amount"], -1)
        self.assertEqual(result["msg"], "internal error")
        self.assertEqual(result["balance"], 2000)

    def test_send_request_handle_sell_return_result_corresponding_next_data(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)
        dummy_datetime = [
            "2020-02-25T23:59:00",
            "2020-02-25T23:59:10",
            "2020-02-25T23:59:20",
            "2020-02-25T23:59:59",
            "2020-02-26T23:59:59",
            "2020-02-27T00:00:59",
        ]

        for i in range(6):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["trade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = dummy_datetime[i]

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1790)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:00")

        dummy_request2 = {"id": "orange", "type": "sell", "price": 2000, "amount": 0.05}
        result = market.send_request(dummy_request2)
        self.assertEqual(result["request_id"], "orange")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.05)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1885)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:10")

        # 매도 요청 가격이 높은 경우
        dummy_request3 = {"id": "apple", "type": "sell", "price": 2500, "amount": 0.05}
        result = market.send_request(dummy_request3)
        self.assertEqual(result["request_id"], "apple")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "not matched")
        self.assertEqual(result["balance"], 1885)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:20")

        # 매도 요청 양이 보유양 보다 많은 경우
        dummy_request4 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request4)
        self.assertEqual(result["request_id"], "banana")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.05)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1980)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:59")

    def test_send_request_handle_sell_return_error_request_when_data_invalid(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data_invalid_key.json", None, None)
        market.deposit(2000)
        market.asset["mango"] = (2000, 1)

        for i in range(3):
            market.data[i]["pening_price"] = 2000.00000000
            market.data[i]["igh_price"] = 2100.00000000
            market.data[i]["ow_price"] = 1900.00000000
            market.data[i]["rade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], -1)
        self.assertEqual(result["amount"], -1)
        self.assertEqual(result["msg"], "internal error")
        self.assertEqual(result["balance"], 2000)

    def test_send_request_handle_return_error_when_invalid_type(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)

        dummy_request = {"id": "mango", "type": "apple", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "apple")
        self.assertEqual(result["price"], -1)
        self.assertEqual(result["amount"], -1)
        self.assertEqual(result["msg"], "invalid type")

    def test_send_request_handle_sell_return_error_request_when_target_asset_empty(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(999)

        dummy_request = {"id": "mango", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "asset empty")
        self.assertEqual(result["balance"], 999)

    def test_send_request_handle_buy_return_no_money_when_balance_is_NOT_enough(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(200)
        market.set_commission_ratio(5)

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["trade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.048}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.048)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 99)

        # 2000 * 0.048 = 96은 잔고로 가능하지만 수수료를 포함하면 부족한 금액
        dummy_request2 = {"id": "orange", "type": "buy", "price": 2000, "amount": 0.048}
        result = market.send_request(dummy_request2)
        self.assertEqual(result["request_id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "no money")
        self.assertEqual(result["balance"], 99)

    def test_send_request_handle_update_balance_correctly(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)
        self.assertEqual(market.balance, 2000)

        for i in range(4):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["trade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)
        # 최저 가격이 1900 이므로 정상적으로 채결됨
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        # 2000 * 0.1 = 200, 수수료 200 * 0.05 = 210, 2000 - 210 = 1790
        self.assertEqual(market.balance, 1790)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1900, "amount": 0.5}
        result = market.send_request(dummy_request2)
        # 최저 가격이 1900 이므로 정상적으로 채결됨
        self.assertEqual(result["request_id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 1900)
        self.assertEqual(result["amount"], 0.5)
        self.assertEqual(result["msg"], "success")
        # 1900 * 0.5 = 950, 수수료 950 * 0.05 = 47.5, 1790 - 950 - 47.5 = 792.5
        # 792.5 반올림 792
        self.assertEqual(market.balance, 792)

        dummy_request3 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.2}
        result = market.send_request(dummy_request3)
        # 최고 가격이 2100 이므로 정상적으로 채결됨
        self.assertEqual(result["request_id"], "banana")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.2)
        self.assertEqual(result["msg"], "success")
        # 2000 * 0.2 = 400, 수수료 400 * 0.05 = 20, 792 + 400 - 20 = 1172
        self.assertEqual(market.balance, 1172)

    def test_send_request_return_error_result_when_turn_is_overed(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        for i in range(len(market.data) - 2):
            result = market.send_request(dummy_request)
            self.assertEqual(result["request_id"], "mango")
            self.assertEqual(result["type"], "buy")

        result = market.send_request(dummy_request)
        self.assertEqual(result["price"], -1)
        self.assertEqual(result["amount"], -1)
        self.assertEqual(result["msg"], "game-over")

    def test_send_request_handle_turn_over_with_zero_price(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)
        self.assertEqual(market.balance, 2000)

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["trade_price"] = 2050.00000000
            market.data[i]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 0, "amount": 0}
        result = market.send_request(dummy_request)
        self.assertEqual(result["request_id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "turn over")
        self.assertEqual(market.balance, 2000)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request2)
        self.assertEqual(result["request_id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(market.balance, 1790)

    def test_deposit_update_balance_correctly(self):
        market = VirtualMarket()
        self.assertEqual(market.balance, 0)
        market.deposit(1000)
        self.assertEqual(market.balance, 1000)
        market.deposit(-500)
        self.assertEqual(market.balance, 500)

    def test_set_commission_ratio_update_commision_ratio_correctly(self):
        market = VirtualMarket()
        self.assertEqual(market.commission_ratio, 0.0005)
        market.set_commission_ratio(0.01)
        self.assertEqual(market.commission_ratio, 0.0001)
        market.set_commission_ratio(5)
        self.assertEqual(market.commission_ratio, 0.05)
        market.set_commission_ratio(70)
        self.assertEqual(market.commission_ratio, 0.7)
        market.set_commission_ratio(0.00007)
        self.assertEqual(market.commission_ratio, 0.0000007)

    def test_get_balance_return_balance_and_property_list(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.set_commission_ratio(5)
        info = market.get_balance()
        self.assertEqual(info["balance"], 2000)
        self.assertEqual(len(info["asset"]), 0)

        market.data[0]["opening_price"] = 2000.00000000
        market.data[0]["high_price"] = 2100.00000000
        market.data[0]["low_price"] = 1900.00000000
        market.data[0]["trade_price"] = 2050.00000000
        market.data[0]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        market.data[1]["opening_price"] = 2010.00000000
        market.data[1]["high_price"] = 2100.00000000
        market.data[1]["low_price"] = 1900.00000000
        market.data[1]["trade_price"] = 2050.00000000
        market.data[1]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        market.data[2]["opening_price"] = 2020.00000000
        market.data[2]["high_price"] = 2100.00000000
        market.data[2]["low_price"] = 1900.00000000
        market.data[2]["trade_price"] = 2050.00000000
        market.data[2]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        market.data[3]["opening_price"] = 2030.00000000
        market.data[3]["high_price"] = 2100.00000000
        market.data[3]["low_price"] = 1900.00000000
        market.data[3]["trade_price"] = 2050.00000000
        market.data[3]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        market.data[4]["opening_price"] = 2040.00000000
        market.data[4]["high_price"] = 2100.00000000
        market.data[4]["low_price"] = 1900.00000000
        market.data[4]["trade_price"] = 2050.00000000
        market.data[4]["candle_date_time_kst"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.send_request(dummy_request)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1790)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 2000)
        self.assertEqual(info["asset"]["mango"][1], 0.1)
        self.assertEqual(info["quote"]["mango"], 2010)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1900, "amount": 0.5}
        result = market.send_request(dummy_request2)

        info = market.get_balance()
        self.assertEqual(info["balance"], 792)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 1917)
        self.assertEqual(info["asset"]["mango"][1], 0.6)
        self.assertEqual(info["quote"]["mango"], 2020)

        dummy_request3 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.2}
        result = market.send_request(dummy_request3)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1172)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 1917)
        self.assertEqual(round(info["asset"]["mango"][1], 1), 0.4)
        self.assertEqual(info["quote"]["mango"], 2030)

        dummy_request4 = {"id": "banana", "type": "sell", "price": 1950, "amount": 1}
        result = market.send_request(dummy_request4)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1913)
        self.assertEqual(len(info["asset"]), 0)
        self.assertEqual(info["quote"]["mango"], 2040)

    def test_get_balance_return_None_when_data_invalid(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data_invalid_key.json", None, None)
        market.deposit(2000)
        info = market.get_balance()
        self.assertEqual(info, None)

    def test_get_balance_return_None_when_data_index_invalid(self):
        market = VirtualMarket()
        market.initialize_from_file("./tests/data/mango_data.json", None, None)
        market.deposit(2000)
        market.turn_count = 5000
        info = market.get_balance()
        self.assertEqual(info, None)
