import unittest
from smtm import StrategySma0
from unittest.mock import *


class StrategySma0Tests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_update_initial_balance(self):
        sma = StrategySma0()
        self.assertEqual(sma.is_intialized, False)
        sma.initialize(50000, 50)
        self.assertEqual(sma.budget, 50000)
        self.assertEqual(sma.balance, 50000)
        self.assertEqual(sma.min_price, 50)
        self.assertEqual(sma.is_intialized, True)
        sma.initialize(100, 10)
        self.assertEqual(sma.budget, 50000)
        self.assertEqual(sma.balance, 50000)
        self.assertEqual(sma.min_price, 50)

    def test_update_trading_info_append_info_to_data(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.data.pop(), dummy_info)

    def test_update_trading_info_append_closing_price(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.closing_price_list.pop(), 500)

    @patch("numpy.isnan")
    @patch("pandas.Series")
    def test_update_trading_info_update_process_when_long_gt_short(self, mock_series, mock_np):
        sma = StrategySma0()

        for i in range(sma.LONG):
            sma.closing_price_list.append(500)

        class DummyMean:
            pass

        dummy_mean_short = DummyMean()
        dummy_mean_mid = DummyMean()
        dummy_mean_long = DummyMean()

        dummy_mean_short.values = [5]
        dummy_mean_mid.values = [7]
        dummy_mean_long.values = [10]

        rolling_return_mock = MagicMock()
        rolling_return_mock.mean.side_effect = [
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
        ]
        series_return = MagicMock()
        series_return.rolling.return_value = rolling_return_mock
        mock_series.return_value = series_return

        dummy_info = {
            "date_time": "mango",
            "closing_price": 500,
        }
        mock_np.return_value = False
        sma.initialize(100, 10)
        sma.current_process = "buy"
        sma.asset_amount = 12
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 12 / sma.STEP)

        self.assertEqual(sma.cross_info[0], {"price": 0, "index": 0})
        self.assertEqual(sma.cross_info[1], {"price": 500, "index": 60})

        # current_process가 "sell" 일때는 업데이트 되지 않아야함
        sma.current_process = "sell"
        sma.asset_amount = 9
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 12)  # 12 / STEP

    @patch("numpy.isnan")
    @patch("pandas.Series")
    def test_update_trading_info_update_process_when_long_lt_short(self, mock_series, mock_np):
        sma = StrategySma0()

        for i in range(sma.LONG):
            sma.closing_price_list.append(500)

        class DummyMean:
            pass

        dummy_mean_short = DummyMean()
        dummy_mean_mid = DummyMean()
        dummy_mean_long = DummyMean()

        dummy_mean_short.values = [10]
        dummy_mean_mid.values = [7]
        dummy_mean_long.values = [5]

        rolling_return_mock = MagicMock()
        rolling_return_mock.mean.side_effect = [
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
        ]
        series_return = MagicMock()
        series_return.rolling.return_value = rolling_return_mock
        mock_series.return_value = series_return

        dummy_info = {
            "date_time": "mango",
            "closing_price": 500,
        }
        mock_np.return_value = False
        sma.initialize(100, 10)
        sma.current_process = "sell"
        sma.balance = 90000
        expected_price = 90000 / sma.STEP
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], expected_price)
        self.assertEqual(sma.process_unit[1], 0)

        self.assertEqual(sma.cross_info[0], {"price": 0, "index": 0})
        self.assertEqual(sma.cross_info[1], {"price": 500, "index": 60})

        # current_process가 "buy" 일때는 업데이트 되지 않아야함
        sma.current_process = "buy"
        sma.balance = 90000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 90000)  # 90000 / STEP
        self.assertEqual(sma.process_unit[1], 0)

    @patch("numpy.isnan")
    @patch("pandas.Series")
    def test_update_trading_info_update_process_and_cross_info_when_long_lt_short(
        self, mock_series, mock_np
    ):
        sma = StrategySma0()

        for i in range(sma.LONG + sma.STD_K):
            sma.closing_price_list.append(500)

        class DummyMean:
            pass

        dummy_mean_short = DummyMean()
        dummy_mean_mid = DummyMean()
        dummy_mean_long = DummyMean()

        dummy_mean_short.values = [10]
        dummy_mean_mid.values = [7]
        dummy_mean_long.values = []

        for i in range(sma.STD_K):
            dummy_mean_long.values.append(i)

        dummy_mean_long.values.append(5)

        rolling_return_mock = MagicMock()
        rolling_return_mock.mean.side_effect = [
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
            dummy_mean_short,
            dummy_mean_mid,
            dummy_mean_long,
        ]
        series_return = MagicMock()
        series_return.rolling.return_value = rolling_return_mock
        mock_series.return_value = series_return

        dummy_info = {
            "date_time": "dummy_datetime",
            "closing_price": 500,
        }
        mock_np.return_value = False
        sma.initialize(100, 10)
        sma.current_process = "sell"
        sma.balance = 90000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 90000 / sma.STEP)
        self.assertEqual(sma.process_unit[1], 0)

        self.assertEqual(sma.cross_info[0], {"price": 0, "index": 85})
        self.assertEqual(sma.cross_info[1], {"price": 500, "index": 85})

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sma = StrategySma0()
        sma.update_trading_info("mango")
        self.assertEqual(len(sma.data), 0)

    def test_update_result_append_result(self):
        sma = StrategySma0()
        sma.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "orange")
        self.assertEqual(sma.result[-1]["request"]["id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "777000")
        self.assertEqual(sma.result[-1]["amount"], "0.0001234")
        self.assertEqual(sma.result[-1]["msg"], "melon")
        self.assertEqual(sma.result[-1]["balance"], 500)

    def test_update_result_remove_from_waiting_requests(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "orange")
        self.assertEqual(sma.result[-1]["request"]["id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "777000")
        self.assertEqual(sma.result[-1]["amount"], "0.0001234")
        self.assertEqual(sma.result[-1]["msg"], "melon")
        self.assertEqual(sma.result[-1]["balance"], 500)
        self.assertFalse("banana" in sma.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        sma.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "requested",
        }
        sma.update_result(dummy_result)
        self.assertEqual(len(sma.result), 0)
        self.assertTrue("banana" in sma.waiting_requests)

    def test_update_result_update_balance_and_asset_amount(self):
        sma = StrategySma0()
        sma.initialize(100000, 10)
        self.assertEqual(sma.balance, 100000)
        sma.asset_amount = 50

        dummy_result = {
            "type": "buy",
            "request": {"id": "orange"},
            "price": 1000,
            "amount": 5,
            "msg": "success",
            "balance": 100,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 94998)
        self.assertEqual(sma.asset_amount, 55)
        self.assertEqual(sma.result[-1]["type"], "buy")
        self.assertEqual(sma.result[-1]["request"]["id"], "orange")
        self.assertEqual(sma.result[-1]["price"], 1000)
        self.assertEqual(sma.result[-1]["amount"], 5)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 100)

        dummy_result = {
            "type": "sell",
            "request": {"id": "apple"},
            "price": 1000,
            "amount": 53,
            "msg": "success",
            "balance": 1000,
            "state": "done",
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 147972)
        self.assertEqual(sma.asset_amount, 2)
        self.assertEqual(sma.result[-1]["type"], "sell")
        self.assertEqual(sma.result[-1]["request"]["id"], "apple")
        self.assertEqual(sma.result[-1]["price"], 1000)
        self.assertEqual(sma.result[-1]["amount"], 53)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 1000)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        sma = StrategySma0()
        sma.update_result("orange")
        self.assertEqual(len(sma.result), 0)

    def test_get_request_return_None_when_not_yet_initialized(self):
        sma = StrategySma0()
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_data_is_empty(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_data_is_invaild(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        dummy_info = {}
        sma.update_trading_info(dummy_info)
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_None_when_cross_info_is_invaild(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        dummy_info = {"closing_price": 2000}
        sma.closing_price_list.append(dummy_info)
        sma.cross_info[0] = {"price": 0, "index": 1}
        requests = sma.get_request()
        self.assertEqual(requests, None)

    def test_get_request_return_correct_request_at_buy_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        dummy_info = {"closing_price": 20000000}
        sma.update_trading_info(dummy_info)
        sma.cross_info[0] = {"price": 500, "index": 1}
        sma.cross_info[1] = {"price": 500, "index": 2}
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0001)
        self.assertEqual(requests[0]["type"], "buy")

        dummy_info = {"closing_price": 10000000}
        sma.update_trading_info(dummy_info)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 10000000)
        self.assertEqual(requests[0]["amount"], 0.0003)
        self.assertEqual(requests[0]["type"], "buy")

        dummy_info = {"closing_price": 100}
        sma.update_trading_info(dummy_info)
        sma.balance = 2000
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 100)
        self.assertEqual(requests[0]["amount"], 19.9899)
        self.assertEqual(requests[0]["type"], "buy")

    def test_get_request_return_correct_request_at_sell_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        dummy_info = {"closing_price": 20000000}
        sma.update_trading_info(dummy_info)
        sma.cross_info[0] = {"price": 500, "index": 1}
        sma.cross_info[1] = {"price": 500, "index": 2}

        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 20)
        self.assertEqual(requests[0]["type"], "sell")

        dummy_info = {"closing_price": 10000000}
        sma.update_trading_info(dummy_info)
        sma.asset_amount = 10
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 10000000)
        self.assertEqual(requests[0]["amount"], 10)
        self.assertEqual(requests[0]["type"], "sell")

    def test_get_request_return_request_with_cancel_requests(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        sma.cross_info[0] = {"price": 500, "index": 1}
        sma.cross_info[1] = {"price": 500, "index": 2}
        sma.waiting_requests["mango_id"] = {"request": {"id": "mango_id"}}
        sma.waiting_requests["orange_id"] = {"request": {"id": "orange_id"}}
        sma.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        requests = sma.get_request()
        self.assertEqual(requests[0]["id"], "mango_id")
        self.assertEqual(requests[0]["type"], "cancel")
        self.assertEqual(requests[1]["id"], "orange_id")
        self.assertEqual(requests[1]["type"], "cancel")
        self.assertEqual(requests[2]["price"], 20000000)
        self.assertEqual(requests[2]["amount"], 20)
        self.assertEqual(requests[2]["type"], "sell")
        self.assertEqual(requests[2]["date_time"], "2020-02-25T15:41:09")

    def test_get_request_return_turn_over_when_last_data_is_None(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        sma.cross_info[0] = {"price": 500, "index": 1}
        sma.cross_info[1] = {"price": 500, "index": 2}
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0001)
        self.assertEqual(requests[0]["type"], "buy")

        sma.update_trading_info(None)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)

    def test_get_request_return_turn_over_when_target_budget_lt_min_price_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(1000, 500)
        sma.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (300, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)
        self.assertEqual(requests[0]["type"], "buy")

    def test_get_request_return_turn_over_when_asset_amount_empty_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(900, 10)
        sma.cross_info[0] = {"price": 500, "index": 1}
        sma.cross_info[1] = {"price": 500, "index": 2}
        sma.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 0
        sma.process_unit = (0, 10)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)
        self.assertEqual(requests[0]["type"], "sell")
