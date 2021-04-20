import os
import time
from datetime import datetime
import unittest
from unittest.mock import *
from smtm import BithumbTrader


class BithumbTraderIntegrationTester(unittest.TestCase):
    MAIN_STATEMENT = "아무키나 입력하면 다음으로 진행됩니다. s: 건너뛰기, q: 중단 > "
    NEXT_STATEMENT = "아무키나 입력하면 다음으로 진행됩니다."
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def setUp(self):
        self.test_list = [
            {
                "preparation": "현재 계좌 잔고를 조회합니다.",
                "action": self.query_account,
                "verification": "실제 계좌 정보와 일치하는지 확인하세요.",
            },
            {
                "preparation": "최근 거래 가격으로 총액 10,000원 만큼 BTC를 매수합니다.",
                "action": self.buy_btc_10000,
                "verification": "매수 결과를 확인하세요.",
            },
            {
                "preparation": "현재 계좌 잔고를 조회합니다.",
                "action": self.query_account,
                "verification": "실제 계좌 정보와 일치하는지 확인하세요.",
            },
            {
                "preparation": "최근 거래 가격으로 0.00014864 만큼 BTC를 매도합니다.",
                "action": self.sell_btc_00014864,
                "verification": "매도 결과를 확인하세요.",
            },
            {
                "preparation": "현재 계좌 잔고를 조회합니다.",
                "action": self.query_account,
                "verification": "실제 계좌 정보와 일치하는지 확인하세요.",
            },
        ]

    def tearDown(self):
        pass

    def test_main(self):
        """main 함수"""
        self.bithumbTrader = BithumbTrader()
        for test_index in range(len(self.test_list)):
            test = self.test_list[test_index]
            print(f"{test_index + 1} 번째 테스트 시작 ------------------------")
            print(test["preparation"])
            response = input(self.MAIN_STATEMENT)
            if response == "q":
                break
            elif response == "s":
                continue

            test["action"]()
            time.sleep(2)
            print(test["verification"])
            print(f"{test_index + 1} 번째 테스트 종료 ------------------------")

        print("tests all done")

    def query_account(self):
        def callback(info):
            print(info)
            self.assertTrue(info["balance"] is not None)
            print(f"# balance {info['balance']}")
            asset = info["asset"]
            self.assertTrue(asset is not None)
            for key, value in asset.items():
                print(f"# {key} : price {value[0]}, amount {value[1]}")

        self.bithumbTrader.get_account_info(callback)

    def buy_btc_10000(self):
        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        request = {
            "id": "test" + str(round(time.time(), 3)),
            "type": "buy",
            "price": 10000,
            "amount": None,
            "date_time": now,
        }

        def callback(info):
            print(info)
            # self.assertEqual(len(info) > 0)

        self.bithumbTrader.send_request(request, callback)

    def sell_btc_00014864(self):
        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        request = {
            "id": "test" + str(round(time.time(), 3)),
            "type": "sell",
            "price": None,
            "amount": 0.00014864,
            "date_time": now,
        }

        def callback(info):
            print(info)
            # self.assertEqual(len(info) > 0)

        self.bithumbTrader.send_request(request, callback)

    def execute_action(self):
        print("테스트 코드가 실행 되었습니다!!! ===")
