import unittest
from smtm import StrategyBuyAndHold
from unittest.mock import *


class StrategyBuyAndHoldIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_strategy_buy_and_hold_full(self):
        strategy = StrategyBuyAndHold()
        self.assertEqual(strategy.get_request(), None)
        strategy.initialize(50000, 5000)
        # 거래 정보 입력 - 1
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:51:00",
                "opening_price": 11288000.0,
                "high_price": 11304000.0,
                "low_price": 11282000.0,
                "closing_price": 11304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 11304000.0,
            "amount": 0.0008,
        }
        self.assertEqual(request[0]["type"], expected_request["type"])
        self.assertEqual(request[0]["price"], expected_request["price"])
        self.assertEqual(request[0]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 정상 체결 됨
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 11304000.0,
                    "amount": 0.0009,
                    "date_time": "2020-04-30T14:51:00",
                },
                "type": "buy",
                "price": 11304000.0,
                "amount": 0.0009,
                "msg": "success",
                "balance": 0,
                "state": "done",
                "date_time": "2020-04-30T14:51:00",
            }
        )
        self.assertEqual(strategy.balance, 39821)

        # 거래 정보 입력 - 2
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 11304000.0,
                "high_price": 21304000.0,
                "low_price": 11304000.0,
                "closing_price": 21304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 21304000.0,
            "amount": 0.0004,
        }
        self.assertEqual(request[0]["type"], expected_request["type"])
        self.assertEqual(request[0]["price"], expected_request["price"])
        self.assertEqual(request[0]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 요청되었으나 체결 안됨
        self.assertEqual(strategy.balance, 39821)
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 11304000.0,
                    "amount": 0.0009,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 11304000.0,
                "amount": 0.0009,
                "msg": "success",
                "balance": 0,
                "state": "requested",
                "date_time": "2020-04-30T14:52:00",
            }
        )
        self.assertEqual(strategy.balance, 39821)
        last_id = request[0]["id"]

        # 거래 정보 입력 - 3
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 21304000.0,
                "high_price": 21304000.0,
                "low_price": 21304000.0,
                "closing_price": 21304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 21304000.0,
            "amount": 0.0004,
        }
        self.assertEqual(request[0]["type"], "cancel")
        self.assertEqual(request[0]["id"], last_id)
        self.assertEqual(request[1]["type"], expected_request["type"])
        self.assertEqual(request[1]["price"], expected_request["price"])
        self.assertEqual(request[1]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 일부 체결됨
        self.assertEqual(strategy.balance, 39821)
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 21304000.0,
                    "amount": 0.0009,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 21304000.0,
                "amount": 0.0002,
                "msg": "success",
                "balance": 0,
                "state": "done",
                "date_time": "2020-04-30T14:52:00",
            }
        )
        self.assertEqual(strategy.balance, 35558)

        # 거래 정보 입력 - 4
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 21304000.0,
                "high_price": 41304000.0,
                "low_price": 21304000.0,
                "closing_price": 41304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 41304000.0,
            "amount": 0.0002,
        }
        self.assertEqual(request[0]["type"], expected_request["type"])
        self.assertEqual(request[0]["price"], expected_request["price"])
        self.assertEqual(request[0]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 정상 체결됨
        self.assertEqual(strategy.balance, 35558)
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 41304000.0,
                    "amount": 0.0009,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 41304000.0,
                "amount": 0.0002,
                "msg": "success",
                "balance": 0,
                "state": "done",
                "date_time": "2020-04-30T14:52:00",
            }
        )
        self.assertEqual(strategy.balance, 27293)

        # 거래 정보 입력 - 5
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 41304000.0,
                "high_price": 61304000.0,
                "low_price": 41304000.0,
                "closing_price": 61304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 61304000.0,
            "amount": 0.0001,
        }
        self.assertEqual(request[0]["type"], expected_request["type"])
        self.assertEqual(request[0]["price"], expected_request["price"])
        self.assertEqual(request[0]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 정상 체결됨
        self.assertEqual(strategy.balance, 27293)
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 61304000.0,
                    "amount": 0.0009,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 61304000.0,
                "amount": 0.0002,
                "msg": "success",
                "balance": 0,
                "state": "done",
                "date_time": "2020-04-30T14:52:00",
            }
        )
        self.assertEqual(strategy.balance, 15026)

        # 거래 정보 입력 - 6
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 61304000.0,
                "high_price": 61304000.0,
                "low_price": 61304000.0,
                "closing_price": 61304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        expected_request = {
            "type": "buy",
            "price": 61304000.0,
            "amount": 0.0001,
        }
        self.assertEqual(request[0]["type"], expected_request["type"])
        self.assertEqual(request[0]["price"], expected_request["price"])
        self.assertEqual(request[0]["amount"], expected_request["amount"])
        # 거래 결과 입력 - 정상 체결됨
        self.assertEqual(strategy.balance, 15026)
        strategy.update_result(
            {
                "request": {
                    "id": request[0]["id"],
                    "type": "buy",
                    "price": 61304000.0,
                    "amount": 0.0002,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 61304000.0,
                "amount": 0.0002,
                "msg": "success",
                "balance": 0,
                "state": "done",
                "date_time": "2020-04-30T14:52:00",
            }
        )
        self.assertEqual(strategy.balance, 2759)

        # 거래 정보 입력 - 7
        strategy.update_trading_info(
            {
                "market": "KRW-BTC",
                "date_time": "2020-04-30T14:52:00",
                "opening_price": 61304000.0,
                "high_price": 61304000.0,
                "low_price": 61304000.0,
                "closing_price": 61304000.0,
                "acc_price": 587101574.8949,
                "acc_volume": 51.97606868,
            }
        )
        # 거래 요청 정보 생성
        request = strategy.get_request()
        self.assertEqual(request, None)
        self.assertEqual(strategy.balance, 2759)
