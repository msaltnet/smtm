import unittest
from smtm import StrategyHey
from unittest.mock import *
import numpy as np

class StrategyHeyTests(unittest.TestCase):
    def test_initialize_update_initial_balance(self):
        sas = StrategyHey()
        self.assertEqual(sas.is_intialized, False)
        sas.initialize(50000, 50)
        self.assertEqual(sas.budget, 50000)
        self.assertEqual(sas.balance, 50000)
        self.assertEqual(sas.min_price, 50)
        self.assertEqual(sas.is_intialized, True)
        sas.initialize(100, 10)
        self.assertEqual(sas.budget, 50000)
        self.assertEqual(sas.balance, 50000)
        self.assertEqual(sas.min_price, 50)

    def test_update_trading_info_append_info_to_data(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        dummy_info = [
            {
                "type": "primary_candle",
                "market": "orange",
                "date_time": "2020-02-25T15:41:09",
                "closing_price": 500,
            }
        ]
        sas.update_trading_info(dummy_info)
        self.assertEqual(sas.data.pop(), dummy_info[0])

    def test_update_trading_info_ignore_info_when_not_yet_initialzed(self):
        sas = StrategyHey()
        sas.update_trading_info("mango")
        self.assertEqual(len(sas.data), 0)

    def test_update_result_append_result(self):
        sas = StrategyHey()
        sas.initialize(100, 10)

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.result[-1]["type"], "orange")
        self.assertEqual(sas.result[-1]["request"]["id"], "banana")
        self.assertEqual(sas.result[-1]["price"], "777000")
        self.assertEqual(sas.result[-1]["amount"], "0.0001234")
        self.assertEqual(sas.result[-1]["msg"], "melon")
        self.assertEqual(sas.result[-1]["balance"], 500)

    def test_update_result_remove_from_waiting_requests(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        sas.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.result[-1]["type"], "orange")
        self.assertEqual(sas.result[-1]["request"]["id"], "banana")
        self.assertEqual(sas.result[-1]["price"], "777000")
        self.assertEqual(sas.result[-1]["amount"], "0.0001234")
        self.assertEqual(sas.result[-1]["msg"], "melon")
        self.assertEqual(sas.result[-1]["balance"], 500)
        self.assertFalse("banana" in sas.waiting_requests)

    def test_update_result_insert_into_waiting_requests(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        sas.waiting_requests["banana"] = "banana_request"

        dummy_result = {
            "type": "orange",
            "request": {"id": "banana"},
            "price": "777000",
            "amount": "0.0001234",
            "msg": "melon",
            "balance": 500,
            "state": "requested",
        }
        sas.update_result(dummy_result)
        self.assertEqual(len(sas.result), 0)
        self.assertTrue("banana" in sas.waiting_requests)

    def test_update_result_update_balance_and_asset_amount(self):
        sas = StrategyHey()
        sas.initialize(100000, 10)
        self.assertEqual(sas.balance, 100000)
        sas.asset_amount = 50

        dummy_result = {
            "type": "buy",
            "request": {"id": "orange"},
            "price": 1000,
            "amount": 5,
            "msg": "success",
            "balance": 100,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.balance, 94998)
        self.assertEqual(sas.asset_amount, 55)
        self.assertEqual(sas.result[-1]["type"], "buy")
        self.assertEqual(sas.result[-1]["request"]["id"], "orange")
        self.assertEqual(sas.result[-1]["price"], 1000)
        self.assertEqual(sas.result[-1]["amount"], 5)
        self.assertEqual(sas.result[-1]["msg"], "success")
        self.assertEqual(sas.result[-1]["balance"], 100)

        dummy_result = {
            "type": "sell",
            "request": {"id": "apple"},
            "price": 1000,
            "amount": 53,
            "msg": "success",
            "balance": 1000,
            "state": "done",
        }
        sas.update_result(dummy_result)
        self.assertEqual(sas.balance, 147972)
        self.assertEqual(sas.asset_amount, 2)
        self.assertEqual(sas.result[-1]["type"], "sell")
        self.assertEqual(sas.result[-1]["request"]["id"], "apple")
        self.assertEqual(sas.result[-1]["price"], 1000)
        self.assertEqual(sas.result[-1]["amount"], 53)
        self.assertEqual(sas.result[-1]["msg"], "success")
        self.assertEqual(sas.result[-1]["balance"], 1000)

    def test_update_result_ignore_result_when_not_yet_initialized(self):
        sas = StrategyHey()
        sas.update_result("orange")
        self.assertEqual(len(sas.result), 0)

    def test_get_request_return_None(self):
        sas = StrategyHey()
        sas.initialize(100, 10)
        requests = sas.get_request()
        self.assertEqual(requests, None)

    def test_update_atr_info_should_update_correctly(self):
        detector = StrategyHey()
        detector.ATR_PERIOD = 3

        # 초기 상태 확인
        self.assertEqual(len(detector.data), 0)
        self.assertIsNone(detector.prev_close)
        self.assertIsNone(detector.atr)

        # 새로운 거래 정보 추가 및 업데이트
        new_price_info_1 = {"date_time": "2024-04-25T09:00:00", "opening_price": 10000, "high_price": 10500, "low_price": 9800, "closing_price": 10300}
        detector.data.append(new_price_info_1)
        detector.update_atr_info(new_price_info_1)

        self.assertEqual(len(detector.data), 1)
        self.assertIsNone(detector.prev_close)
        self.assertIsNone(detector.atr)  # 최소 2개의 거래 정보가 필요함

        new_price_info_2 = {"date_time": "2024-04-25T09:30:00", "opening_price": 10300, "high_price": 10600, "low_price": 10000, "closing_price": 10450}
        detector.data.append(new_price_info_2)
        detector.update_atr_info(new_price_info_2)

        self.assertEqual(len(detector.data), 2)
        self.assertEqual(detector.prev_close, 10300)  # 이전 거래일 종가 업데이트 확인
        self.assertEqual(detector.atr, 600.0)

        new_price_info_3 = {"date_time": "2024-04-25T10:00:00", "opening_price": 10450, "high_price": 10700, "low_price": 10200, "closing_price": 10580}
        detector.data.append(new_price_info_3)
        detector.update_atr_info(new_price_info_3)

        self.assertEqual(len(detector.data), 3)
        self.assertEqual(detector.prev_close, 10450)
        self.assertEqual(detector.atr, 550.0)

    def test_detect_breakout_signals_should_return_correct_value(self):
        detector = StrategyHey()
        detector.ATR_PERIOD = 3
        detector.VOLATILITY_BREAKOUT = 1.2

        # 변동성 돌파 신호 감지 테스트
        new_price_info_1 = {"date_time": "2024-04-25T09:00:00", "opening_price": 10000, "high_price": 10500, "low_price": 9800, "closing_price": 10300}
        new_price_info_2 = {"date_time": "2024-04-25T09:30:00", "opening_price": 10300, "high_price": 10600, "low_price": 10000, "closing_price": 10450}

        detector.data.append(new_price_info_1)
        detector.update_atr_info(new_price_info_1)

        detector.data.append(new_price_info_2)
        detector.update_atr_info(new_price_info_2)

        breakout_buy_signal, breakout_sell_signal = detector.detect_breakout_signals()

        # 최소 2개의 거래 정보가 필요하므로 초기값은 False 여야 함
        self.assertFalse(breakout_buy_signal)
        self.assertFalse(breakout_sell_signal)

        # 추가 정보로 변동성 돌파 신호 확인
        new_price_info_3 = {"date_time": "2024-04-25T10:00:00", "opening_price": 10450, "high_price": 12700, "low_price": 10200, "closing_price": 10580}
        detector.data.append(new_price_info_3)
        detector.update_atr_info(new_price_info_3)

        breakout_buy_signal, breakout_sell_signal = detector.detect_breakout_signals()

        # 변동성 돌파 신호 예상 확인
        self.assertTrue(breakout_buy_signal)
        self.assertFalse(breakout_sell_signal)

        # 추가 정보로 변동성 돌파 신호 확인
        new_price_info_4 = {"date_time": "2024-04-25T10:30:00", "opening_price": 10580, "high_price": 10800, "low_price": 8200, "closing_price": 10650}
        detector.data.append(new_price_info_4)
        detector.update_atr_info(new_price_info_4)

        breakout_buy_signal, breakout_sell_signal = detector.detect_breakout_signals()

        # 변동성 돌파 신호 예상 확인
        self.assertFalse(breakout_buy_signal)
        self.assertTrue(breakout_sell_signal)
