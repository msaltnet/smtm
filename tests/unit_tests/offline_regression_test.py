"""Synthetic suite semantics, fail-closed comparison and guarded CLI contracts."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import evaluate_offline as evaluation
from tools import evaluate_regression as regression

FIXTURES = evaluation.ROOT / "tests/fixtures/evaluation"


class OfflineRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = regression.run_suite(sorted(FIXTURES.glob("*.json")))

    def test_market_paths_have_independently_calculated_accounts(self):
        reports = regression.indexed_reports(self.suite)
        for name, price, equity, bnh_equity in [
            ("rising", 130, 1060, 1113.028),
            ("falling", 70, 940, 870.556),
            ("sideways", 100, 1000, 1000),
        ]:
            with self.subTest(name=name):
                bnh, llm = reports["synthetic-" + name + "-v1"]["arms"]
                self.assertEqual(
                    llm["summary"]["final_account"],
                    {
                        "cash": 800.0,
                        "asset_amount": 2.0,
                        "equity": equity,
                        "mark_price": price,
                        "open_orders": 0,
                    },
                )
                self.assertAlmostEqual(
                    bnh["summary"]["final_account"]["equity"], bnh_equity
                )
                self.assertEqual(
                    llm["summary"]["outcome_counts"], {"requests_emitted": 1, "hold": 3}
                )
                self.assertEqual(llm["summary"]["filled_orders"], 1)

    def test_rejections_and_missing_first_quote_cannot_trade(self):
        report = regression.indexed_reports(self.suite)["synthetic-rejections-v1"]
        bnh, llm = report["arms"]
        for arm in (bnh, llm):
            self.assertEqual(arm["ticks"][0]["account"]["equity"], 1000)
            self.assertIsNone(arm["ticks"][0]["account"]["mark_price"])
            self.assertEqual(arm["ticks"][0]["fake_calls"], [])
        self.assertEqual(
            llm["summary"]["outcome_counts"],
            {"missing_primary_candle": 1, "decision_rejected": 3},
        )
        self.assertEqual(llm["summary"]["final_account"]["equity"], 1000)
        self.assertEqual(llm["summary"]["fake_call_count"], 3)
        self.assertTrue(
            all(not tick["requests"] and not tick["events"] for tick in llm["ticks"])
        )

    def test_repeat_and_reordered_scenarios_match_without_mutation(self):
        candidate = regression.run_suite(
            list(reversed(sorted(FIXTURES.glob("*.json"))))
        )
        old = copy.deepcopy(self.suite)
        self.assertTrue(regression.compare_suites(self.suite, candidate)["matches"])
        self.assertEqual(old, self.suite)

    def test_only_explicit_provenance_and_timing_are_ignored(self):
        candidate = copy.deepcopy(self.suite)
        for report in candidate["reports"]:
            report["runtime"] = {"created_at_utc": "different", "python": "different"}
            report["fixture_file_sha256"] = "different whitespace"
            report["source_sha256"]["tools/evaluate_offline.py"] = "changed"
            report["source_bundle_sha256"] = "changed"
            for arm in report["arms"]:
                arm["summary"]["local_decision_latency_ms"] = {
                    "samples": 999,
                    "mean": 888,
                }
                for tick in arm["ticks"]:
                    tick["local_decision_latency_ms"] = 999
        comparison = regression.compare_suites(self.suite, candidate)
        self.assertTrue(comparison["matches"])
        self.assertEqual(len(comparison["source_changed_scenarios"]), 5)

    def test_behavior_changes_have_paths(self):
        for section in ("cash", "outcome", "events", "tokens", "fixture", "new_field"):
            with self.subTest(section=section):
                candidate = copy.deepcopy(self.suite)
                report = candidate["reports"][0]
                arm = report["arms"][1]
                if section == "cash":
                    arm["summary"]["final_account"]["cash"] += 1
                elif section == "outcome":
                    arm["ticks"][0]["outcome"] = "hold"
                elif section == "events":
                    arm["ticks"][0]["events"] = []
                elif section == "tokens":
                    arm["summary"]["scripted_token_totals"]["input_tokens"] += 1
                elif section == "fixture":
                    report["fixture_sha256"] = "changed"
                else:
                    arm["new_field"] = True
                result = regression.compare_suites(self.suite, candidate)
                self.assertFalse(result["matches"])
                self.assertTrue(result["changed_paths"][report["scenario_id"]])

    def test_added_removed_and_duplicate_scenarios(self):
        candidate = copy.deepcopy(self.suite)
        removed = candidate["reports"].pop()
        result = regression.compare_suites(self.suite, candidate)
        self.assertEqual(result["changed_paths"][removed["scenario_id"]], ["removed"])
        result = regression.compare_suites(candidate, self.suite)
        self.assertEqual(result["changed_paths"][removed["scenario_id"]], ["added"])
        candidate["reports"].append(candidate["reports"][0])
        with self.assertRaises(ValueError):
            regression.compare_suites(self.suite, candidate)

    def test_invalid_artifacts_do_not_pass(self):
        for value in (
            {},
            {
                "schema_version": True,
                "evaluation_kind": "offline_scripted_suite",
                "reports": self.suite["reports"],
            },
            dict(self.suite, reports=[]),
        ):
            with self.assertRaises(ValueError):
                regression.compare_suites(self.suite, value)
        invalid = copy.deepcopy(self.suite)
        invalid["reports"][0]["evaluation_kind"] = "live"
        with self.assertRaises(ValueError):
            regression.compare_suites(self.suite, invalid)

    def test_malformed_reports_cannot_match_themselves(self):
        for mutation in (
            "boolean_version",
            "summary",
            "ticks",
            "tick",
            "identity",
            "config",
        ):
            candidate = copy.deepcopy(self.suite)
            report = candidate["reports"][0]
            if mutation == "boolean_version":
                report["schema_version"] = True
            elif mutation == "summary":
                report["arms"][0]["summary"] = {}
            elif mutation == "ticks":
                report["arms"][0]["ticks"] = []
            elif mutation == "tick":
                report["arms"][0]["ticks"][0] = {}
            elif mutation == "identity":
                del report["fixture_sha256"]
            else:
                report["config"] = {}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                regression.compare_suites(candidate, candidate)

    def test_config_requires_every_evaluator_field_and_type(self):
        strings = (
            "currency",
            "cash_accounting",
            "slippage",
            "timestamp_timezone",
            "execution",
            "end_policy",
        )
        numbers = ("initial_cash", "min_order_value", "fees")
        for field in strings + numbers:
            invalid_values = (None, True, [], {})
            if field in strings:
                invalid_values += (0, "", "   ")
            else:
                invalid_values += ("0", float("nan"), float("inf"), -float("inf"))
            for value in ("missing",) + invalid_values:
                candidate = copy.deepcopy(self.suite)
                config = candidate["reports"][0]["config"]
                if value == "missing":
                    del config[field]
                else:
                    config[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        regression.compare_suites(candidate, candidate)
        candidate = copy.deepcopy(self.suite)
        candidate["reports"][0]["config"] = {"currency": "BTC"}
        with self.assertRaises(ValueError):
            regression.compare_suites(candidate, candidate)

    def test_valid_config_changes_remain_semantic_differences(self):
        changes = {
            "initial_cash": 2000.0,
            "min_order_value": 20,
            "fees": 0.001,
            "currency": "ETH",
            "cash_accounting": "rounded",
            "slippage": "modeled",
            "timestamp_timezone": "Asia/Seoul",
            "execution": "next_close",
            "end_policy": "keep_pending",
        }
        for field, value in changes.items():
            candidate = copy.deepcopy(self.suite)
            report = candidate["reports"][0]
            report["config"][field] = value
            with self.subTest(field=field):
                result = regression.compare_suites(self.suite, candidate)
                self.assertFalse(result["matches"])
                self.assertEqual(
                    result["changed_paths"][report["scenario_id"]],
                    ['$["config"]["' + field + '"]'],
                )

    def test_diff_retains_numeric_types_and_list_length(self):
        self.assertEqual(
            regression.differences({"x": [1]}, {"x": [True, 2]}),
            ['$["x"][0]', '$["x"][1]'],
        )

    def test_cli_capture_compare_difference_and_no_overwrite(self):
        script = evaluation.ROOT / "tools/evaluate_regression.py"
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)

            def run(output, baseline=None, fixtures=FIXTURES):
                args = [
                    sys.executable,
                    "-S",
                    str(script),
                    "--fixtures",
                    str(fixtures),
                    "--output",
                    str(output),
                ]
                if baseline:
                    args += ["--baseline", str(baseline)]
                return subprocess.run(
                    args, cwd=temp, capture_output=True, text=True, timeout=20
                )

            baseline, candidate = temp / "baseline.json", temp / "candidate.json"
            self.assertEqual(run(baseline).returncode, 0)
            original = baseline.read_bytes()
            self.assertEqual(run(candidate, baseline).returncode, 0)
            altered = json.loads(original)
            altered["reports"][0]["arms"][1]["summary"]["filled_orders"] += 1
            mutated = temp / "mutated.json"
            mutated.write_text(json.dumps(altered))
            self.assertEqual(run(temp / "changed.json", mutated).returncode, 1)
            self.assertFalse(
                json.loads((temp / "changed.json").read_text())["comparison"]["matches"]
            )
            for index, config in enumerate(
                (
                    {"currency": "BTC"},
                    dict(altered["reports"][0]["config"], initial_cash=True),
                    dict(altered["reports"][0]["config"], fees="0"),
                )
            ):
                malformed = json.loads(original)
                malformed["reports"][0]["config"] = config
                invalid = temp / ("invalid-" + str(index) + ".json")
                invalid.write_text(json.dumps(malformed))
                output = temp / ("invalid-output-" + str(index) + ".json")
                result = run(output, invalid)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("config.", result.stderr)
                self.assertFalse(output.exists())
            self.assertEqual(run(baseline).returncode, 2)
            self.assertEqual(baseline.read_bytes(), original)
            empty = temp / "empty"
            empty.mkdir()
            self.assertEqual(run(temp / "empty.json", fixtures=empty).returncode, 2)
            self.assertFalse((temp / "empty.json").exists())
            self.assertEqual(
                run(temp / "bad.json", fixtures=temp / "absent").returncode, 2
            )


if __name__ == "__main__":
    unittest.main()
