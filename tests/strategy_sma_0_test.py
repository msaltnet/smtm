import unittest
from smtm import StrategySma0
from unittest.mock import *


class StrategySma0Tests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_update_simulation_mode(self):
        sma = StrategySma0()
        sma.initialize(50000, 50, False)
        self.assertEqual(sma.is_simulation, False)

        sma = StrategySma0()
        sma.initialize(0, 0, True)
        self.assertEqual(sma.is_simulation, True)

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

        class DummySeries:
            """ interval을 최종 결과로 리턴하는 DummySeries"""

            def rolling(self, interval):
                class DummyRolling:
                    def __init__(self, value):
                        self.return_value = value

                    def mean(self):
                        class DummyValue:
                            pass

                        meanlist = DummyValue()
                        meanlist.values = [self.return_value]
                        return meanlist

                return DummyRolling(interval)

        mock_series.return_value = DummySeries()
        mock_np.return_value = False
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.current_process = "buy"
        sma.asset_amount = 12
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 4)  # 12 / STEP

        # current_process가 "sell" 일때는 업데이트 되지 않아야함
        sma.current_process = "sell"
        sma.asset_amount = 9
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 4)  # 12 / STEP

        # mock_np.return_value가 True 일때는 업데이트 되지 않아야함
        mock_np.return_value = True
        sma.current_process = "buy"
        sma.asset_amount = 15
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 4)  # 12 / STEP

        mock_np.return_value = False
        sma.current_process = "buy"
        sma.asset_amount = 15
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 0)
        self.assertEqual(sma.process_unit[1], 5)  # 15 / STEP

    @patch("numpy.isnan")
    @patch("pandas.Series")
    def test_update_trading_info_update_process_when_long_lt_short(self, mock_series, mock_np):
        sma = StrategySma0()

        class DummySeriesInverse:
            """ interval에 -1을 곱한 값을 최종 결과로 리턴하는 DummySeries"""

            def rolling(self, interval):
                class DummyRolling:
                    def __init__(self, value):
                        self.return_value = value * -1

                    def mean(self):
                        class DummyValue:
                            pass

                        meanlist = DummyValue()
                        meanlist.values = [self.return_value]
                        return meanlist

                return DummyRolling(interval)

        mock_series.return_value = DummySeriesInverse()
        mock_np.return_value = False
        sma.initialize(100, 10)
        dummy_info = {
            "closing_price": 500,
        }
        sma.current_process = "sell"
        sma.balance = 90000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 30000)  # 90000 / STEP
        self.assertEqual(sma.process_unit[1], 0)

        # current_process가 "buy" 일때는 업데이트 되지 않아야함
        sma.current_process = "buy"
        sma.balance = 90000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 30000)  # 90000 / STEP
        self.assertEqual(sma.process_unit[1], 0)

        # mock_np.return_value가 True 일때는 업데이트 되지 않아야함
        mock_np.return_value = True
        sma.current_process = "sell"
        sma.balance = 30000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "sell")
        self.assertEqual(sma.process_unit[0], 30000)  # 90000 / STEP
        self.assertEqual(sma.process_unit[1], 0)

        mock_np.return_value = False
        sma.current_process = "sell"
        sma.balance = 30000
        sma.update_trading_info(dummy_info)
        self.assertEqual(sma.current_process, "buy")
        self.assertEqual(sma.process_unit[0], 10000)  # 30000 / STEP
        self.assertEqual(sma.process_unit[1], 0)

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sma = StrategySma0()
        sma.update_trading_info("mango")
        self.assertEqual(len(sma.data), 0)

    def test_update_result_append_result(self):
        sma = StrategySma0()
        sma.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request_id": "banana",
            "price": "apple",
            "amount": "kiwi",
            "msg": "melon",
            "balance": 500,
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.result[-1]["type"], "orange")
        self.assertEqual(sma.result[-1]["request_id"], "banana")
        self.assertEqual(sma.result[-1]["price"], "apple")
        self.assertEqual(sma.result[-1]["amount"], "kiwi")
        self.assertEqual(sma.result[-1]["msg"], "melon")
        self.assertEqual(sma.result[-1]["balance"], 500)

    def test_update_result_update_balance_and_asset_amount(self):
        sma = StrategySma0()
        sma.initialize(100, 10)
        self.assertEqual(sma.balance, 100)
        sma.asset_amount = 50

        dummy_result = {
            "type": "buy",
            "request_id": "orange",
            "price": 10,
            "amount": 5,
            "msg": "success",
            "balance": 100,
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 100)
        self.assertEqual(sma.asset_amount, 55)
        self.assertEqual(sma.result[-1]["type"], "buy")
        self.assertEqual(sma.result[-1]["request_id"], "orange")
        self.assertEqual(sma.result[-1]["price"], 10)
        self.assertEqual(sma.result[-1]["amount"], 5)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 100)

        dummy_result = {
            "type": "sell",
            "request_id": "apple",
            "price": 100,
            "amount": 53,
            "msg": "success",
            "balance": 1000,
        }
        sma.update_result(dummy_result)
        self.assertEqual(sma.balance, 1000)
        self.assertEqual(sma.asset_amount, 2)
        self.assertEqual(sma.result[-1]["type"], "sell")
        self.assertEqual(sma.result[-1]["request_id"], "apple")
        self.assertEqual(sma.result[-1]["price"], 100)
        self.assertEqual(sma.result[-1]["amount"], 53)
        self.assertEqual(sma.result[-1]["msg"], "success")
        self.assertEqual(sma.result[-1]["balance"], 1000)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        sma = StrategySma0()
        sma.update_result("orange")
        self.assertEqual(len(sma.result), 0)

    def test_get_request_return_None_when_not_yet_initialized(self):
        sma = StrategySma0()
        request = sma.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_None_when_data_is_empty(self):
        sma = StrategySma0()
        sma.initialize(100, 10, False)
        request = sma.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_None_when_data_is_invaild(self):
        sma = StrategySma0()
        sma.initialize(100, 10, False)
        dummy_info = {}
        sma.update_trading_info(dummy_info)
        request = sma.get_request()
        self.assertEqual(request, None)

    def test_get_request_return_correct_request_at_buy_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        request = sma.get_request()
        self.assertEqual(request["price"], 20000000)
        self.assertEqual(request["amount"], 4000 / 20000000)
        self.assertEqual(request["type"], "buy")

        dummy_info = {}
        dummy_info["closing_price"] = 10000000
        sma.update_trading_info(dummy_info)
        request = sma.get_request()
        self.assertEqual(request["price"], 10000000)
        self.assertEqual(request["amount"], 4000 / 10000000)
        self.assertEqual(request["type"], "buy")

        dummy_info = {}
        dummy_info["closing_price"] = 100
        sma.update_trading_info(dummy_info)
        sma.balance = 2000
        request = sma.get_request()
        self.assertEqual(request["price"], 100)
        self.assertEqual(request["amount"], 2000 / 100)
        self.assertEqual(request["type"], "buy")

    def test_get_request_return_correct_request_at_sell_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        request = sma.get_request()
        self.assertEqual(request["price"], 20000000)
        self.assertEqual(request["amount"], 20)
        self.assertEqual(request["type"], "sell")

        dummy_info = {}
        dummy_info["closing_price"] = 10000000
        sma.asset_amount = 10
        sma.update_trading_info(dummy_info)
        request = sma.get_request()
        self.assertEqual(request["price"], 10000000)
        self.assertEqual(request["amount"], 10)
        self.assertEqual(request["type"], "sell")

    def test_get_request_return_same_datetime_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(10000, 100, True)
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        request = sma.get_request()
        self.assertEqual(request["price"], 20000000)
        self.assertEqual(request["amount"], 20)
        self.assertEqual(request["type"], "sell")
        self.assertEqual(request["date_time"], "2020-02-25T15:41:09")

    def test_get_request_return_turn_over_when_last_data_is_None(self):
        sma = StrategySma0()
        sma.initialize(10000, 100, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        request = sma.get_request()
        self.assertEqual(request["price"], 20000000)
        self.assertEqual(request["amount"], 4000 / 20000000)
        self.assertEqual(request["type"], "buy")

        sma.update_trading_info(None)
        request = sma.get_request()
        self.assertEqual(request["price"], 0)
        self.assertEqual(request["amount"], 0)

    def test_get_request_return_turn_over_when_target_budget_lt_min_price(self):
        sma = StrategySma0()
        sma.initialize(1000, 500, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (300, 0)
        request = sma.get_request()
        self.assertEqual(request["price"], 0)
        self.assertEqual(request["amount"], 0)
        self.assertEqual(request["type"], "buy")

    def test_get_request_return_turn_over_when_process_unit_invalid(self):
        sma = StrategySma0()
        sma.initialize(1000, 500, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (0, 0)
        request = sma.get_request()
        self.assertEqual(request["price"], 0)
        self.assertEqual(request["amount"], 0)
        self.assertEqual(request["type"], "buy")

        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 0)
        request = sma.get_request()
        self.assertEqual(request["price"], 0)
        self.assertEqual(request["amount"], 0)
        self.assertEqual(request["type"], "sell")

    def test_get_request_return_turn_over_when_asset_amount_empty(self):
        sma = StrategySma0()
        sma.initialize(900, 10, False)
        dummy_info = {}
        dummy_info["closing_price"] = 20000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 0
        sma.process_unit = (0, 10)
        request = sma.get_request()
        self.assertEqual(request["price"], 0)
        self.assertEqual(request["amount"], 0)
        self.assertEqual(request["type"], "sell")
