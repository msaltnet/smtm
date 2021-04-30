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

        class DummySeries:
            """rolling의 window인자를 최종 결과로 리턴
            장기 이동평균 값이 단기 이동평균 값보다 큰 상황을 만들기 위함
            """

            def rolling(self, window):
                class DummyRolling:
                    def __init__(self, value):
                        self.return_value = value

                    def mean(self):
                        class DummyValue:
                            pass

                        meanlist = DummyValue()
                        meanlist.values = [self.return_value]
                        return meanlist

                return DummyRolling(window)

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
            """rolling의 window인자에 -1을 곱한 값을 최종 결과로 리턴
            장기 이동평균 값이 단기 이동평균 값보다 작은 상황을 만들기 위함
            """

            def rolling(self, window인자에):
                class DummyRolling:
                    def __init__(self, value):
                        self.return_value = value * -1

                    def mean(self):
                        class DummyValue:
                            pass

                        meanlist = DummyValue()
                        meanlist.values = [self.return_value]
                        return meanlist

                return DummyRolling(window인자에)

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

    def test_get_request_return_correct_request_at_buy_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0002)
        self.assertEqual(requests[0]["type"], "buy")

        dummy_info = {}
        dummy_info["closing_price"] = 10000000
        sma.update_trading_info(dummy_info)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 10000000)
        self.assertEqual(requests[0]["amount"], 0.0004)
        self.assertEqual(requests[0]["type"], "buy")

        dummy_info = {}
        dummy_info["closing_price"] = 100
        sma.update_trading_info(dummy_info)
        sma.balance = 2000
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 100)
        self.assertEqual(requests[0]["amount"], 19.99)
        self.assertEqual(requests[0]["type"], "buy")

    def test_get_request_return_correct_request_at_sell_process(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 20)
        self.assertEqual(requests[0]["type"], "sell")

        dummy_info = {}
        dummy_info["closing_price"] = 10000000
        sma.asset_amount = 10
        sma.update_trading_info(dummy_info)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 10000000)
        self.assertEqual(requests[0]["amount"], 10)
        self.assertEqual(requests[0]["type"], "sell")

    def test_get_request_return_request_with_cancel_requests(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
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

    def test_get_request_return_same_datetime_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        sma.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 20)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 20)
        self.assertEqual(requests[0]["type"], "sell")
        self.assertEqual(requests[0]["date_time"], "2020-02-25T15:41:09")

    def test_get_request_return_turn_over_when_last_data_is_None(self):
        sma = StrategySma0()
        sma.initialize(10000, 100)
        dummy_info = {}
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (4000, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 20000000)
        self.assertEqual(requests[0]["amount"], 0.0002)
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

    def test_get_request_return_turn_over_when_process_unit_invalid_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(1000, 500)
        sma.is_simulation = True
        dummy_info = {}
        dummy_info["date_time"] = "2020-02-25T15:41:09"
        dummy_info["closing_price"] = 20000000
        sma.update_trading_info(dummy_info)
        sma.current_process = "buy"
        sma.process_unit = (0, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)
        self.assertEqual(requests[0]["type"], "buy")

        sma.current_process = "sell"
        sma.asset_amount = 60
        sma.process_unit = (0, 0)
        requests = sma.get_request()
        self.assertEqual(requests[0]["price"], 0)
        self.assertEqual(requests[0]["amount"], 0)
        self.assertEqual(requests[0]["type"], "sell")

    def test_get_request_return_turn_over_when_asset_amount_empty_at_simulation(self):
        sma = StrategySma0()
        sma.initialize(900, 10)
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
