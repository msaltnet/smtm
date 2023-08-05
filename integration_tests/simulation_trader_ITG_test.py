import unittest
from smtm import SimulationTrader, Config
from unittest.mock import *


class SimulationTraderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.interval = Config.candle_interval
        Config.candle_interval = 60

    def tearDown(self):
        Config.candle_interval = self.interval

    def test_ITG_simulation_trader_full(self):
        trader = SimulationTrader()
        end_date = "2020-04-30T16:30:00"
        trader.initialize_simulation(end=end_date, count=50, budget=50000)

        # 1 거래 요청 - buy
        request = [
            {
                "id": "request_1",
                "type": "buy",
                "price": 11372000.0,
                "amount": 0.0009,
                "date_time": "2020-04-30T14:40:00",
            }
        ]
        expected_result = {
            "request": {
                "id": "request_1",
                "type": "buy",
                "price": 11372000.0,
                "amount": 0.0009,
                "date_time": "2020-04-30T14:40:00",
            },
            "type": "buy",
            "price": 11372000.0,
            "amount": 0.0009,
            "msg": "success",
            "balance": 39760,
            "state": "done",
            "date_time": "2020-04-30T15:40:00",
        }

        result = None

        def send_request_callback(callback_result):
            nonlocal result
            result = callback_result

        trader.send_request(request, send_request_callback)
        self.assertEqual(result, expected_result)

        # 2 거래 요청 - sell
        request = [
            {
                "id": "request_2",
                "type": "sell",
                "price": 11292000.0,
                "amount": 0.0003,
                "date_time": "2020-04-30T14:41:00",
            }
        ]
        expected_result = {
            "request": {
                "id": "request_2",
                "type": "sell",
                "price": 11292000.0,
                "amount": 0.0003,
                "date_time": "2020-04-30T14:41:00",
            },
            "type": "sell",
            "price": 11292000.0,
            "amount": 0.0003,
            "msg": "success",
            "balance": 43146,
            "state": "done",
            "date_time": "2020-04-30T15:41:00",
        }

        result = None

        def send_request_callback(callback_result):
            nonlocal result
            result = callback_result

        trader.send_request(request, send_request_callback)
        self.assertEqual(result, expected_result)

        # 3 계좌 정보 요청
        expected_account_info = {
            "balance": 43146,
            "asset": {"KRW-BTC": (11372000.0, 0.0006)},
            "quote": {"KRW-BTC": 11370000.0},
            "date_time": "2020-04-30T15:42:00",
        }

        account_info = trader.get_account_info()
        self.assertEqual(account_info, expected_account_info)

        # 4 거래 요청 - buy 큰 금액으로 매수 시도
        request = [
            {
                "id": "request_3",
                "type": "sell",
                "price": 13292000.0,
                "amount": 0.0003,
                "date_time": "2020-04-30T14:43:00",
            }
        ]
        expected_result = "pass"
        result = None

        def send_request_callback(callback_result):
            nonlocal result
            result = callback_result

        trader.send_request(request, send_request_callback)
        self.assertEqual(result, expected_result)

        # 5 계좌 정보 요청 - 변함 없음 확인
        expected_account_info = {
            "balance": 43146,
            "asset": {"KRW-BTC": (11372000.0, 0.0006)},
            "quote": {"KRW-BTC": 11365000.0},
            "date_time": "2020-04-30T15:43:00",
        }

        account_info = trader.get_account_info()
        self.assertEqual(account_info, expected_account_info)

        # 6 거래 요청 - sell 보유 수량보다 큰 수량 매도
        request = [
            {
                "id": "request_4",
                "type": "sell",
                "price": 11302000.0,
                "amount": 0.0013,
                "date_time": "2020-04-30T14:44:00",
            }
        ]
        expected_result = {
            "request": {
                "id": "request_4",
                "type": "sell",
                "price": 11302000.0,
                "amount": 0.0013,
                "date_time": "2020-04-30T14:44:00",
            },
            "type": "sell",
            "price": 11302000.0,
            "amount": 0.0006,
            "msg": "success",
            "balance": 49924,
            "state": "done",
            "date_time": "2020-04-30T15:43:00",
        }

        result = None

        def send_request_callback(callback_result):
            nonlocal result
            result = callback_result

        trader.send_request(request, send_request_callback)
        print(result)
        self.assertEqual(result, expected_result)

        # 7 계좌 정보 요청
        expected_account_info = {
            "balance": 49924,
            "asset": {},
            "quote": {"KRW-BTC": 11358000.0},
            "date_time": "2020-04-30T15:44:00",
        }

        account_info = trader.get_account_info()
        self.assertEqual(account_info, expected_account_info)
