import unittest
from smtm import VirtualMarket
from unittest.mock import *


class VirtualMarketInitializeTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("requests.get")
        self.request_mock = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_intialize_should_update_data_from_data_repository(self):
        market = VirtualMarket()
        market.repo = MagicMock()
        market.repo.get_data.return_value = ["mango", "orange"]
        market.market = "mango_market"
        market.initialize(end="2020-04-30T00:00:00", count=500, budget=7777777)
        self.assertEqual(market.data[0], "mango")
        self.assertEqual(market.data[1], "orange")
        self.assertEqual(market.is_initialized, True)
        self.assertEqual(market.balance, 7777777)
        market.repo.get_data.assert_called_once_with(
            "2020-04-29T15:40:00", "2020-04-30T00:00:00", market="mango_market"
        )

    def test_intialize_should_update_data_from_data_repository_with_3m_interval(self):
        market = VirtualMarket(interval=180)
        market.repo = MagicMock()
        market.repo.get_data.return_value = ["mango", "orange"]
        market.market = "mango_market"
        market.initialize(end="2020-04-30T00:00:00", count=250, budget=7777777)
        self.assertEqual(market.data[0], "mango")
        self.assertEqual(market.data[1], "orange")
        self.assertEqual(market.is_initialized, True)
        self.assertEqual(market.balance, 7777777)
        market.repo.get_data.assert_called_once_with(
            "2020-04-29T11:30:00", "2020-04-30T00:00:00", market="mango_market"
        )


class VirtualMarketTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_request_return_emtpy_result_when_NOT_initialized(self):
        market = VirtualMarket()

        dummy_request = {"id": "mango", "type": "orange"}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, None)

    def test_handle_request_return_trading_result_with_same_id_and_type(self):
        market = VirtualMarket()

        dummy_request = {"id": "mango", "type": "orange", "price": 2000, "amount": 10}
        market.data = self.get_mango_data()
        market.is_initialized = True
        result = market.handle_request(dummy_request)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_buy_return_result_corresponding_next_data(self):
        market = VirtualMarket()
        market.data = self.get_mango_data()
        market.is_initialized = True
        market.balance = 2000
        market.commission_ratio = 0.05

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["closing_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result["request"]["id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1790)
        self.assertEqual(result["state"], "done")

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1800, "amount": 0.1}
        result = market.handle_request(dummy_request2)
        self.assertEqual(result, "pass")

    def test_handle_request_handle_buy_return_error_request_when_data_invalid(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_invalid_key_data()
        market.balance = 2000
        market.commission_ratio = 0.05

        for i in range(3):
            market.data[i]["pening_price"] = 2000.00000000
            market.data[i]["igh_price"] = 2100.00000000
            market.data[i]["ow_price"] = 1900.00000000
            market.data[i]["rade_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_sell_return_result_corresponding_next_data(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000
        market.commission_ratio = 0.05
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
            market.data[i]["closing_price"] = 2050.00000000
            market.data[i]["date_time"] = dummy_datetime[i]

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result["request"]["id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1790)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:00")
        self.assertEqual(result["state"], "done")

        dummy_request2 = {"id": "orange", "type": "sell", "price": 2000, "amount": 0.05}
        result = market.handle_request(dummy_request2)
        self.assertEqual(result["request"]["id"], "orange")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.05)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1885)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:10")
        self.assertEqual(result["state"], "done")

        # 매도 요청 가격이 높은 경우
        dummy_request3 = {"id": "apple", "type": "sell", "price": 2500, "amount": 0.05}
        result = market.handle_request(dummy_request3)
        self.assertEqual(result, "pass")

        # 매도 요청 양이 보유양 보다 많은 경우
        dummy_request4 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request4)
        self.assertEqual(result["request"]["id"], "banana")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.05)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 1980)
        self.assertEqual(result["date_time"], "2020-02-25T23:59:59")
        self.assertEqual(result["state"], "done")

    def test_handle_request_handle_sell_return_error_request_when_data_invalid(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_invalid_key_data()
        market.balance = 2000
        market.asset["mango"] = (2000, 1)

        for i in range(3):
            market.data[i]["pening_price"] = 2000.00000000
            market.data[i]["igh_price"] = 2100.00000000
            market.data[i]["ow_price"] = 1900.00000000
            market.data[i]["rade_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_return_error_when_invalid_type(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()

        dummy_request = {"id": "mango", "type": "apple", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_sell_return_error_request_when_target_asset_empty(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 999

        dummy_request = {"id": "mango", "type": "sell", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_buy_return_no_money_when_balance_is_NOT_enough(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 200
        market.commission_ratio = 0.05

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["closing_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.048}
        result = market.handle_request(dummy_request)
        self.assertEqual(result["request"]["id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.048)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(result["balance"], 99)
        self.assertEqual(result["state"], "done")

        # 2000 * 0.048 = 96은 잔고로 가능하지만 수수료를 포함하면 부족한 금액
        dummy_request2 = {"id": "orange", "type": "buy", "price": 2000, "amount": 0.048}
        result = market.handle_request(dummy_request2)
        self.assertEqual(result, "error!")

    def test_handle_request_handle_update_balance_correctly(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000
        market.commission_ratio = 0.05

        for i in range(4):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["closing_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)
        # 최저 가격이 1900 이므로 정상적으로 채결됨
        self.assertEqual(result["request"]["id"], "mango")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        # 2000 * 0.1 = 200, 수수료 200 * 0.05 = 210, 2000 - 210 = 1790
        self.assertEqual(market.balance, 1790)
        self.assertEqual(result["state"], "done")

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1900, "amount": 0.5}
        result = market.handle_request(dummy_request2)
        # 최저 가격이 1900 이므로 정상적으로 채결됨
        self.assertEqual(result["request"]["id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 1900)
        self.assertEqual(result["amount"], 0.5)
        self.assertEqual(result["msg"], "success")
        # 1900 * 0.5 = 950, 수수료 950 * 0.05 = 47.5, 1790 - 950 - 47.5 = 792.5
        # 792.5 반올림 792
        self.assertEqual(market.balance, 792)
        self.assertEqual(result["state"], "done")

        dummy_request3 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.2}
        result = market.handle_request(dummy_request3)
        # 최고 가격이 2100 이므로 정상적으로 채결됨
        self.assertEqual(result["request"]["id"], "banana")
        self.assertEqual(result["type"], "sell")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.2)
        self.assertEqual(result["msg"], "success")
        # 2000 * 0.2 = 400, 수수료 400 * 0.05 = 20, 792 + 400 - 20 = 1172
        self.assertEqual(market.balance, 1172)
        self.assertEqual(result["state"], "done")

    def test_handle_request_return_error_result_when_turn_is_overed(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        for i in range(len(market.data) - 2):
            result = market.handle_request(dummy_request)
            self.assertEqual(result["request"]["id"], "mango")
            self.assertEqual(result["type"], "buy")

        result = market.handle_request(dummy_request)
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["msg"], "game-over")

    def test_handle_request_handle_turn_over_with_zero_price(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000
        market.commission_ratio = 0.05

        for i in range(3):
            market.data[i]["opening_price"] = 2000.00000000
            market.data[i]["high_price"] = 2100.00000000
            market.data[i]["low_price"] = 1900.00000000
            market.data[i]["closing_price"] = 2050.00000000
            market.data[i]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 0, "amount": 0}
        result = market.handle_request(dummy_request)
        self.assertEqual(result, None)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request2)
        self.assertEqual(result["request"]["id"], "orange")
        self.assertEqual(result["type"], "buy")
        self.assertEqual(result["price"], 2000)
        self.assertEqual(result["amount"], 0.1)
        self.assertEqual(result["msg"], "success")
        self.assertEqual(market.balance, 1790)
        self.assertEqual(result["state"], "done")

    def test_get_balance_return_balance_and_property_list(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000
        market.commission_ratio = 0.05
        info = market.get_balance()
        self.assertEqual(info["balance"], 2000)
        self.assertEqual(len(info["asset"]), 0)

        market.data[0]["opening_price"] = 2000.00000000
        market.data[0]["high_price"] = 2100.00000000
        market.data[0]["low_price"] = 1900.00000000
        market.data[0]["closing_price"] = 2050.00000000
        market.data[0]["date_time"] = "2020-02-27T00:00:59"

        market.data[1]["opening_price"] = 2010.00000000
        market.data[1]["high_price"] = 2100.00000000
        market.data[1]["low_price"] = 1900.00000000
        market.data[1]["closing_price"] = 2050.00000000
        market.data[1]["date_time"] = "2020-02-27T00:00:59"

        market.data[2]["opening_price"] = 2020.00000000
        market.data[2]["high_price"] = 2100.00000000
        market.data[2]["low_price"] = 1900.00000000
        market.data[2]["closing_price"] = 2020.00000000
        market.data[2]["date_time"] = "2020-02-27T00:00:59"

        market.data[3]["opening_price"] = 2030.00000000
        market.data[3]["high_price"] = 2100.00000000
        market.data[3]["low_price"] = 1900.00000000
        market.data[3]["closing_price"] = 2030.00000000
        market.data[3]["date_time"] = "2020-02-27T00:00:59"

        market.data[4]["opening_price"] = 2040.00000000
        market.data[4]["high_price"] = 2100.00000000
        market.data[4]["low_price"] = 1900.00000000
        market.data[4]["closing_price"] = 2040.00000000
        market.data[4]["date_time"] = "2020-02-27T00:00:59"

        dummy_request = {"id": "mango", "type": "buy", "price": 2000, "amount": 0.1}
        result = market.handle_request(dummy_request)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1790)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 2000)
        self.assertEqual(info["asset"]["mango"][1], 0.1)
        self.assertEqual(info["quote"]["mango"], 2050)

        dummy_request2 = {"id": "orange", "type": "buy", "price": 1900, "amount": 0.5}
        result = market.handle_request(dummy_request2)

        info = market.get_balance()
        self.assertEqual(info["balance"], 792)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 1917)
        self.assertEqual(info["asset"]["mango"][1], 0.6)
        self.assertEqual(info["quote"]["mango"], 2020)

        dummy_request3 = {"id": "banana", "type": "sell", "price": 2000, "amount": 0.2}
        result = market.handle_request(dummy_request3)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1172)
        self.assertEqual(len(info["asset"]), 1)
        self.assertEqual(info["asset"]["mango"][0], 1917)
        self.assertEqual(round(info["asset"]["mango"][1], 1), 0.4)
        self.assertEqual(info["quote"]["mango"], 2030)

        dummy_request4 = {"id": "banana", "type": "sell", "price": 1950, "amount": 1}
        result = market.handle_request(dummy_request4)

        info = market.get_balance()
        self.assertEqual(info["balance"], 1913)
        self.assertEqual(len(info["asset"]), 0)
        self.assertEqual(info["quote"]["mango"], 2040)

    def test_get_balance_return_None_when_data_invalid(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_invalid_key_data()
        market.balance = 2000
        info = market.get_balance()
        self.assertEqual(info, None)

    def test_get_balance_return_None_when_data_index_invalid(self):
        market = VirtualMarket()
        market.is_initialized = True
        market.data = self.get_mango_data()
        market.balance = 2000
        market.turn_count = 5000
        info = market.get_balance()
        self.assertEqual(info, None)

    @staticmethod
    def get_mango_data():
        return [
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2000.00000000,
                "high_price": 2100.00000000,
                "low_price": 1900.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
        ]

    @staticmethod
    def get_invalid_key_data():
        return [
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "pening_price": 2000.00000000,
                "igh_price": 2100.00000000,
                "ow_price": 1900.00000000,
                "rade_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "pening_price": 2050.00000000,
                "igh_price": 2200.00000000,
                "ow_price": 2000.00000000,
                "rade_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
            {
                "market": "mango",
                "candle_date_time_utc": "2020-02-25T06:41:00",
                "date_time": "2020-02-25T15:41:00",
                "opening_price": 2050.00000000,
                "high_price": 2200.00000000,
                "low_price": 2000.00000000,
                "closing_price": 2050.00000000,
                "timestamp": 1582612901489,
                "candle_acc_closing_price": 17001839.06758000,
                "candle_acc_trade_volume": 1.48642105,
                "unit": 1,
            },
        ]
