# python -m unittest discover tests/strategy_tests/strategy_dml  *test.py -v
# MUST SET Config.simulation_data_provider_type = "dual" in smtm/config.py
# simulation_data_provider_type = "dual"

import json
import unittest
from smtm import Simulator
from unittest.mock import *

KEY_PERIOD = [
    "220701.000000-220701.195900",
    "220710.040000-220710.235900",
    "220711.200000-220712.155900",
    "220712.160000-220713.115900",
    "220715.040000-220715.235900",
    "220723.120000-220724.075900",
    "220724.130000-220725.085900",
    "220728.120000-220729.075900",
    "220731.000000-220731.195900",
    "220811.230000-220812.185900",
    "220814.040000-220814.235900",
    "220815.000000-220815.195900",
    "220826.160000-220827.115900",
    "220830.000000-220830.195900",
    "221004.080000-221005.035900",
    "221010.040000-221010.235900",
    "221026.170000-221027.125900",
    "221101.000000-221101.195900",
    "221114.040000-221114.235900",
    "221118.080000-221119.035900",
    "230112.160000-230113.115900",
    "230113.100000-230114.055900",
    "230117.160000-230118.115900",
    "230210.000000-230210.195900",
    "230227.120000-230228.075900",
    "230422.130000-230423.085900",
    "230424.080000-230425.035900",
    "230425.220000-230426.175900",
    "230428.120000-230429.075900",
    "230507.160000-230508.115900",
    "230511.200000-230512.155900",
    "230512.160000-230513.115900",
    "230516.000000-230516.195900",
    "230527.160000-230528.115900",
    "230528.120000-230529.075900",
    "230530.040000-230530.235900",
]


class SmlIntegrationTests(unittest.TestCase):
    def test_ITG_run_single_simulation(self):
        result_list = []
        for period in KEY_PERIOD:
            request_list = []
            simulator = Simulator(
                budget=1000000,
                interval=0.0001,
                strategy="DML",
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
        # with open("./dml_test_result.json", "w") as f:
        #     json.dump(result_list, f)

        with open("tests/strategy_tests/strategy_dml/dml_test_result.json", "r") as f:
            expected = json.load(f)

        for result_idx, request_list in enumerate(result_list):
            for request_idx, requst in enumerate(request_list):
                target = expected[result_idx][request_idx]
                try:
                    self.assertEqual(
                        requst["type"], target["type"], f"{result_idx}-{request_idx}"
                    )
                    self.assertEqual(
                        requst["price"], target["price"], f"{result_idx}-{request_idx}"
                    )
                    self.assertEqual(
                        requst["amount"], target["amount"], f"{result_idx}-{request_idx}"
                    )
                    self.assertEqual(
                        requst["date_time"],
                        target["date_time"],
                        f"{result_idx}-{request_idx}",
                    )
                except AssertionError as e:
                    print(f"[FAIL] result_idx:{result_idx} - request_idx:{request_idx}")
                    raise e
