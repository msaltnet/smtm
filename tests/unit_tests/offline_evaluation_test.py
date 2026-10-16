"""Offline evaluation contracts using only synthetic JSON and stdlib tools."""
import copy
import importlib
import json
import math
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import evaluate_offline as evaluation


FIXTURE = evaluation.ROOT / "tests/fixtures/evaluation/synthetic-smoke-v1.json"


def fixture():
    """Return fresh fixture data for each mutation test."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def semantics(report):
    """Discard only explicitly nondeterministic runtime and local timings."""
    result = copy.deepcopy(report)
    result.pop("runtime")
    for arm in result["arms"]:
        arm["summary"].pop("local_decision_latency_ms")
        for tick in arm["ticks"]:
            tick.pop("local_decision_latency_ms")
    return result


class OfflineEvaluationTests(unittest.TestCase):
    """Compare actual strategy behavior and exact replay/accounting semantics."""

    def test_fixture_produces_expected_independent_portfolios(self):
        """Known synthetic fills prove arithmetic without asserting model quality."""
        report = evaluation.evaluate(fixture())
        baseline, llm = report["arms"]
        self.assertAlmostEqual(baseline["summary"]["final_account"]["equity"], 1005.0435)
        self.assertEqual(baseline["summary"]["filled_orders"], 5)
        self.assertEqual(baseline["summary"]["failed_orders"], 2)  # Real BNH emits zero size.
        self.assertEqual(llm["summary"]["final_account"]["cash"], 890)
        self.assertEqual(llm["summary"]["final_account"]["asset_amount"], 1)
        self.assertEqual(llm["summary"]["final_account"]["equity"], 990)
        self.assertAlmostEqual(llm["summary"]["return_fraction"], -0.01)
        self.assertAlmostEqual(llm["summary"]["max_sampled_drawdown_fraction"], 40 / 1020)
        self.assertEqual(llm["summary"]["canceled_orders"], 1)
        self.assertEqual(llm["summary"]["final_account"]["open_orders"], 0)

    def test_repeated_runs_have_identical_semantics_and_detach_input(self):
        """Only timestamps and measured local latencies differ across replay."""
        value = fixture()
        before = copy.deepcopy(value)
        first, second = evaluation.evaluate(value), evaluation.evaluate(value)
        self.assertEqual(semantics(first), semantics(second))
        self.assertEqual(value, before)
        first["arms"][0]["ticks"][0]["requests"][0]["price"] = -1
        self.assertEqual(second["arms"][0]["ticks"][0]["requests"][0]["price"], 100)

    def test_dictionary_key_order_does_not_change_prompts(self):
        """Canonical semantic input hashes imply identical real prompt content."""
        value = fixture()
        reordered = json.loads(json.dumps(value, sort_keys=True))
        self.assertEqual(semantics(evaluation.evaluate(value)),
                         semantics(evaluation.evaluate(reordered)))

    def test_arms_share_ordered_snapshot_hashes(self):
        """Every arm receives the same complete per-tick input sequence."""
        value = fixture()
        expected = [evaluation.digest(t["snapshot"]) for t in value["ticks"]]
        for arm in evaluation.evaluate(value)["arms"]:
            self.assertEqual([t["snapshot_sha256"] for t in arm["ticks"]], expected)
            self.assertEqual([t["at"] for t in arm["ticks"]], [t["at"] for t in value["ticks"]])

    def test_missing_primary_skips_both_arms_without_stale_decision(self):
        """An empty snapshot cannot advance scripts or repeat the last order."""
        for arm in evaluation.evaluate(fixture())["arms"]:
            row = arm["ticks"][4]
            self.assertEqual(row["outcome"], "missing_primary_candle")
            self.assertEqual(row["requests"], [])
            self.assertEqual(row["fake_calls"], [])
            self.assertIsNone(row["local_decision_latency_ms"])
            self.assertEqual(row["account"], arm["ticks"][3]["account"])

    def test_failures_and_hold_are_separate_outcomes(self):
        """Provider errors, absent tool calls and rejected decisions stay visible."""
        llm = evaluation.evaluate(fixture())["arms"][1]
        self.assertEqual([x["outcome"] for x in llm["ticks"]], [
            "requests_emitted", "hold", "requests_emitted", "decision_rejected",
            "missing_primary_candle", "provider_error", "missing_decision_tool", "requests_emitted"])
        self.assertEqual(llm["summary"]["fake_call_count"], 7)
        self.assertEqual(llm["summary"]["scripted_token_totals"],
                         {"input_tokens": 62, "output_tokens": 17})
        self.assertEqual(llm["summary"]["usage_missing_call_count"], 1)
        self.assertIsNone(llm["summary"]["model_cost"])
        self.assertEqual(llm["client_kind"], "scripted_fake")

    def test_pending_fill_precedes_next_decision_and_records_observed_time(self):
        """A prior limit fills on a later quote before a sell sees holdings."""
        value = fixture()
        value["ticks"] = value["ticks"][:3]
        value["ticks"][0]["scripted_llm"]["decision"].update(price=95)
        llm = evaluation.evaluate(value)["arms"][1]
        self.assertEqual(llm["ticks"][0]["events"][0]["result"]["state"], "requested")
        events = llm["ticks"][2]["events"]
        self.assertEqual([e["result"]["type"] for e in events], ["buy", "sell"])
        self.assertEqual(events[0]["at"], value["ticks"][2]["at"])
        self.assertEqual(events[0]["result"]["date_time"], value["ticks"][0]["at"])
        self.assertEqual(llm["summary"]["final_account"]["equity"], 1000)

    def test_future_ticks_do_not_rewrite_prefix_decisions(self):
        """Changing unseen prices cannot change already-recorded prompt hashes."""
        value = fixture()
        original = evaluation.evaluate(value)
        value["ticks"][-1]["snapshot"][1]["closing_price"] = 999
        changed = evaluation.evaluate(value)
        for first, second in zip(semantics(original)["arms"], semantics(changed)["arms"]):
            self.assertEqual(first["ticks"][:-1], second["ticks"][:-1])
        self.assertNotEqual(original["fixture_sha256"], changed["fixture_sha256"])

    def test_baseline_is_unaffected_by_fake_script_changes(self):
        """Fake LLM content never contaminates the baseline account."""
        value = fixture()
        original = evaluation.evaluate(value)
        for tick in value["ticks"]:
            tick["scripted_llm"] = {"kind": "decision", "decision": {"action": "hold"}}
        changed = evaluation.evaluate(value)
        self.assertEqual(semantics(original)["arms"][0], semantics(changed)["arms"][0])
        self.assertEqual(changed["arms"][1]["summary"]["final_account"]["equity"], 1000)
        self.assertEqual(changed["arms"][1]["summary"]["usage_missing_call_count"], 7)

    def test_metadata_contains_source_hashes_and_measured_latency(self):
        """Hashes identify source bytes; timings are finite measured local values."""
        report = evaluation.evaluate(fixture())
        self.assertEqual(len(report["source_sha256"]), len(evaluation.SOURCE_MODULES) + 1)
        self.assertEqual(report["source_bundle_sha256"], evaluation.digest(report["source_sha256"]))
        for arm in report["arms"]:
            timing = arm["summary"]["local_decision_latency_ms"]
            self.assertEqual(timing["samples"], 7)
            self.assertGreaterEqual(timing["total"], 0)
            self.assertTrue(math.isfinite(timing["mean"]))
        self.assertIn("zero fees", " ".join(report["limitations"]))
        json.dumps(report, allow_nan=False)

    def test_terminal_cancellation_is_not_a_fill_or_liquidation(self):
        """End-policy releases open reservations but retains owned assets."""
        llm = evaluation.evaluate(fixture())["arms"][1]
        event = llm["finalization_events"][0]
        self.assertEqual(event["phase"], "finalize")
        self.assertEqual(event["result"]["msg"], "canceled")
        self.assertEqual(event["result"]["amount"], 0)
        self.assertEqual(llm["summary"]["filled_orders"], 2)
        self.assertEqual(llm["summary"]["final_account"]["asset_amount"], 1)


class FixtureValidationTests(unittest.TestCase):
    """Fail before loading strategies when fixtures cannot be compared fairly."""

    def test_bad_root_and_numeric_fields(self):
        """Schema, currency and ordinary configuration numbers are validated."""
        for bad in (None, [], {}, {"schema_version": True}):
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                evaluation.evaluate(bad)
        for field, bad in [("initial_cash", True), ("initial_cash", 0),
                           ("initial_cash", float("inf")), ("initial_cash", 10**400), ("min_order_value", -1),
                           ("currency", ""), ("data_kind", "live")]:
            value = fixture()
            value[field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                evaluation.evaluate(value)

    def test_invalid_timeline_and_snapshot_shapes(self):
        """No ambiguous ordering, duplicate candles or untimed price samples."""
        mutations = [
            lambda f: f.update(ticks=[]),
            lambda f: f["ticks"].reverse(),
            lambda f: f["ticks"].append(copy.deepcopy(f["ticks"][-1])),
            lambda f: f["ticks"][0].update(at="2026-01-01T00:00:00Z"),
            lambda f: f["ticks"][0].update(snapshot=[None]),
            lambda f: f["ticks"][0]["snapshot"].append(copy.deepcopy(f["ticks"][0]["snapshot"][1])),
            lambda f: f["ticks"][0]["snapshot"][1].update(market="ETH"),
            lambda f: f["ticks"][0]["snapshot"][1].update(date_time="2025-01-01T00:00:00"),
            lambda f: f["ticks"][0]["snapshot"][1].update(closing_price=False),
            lambda f: f["ticks"][0]["snapshot"][1].update(closing_price=1e-320),
        ]
        for mutate in mutations:
            value = fixture()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                evaluation.evaluate(value)
        value = fixture()
        for tick in value["ticks"]:
            tick["snapshot"] = []
        with self.assertRaises(ValueError):
            evaluation.evaluate(value)

    def test_invalid_scripts_and_usage_fail_explicitly(self):
        """No implicit script fallback or fabricated provider-error token data."""
        for bad in ({}, {"kind": "real_model"}, {"kind": "decision", "decision": []},
                    {"kind": "provider_error", "usage": {"input_tokens": 1}},
                    {"kind": "no_tool", "usage": {"input_tokens": True}},
                    {"kind": "no_tool", "usage": {"output_tokens": -1}},
                    {"kind": "no_tool", "usage": {"cost": 1}}):
            value = fixture()
            value["ticks"][0]["scripted_llm"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                evaluation.evaluate(value)

    def test_finite_but_invalid_decision_reaches_real_validator(self):
        """Decision rejections are outcomes, not removed fixture samples."""
        for decision in ({"action": "unknown"}, {"action": "buy", "price": True, "amount": 1},
                         {"action": "sell", "price": 100, "amount": 999}):
            value = fixture()
            value["ticks"][0]["scripted_llm"]["decision"] = decision
            llm = evaluation.evaluate(value)["arms"][1]
            self.assertEqual(llm["ticks"][0]["outcome"], "decision_rejected")


class IsolationAndCliTests(unittest.TestCase):
    """Offline execution cannot quietly grow real runtime dependencies."""

    def test_private_loader_rejects_config_and_cleans_up(self):
        """The source allowlist excludes package initializers and live modules."""
        before = set(sys.modules)
        with evaluation.load_components() as components:
            prefix = components["date_converter"].__name__.split(".")[0]
            for name in ("config", "trader.upbit_trader", "llm.openai_llm_client"):
                with self.assertRaises(ImportError):
                    importlib.import_module(prefix + "." + name)
            imported = set(sys.modules) - before
            self.assertNotIn("dotenv", imported)
            self.assertNotIn("smtm.config", imported)
        self.assertFalse(any(name.startswith(prefix) for name in sys.modules))

    def test_unexpected_absolute_import_fails_even_if_already_cached(self):
        """A future absolute config/SDK import cannot escape via sys.modules."""
        original = Path.read_bytes
        for dependency in ("smtm.config", "dotenv", "socket"):
            def changed(path):
                content = original(path)
                if path.name == "strategy_bnh.py":
                    content += ("\nimport " + dependency + "\n").encode()
                return content
            with self.subTest(dependency=dependency), patch.object(Path, "read_bytes", changed), \
                    patch.dict(sys.modules, {dependency: types.ModuleType(dependency)}):
                with self.assertRaisesRegex(ImportError, "Unapproved absolute"):
                    with evaluation.load_components():
                        pass

    def test_audit_guard_rejects_network_process_and_secret_paths(self):
        """Test the actual hook without leaving permanent hooks in the suite."""
        with patch.object(sys, "addaudithook") as install:
            evaluation.install_offline_guard()
        guard = install.call_args[0][0]
        for event, args in [("socket.connect", (None, ("localhost", 1))),
                            ("socket.getaddrinfo", ("example.invalid", 443)),
                            ("subprocess.Popen", ("echo",)),
                            ("open", ("/tmp/.env.probe", "r")),
                            ("open", ("/tmp/.ssh/probe", "r"))]:
            with self.subTest(event=event, args=args), self.assertRaises(RuntimeError):
                guard(event, args)
        guard("open", (str(FIXTURE), "r"))

    def test_cli_runs_without_site_packages_and_refuses_overwrite(self):
        """The documented command needs no installed package, account or SDK."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            command = [sys.executable, "-S", str(evaluation.ROOT / "tools/evaluate_offline.py"),
                       "--fixture", str(FIXTURE), "--output", str(output)]
            run = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["evaluation_kind"], "offline_scripted_plumbing")
            original = output.read_bytes()
            again = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_cli_reports_bad_fixture_without_creating_artifact(self):
        """Input failure is an explicit nonzero exit, never a partial success."""
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "bad.json"
            invalid.write_text('{"schema_version": 900}', encoding="utf-8")
            output = Path(directory) / "report.json"
            run = subprocess.run([sys.executable, "-S", str(evaluation.ROOT / "tools/evaluate_offline.py"),
                                  "--fixture", str(invalid), "--output", str(output)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
