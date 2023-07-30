import json
import unittest
from smtm import Simulator
from unittest.mock import *

KEY_PERIOD = [
    "220701.000000-220701.195900",
    "220715.040000-220715.235900",
    "220724.130000-220725.085900",
    "220728.120000-220729.075900",
    "220811.230000-220812.185900",
    "220815.000000-220815.195900",
    "220830.000000-220830.195900",
    "221004.080000-221005.035900",
    "221026.170000-221027.125900",
    "221114.040000-221114.235900",
    "221118.080000-221119.035900",
    "230112.160000-230113.115900",
    "230113.100000-230114.055900",
    "230117.160000-230118.115900",
    "230227.120000-230228.075900",
    "230422.130000-230423.085900",
    "230424.080000-230425.035900",
    "230425.220000-230426.175900",
    "230428.120000-230429.075900",
    "230512.160000-230513.115900",
]


class SmaIntegrationTests(unittest.TestCase):
    def test_ITG_run_single_simulation(self):
        result_list = []
        for period in KEY_PERIOD:
            request_list = []
            simulator = Simulator(
                budget=1000000,
                interval=0.0001,
                strategy="SMA",
                from_dash_to=period,
                currency="BTC",
            )
            simulator.run_single()

            for request in simulator.operator.analyzer.request_list:
                request_list.append(
                    {
                        "type": request["type"],
                        "price": request["price"],
                        "amount": request["amount"],
                        "date_time": request["date_time"],
                    }
                )
            result_list.append(request_list)

        # If you want to update the expected result, uncomment the following code.
        # with open("./sma_test_result.json", "w") as f:
        #     json.dump(result_list, f)

        with open("./integration_tests/strategy_sma/sma_test_result.json", "r") as f:
            expected = json.load(f)

        for result_idx, request_list in enumerate(result_list):
            for request_idx, requst in enumerate(request_list):
                target = expected[result_idx][request_idx]
                self.assertEqual(requst["type"], target["type"], f"{result_idx}-{request_idx}")
                self.assertEqual(requst["price"], target["price"], f"{result_idx}-{request_idx}")
                self.assertEqual(requst["amount"], target["amount"], f"{result_idx}-{request_idx}")
                self.assertEqual(
                    requst["date_time"], target["date_time"], f"{result_idx}-{request_idx}"
                )
