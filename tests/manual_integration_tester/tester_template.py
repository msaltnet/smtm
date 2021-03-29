import os
import unittest
from unittest.mock import *


class Tester(unittest.TestCase):
    MAIN_STATEMENT = "아무키나 입력하면 다음으로 진행됩니다. s: 건너뛰기, q: 중단 > "

    def setUp(self):
        self.test_list = [
            {
                "preparation": "첫번째 테스트를 준비하세요.",
                "action": self.print_help,
                "verification": "첫번째 테스트 결과를 확인하세요.",
            },
            {
                "preparation": "두번째 테스트를 준비하세요.",
                "action": self.print_help,
                "verification": "두번째 테스트 결과를 확인하세요.",
            },
        ]

    def tearDown(self):
        pass

    def test_main(self):
        """main 함수"""

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
            print(test["verification"])

            response = input(self.MAIN_STATEMENT)
            if response == "q":
                break
            elif response == "s":
                continue

            print(f"{test_index + 1} 번째 테스트 종료 ------------------------")

        print("tests all done")

    def print_help(self):
        print("테스트 코드가 실행 되었습니다!!! ===")
