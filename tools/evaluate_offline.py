"""Credential-free replay of real strategies with a scripted, non-model client.

Run from a checkout: python tools/evaluate_offline.py --fixture FILE --output FILE
This intentionally does not import smtm.__init__ or start runtime orchestration.
"""
import argparse
import builtins
import copy
import hashlib
import importlib.util
import json
import logging
import math
import platform
import sys
import time
import types
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODULES = (
    "cash_accounting", "date_converter", "strategy.strategy",
    "strategy.strategy_bnh", "strategy.strategy_llm", "trader.order_spec",
    "trader.trader", "trader.admission", "trader.simulation_admission",
    "trader.simulation_trader", "llm.llm_client",
)
STDLIB_IMPORTS = frozenset({
    "abc", "contextlib", "copy", "dataclasses", "datetime", "enum", "math",
    "os", "threading", "time", "typing",
})
LIMITATIONS = [
    "Scripted fake responses/tokens test plumbing, not actual LLM quality.",
    "Measured latency is local strategy/fake-client runtime, not provider latency.",
    "SimulationTrader uses zero fees, no slippage and six-decimal holdings.",
    "Current-close quote execution is idealized, not an executable backtest.",
    "Only the first primary candle is consumed by current strategies; other context is ignored.",
    "No runtime operator, session, SafetyGuard, chat loop or external integration is exercised.",
    "Missing-primary snapshots skip both arms; pending orders are canceled at end without liquidation.",
    "Scripted decisions may encode future knowledge; no model-performance inference is valid.",
]


def canonical_bytes(value):
    """Return stable strict JSON bytes for hashes and detached snapshots."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    """Hash a JSON-compatible value independently of input whitespace."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def install_offline_guard():
    """Block network/process attempts and common secret-file reads in this CLI.

    This Python audit guard is defense in depth, not an OS sandbox for untrusted
    code. Fixture data is JSON only and is never executed or used as import paths.
    """
    def guard(event, args):
        if event.startswith("socket.") and event != "socket.__new__":
            raise RuntimeError("Offline evaluation forbids networking")
        if event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}:
            raise RuntimeError("Offline evaluation forbids child processes")
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0])
            parts = path.resolve().parts
            if any(p.startswith(".env") or p in {".netrc", ".aws", ".ssh"}
                   for p in parts):
                raise RuntimeError("Offline evaluation forbids secret-file access")
    sys.addaudithook(guard)


@contextmanager
def load_components():
    """Load a fixed production subset in a private, disposable namespace.

    Package initializers and real logging setup are intentionally not executed.
    Imports of unlisted smtm modules are rejected, so a new dependency requires
    an explicit review of this list instead of silently loading configuration.
    """
    prefix = "_smtm_offline_" + str(time.perf_counter_ns())
    allowed = {prefix + "." + name for name in SOURCE_MODULES}
    class RejectUnexpected:
        """Fail closed for unexpected imports in the isolated namespace."""
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith(prefix + ".") and fullname not in allowed:
                raise ImportError("Unapproved offline dependency: " + fullname)
            return None
    def offline_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name.split(".")[0] not in STDLIB_IMPORTS:
            raise ImportError("Unapproved absolute offline dependency: " + name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    blocker = RejectUnexpected()
    sys.meta_path.insert(0, blocker)
    try:
        for suffix in ("", ".strategy", ".trader", ".llm"):
            name = prefix + suffix
            module = types.ModuleType(name)
            module.__path__ = []  # Dependencies are explicitly loaded in order.
            sys.modules[name] = module
        logger_module = types.ModuleType(prefix + ".log_manager")
        logger = logging.getLogger(prefix)
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        logger_module.LogManager = type("OfflineLogManager", (), {
            "get_logger": staticmethod(lambda name: logger)})
        sys.modules[logger_module.__name__] = logger_module
        loaded = {}
        for name in SOURCE_MODULES:
            path = ROOT / "smtm" / (name.replace(".", "/") + ".py")
            spec = importlib.util.spec_from_file_location(prefix + "." + name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            module.__dict__["__builtins__"] = dict(vars(builtins), __import__=offline_import)
            exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
            loaded[name] = module
        yield loaded
    finally:
        sys.meta_path.remove(blocker)
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        logging.Logger.manager.loggerDict.pop(prefix, None)


def _number(value, name, positive=False):
    """Validate bounded ordinary JSON numbers before portfolio arithmetic."""
    if type(value) not in (int, float) or value > 1e15 or value < 0 or \
            (positive and value < 1e-12) or not math.isfinite(value):
        raise ValueError(name + " must be finite and in [1e-12, 1e15] when positive")


def validate_fixture(fixture):
    """Validate version 1, strict chronology, one currency and explicit scripts."""
    canonical_bytes(fixture)  # Reject NaN/Infinity anywhere, including responses.
    if not isinstance(fixture, dict) or type(fixture.get("schema_version")) is not int or fixture.get("schema_version") != 1:
        raise ValueError("fixture schema_version must be 1")
    for field in ("scenario_id", "provenance", "currency"):
        if not isinstance(fixture.get(field), str) or not fixture[field].strip():
            raise ValueError(field + " must be a nonempty string")
    if fixture.get("data_kind") not in {"synthetic", "recorded"}:
        raise ValueError("data_kind must be synthetic or recorded")
    _number(fixture.get("initial_cash"), "initial_cash", positive=True)
    _number(fixture.get("min_order_value"), "min_order_value", positive=True)
    ticks = fixture.get("ticks")
    if not isinstance(ticks, list) or not ticks or len(ticks) > 10000:
        raise ValueError("ticks must contain 1..10000 entries")
    previous = None
    has_candle = False
    for tick in ticks:
        if not isinstance(tick, dict):
            raise ValueError("each tick must be an object")
        stamp = tick.get("at")
        try:
            parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError) as error:
            raise ValueError("tick at must be UTC YYYY-MM-DDTHH:MM:SS") from error
        if parsed.strftime("%Y-%m-%dT%H:%M:%S") != stamp or \
                (previous is not None and stamp <= previous):
            raise ValueError("ticks must be strictly chronological and unique")
        previous = stamp
        snapshot = tick.get("snapshot")
        if not isinstance(snapshot, list) or any(not isinstance(x, dict) or
                not isinstance(x.get("type"), str) for x in snapshot):
            raise ValueError("snapshot must be a list of typed objects")
        candles = [x for x in snapshot if x["type"] == "primary_candle"]
        if len(candles) > 1:
            raise ValueError("at most one primary candle is allowed per tick")
        if candles:
            has_candle = True
            candle = candles[0]
            if candle.get("date_time") != stamp or candle.get("market") != fixture["currency"]:
                raise ValueError("primary candle time/currency must match its tick")
            _number(candle.get("closing_price"), "closing_price", positive=True)
        script = tick.get("scripted_llm")
        if not isinstance(script, dict) or script.get("kind") not in {
                "decision", "no_tool", "provider_error"}:
            raise ValueError("each tick needs a scripted_llm kind")
        if script["kind"] == "decision" and not isinstance(script.get("decision"), dict):
            raise ValueError("scripted decision must be an object")
        usage = script.get("usage", {})
        if not isinstance(usage, dict) or set(usage) - {"input_tokens", "output_tokens"}:
            raise ValueError("usage accepts input_tokens/output_tokens only")
        if any(type(v) is not int or v < 0 for v in usage.values()):
            raise ValueError("scripted token counts must be nonnegative integers")
        if script["kind"] == "provider_error" and usage:
            raise ValueError("provider_error cannot report returned usage")
    if not has_candle:
        raise ValueError("at least one primary candle is required for valuation")


class ScriptedClient:
    """One explicit fake response per replay tick, never a real provider."""
    def __init__(self, response_type, tool_type):
        self.response_type, self.tool_type = response_type, tool_type
        self.script = None
        self.calls = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        """Record only a prompt hash and return the current synthetic script."""
        self.calls.append({"prompt_sha256": digest({"system": system_prompt,
                           "messages": messages, "tools": tools, "choice": tool_choice})})
        if self.script["kind"] == "provider_error":
            raise RuntimeError("synthetic provider failure")
        calls = []
        if self.script["kind"] == "decision":
            calls = [self.tool_type("scripted", "submit_decision",
                                    copy.deepcopy(self.script["decision"]))]
        return self.response_type("", tool_calls=calls,
                                  usage=copy.deepcopy(self.script.get("usage", {})))


def _account(trader, currency, quote):
    """Value total held assets, including reserved assets, at the last close."""
    amount = trader.get_account_info()["asset"].get(currency, (0, 0))[1]
    return {"cash": trader.balance, "asset_amount": amount,
            "equity": trader.balance + amount * (quote or 0), "mark_price": quote,
            "open_orders": len(trader.pending_orders)}


def _run_arm(fixture, components, name):
    """Replay quote -> pending fills -> current decision -> new fills per tick."""
    llm = components["llm.llm_client"]
    client = ScriptedClient(llm.LlmResponse, llm.ToolCall)
    usage_events = []
    strategy = (components["strategy.strategy_bnh"].StrategyBuyAndHold() if name == "BNH"
                else components["strategy.strategy_llm"].StrategyLlm(
                    llm_client=client, usage_observer=usage_events.append))
    strategy.initialize(fixture["initial_cash"], min_price=fixture["min_order_value"],
                        cash_accounting="fractional")
    strategy.is_simulation = True
    trader = components["trader.simulation_trader"].SimulationTrader(
        budget=fixture["initial_cash"], currency=fixture["currency"])
    events, rows = [], []
    current = {"at": None, "phase": "tick", "index": -1}
    sequence = iter(range(1000000))
    components["date_converter"].DateConverter.timestamp_id = staticmethod(
        lambda: name + "-" + str(next(sequence)))

    def on_result(result):
        """Attach execution time separately from the original order timestamp."""
        events.append({"tick_index": current["index"], "at": current["at"],
                       "phase": current["phase"], "result": copy.deepcopy(result)})
        strategy.update_result(copy.deepcopy(result))

    quote = None
    for index, tick in enumerate(fixture["ticks"]):
        current.update(at=tick["at"], index=index)
        snapshot = copy.deepcopy(tick["snapshot"])
        candle = next((x for x in snapshot if x["type"] == "primary_candle"), None)
        start_events, start_calls, start_usage = len(events), len(client.calls), len(usage_events)
        requests = None
        elapsed = None
        outcome = "missing_primary_candle"
        if candle:
            quote = candle["closing_price"]
            trader.update_quote(fixture["currency"], quote)
            strategy.update_trading_info(snapshot)
            client.script = copy.deepcopy(tick["scripted_llm"])
            start = time.perf_counter_ns()
            requests = strategy.get_request()
            elapsed = (time.perf_counter_ns() - start) / 1e6
            if requests:
                outcome = "requests_emitted"
                trader.send_request(copy.deepcopy(requests), on_result)
            elif name == "BNH":
                outcome = "no_request"
            elif client.script["kind"] == "provider_error":
                outcome = "provider_error"
            elif client.script["kind"] == "no_tool":
                outcome = "missing_decision_tool"
            elif client.script["decision"].get("action") == "hold":
                outcome = "hold"
            else:
                outcome = "decision_rejected"
        rows.append({"tick_index": index, "at": tick["at"],
                     "snapshot_sha256": digest(tick["snapshot"]), "outcome": outcome,
                     "requests": copy.deepcopy(requests or []),
                     "events": copy.deepcopy(events[start_events:]),
                     "account": _account(trader, fixture["currency"], quote),
                     "local_decision_latency_ms": elapsed,
                     "fake_calls": copy.deepcopy(client.calls[start_calls:]),
                     "scripted_usage": copy.deepcopy(usage_events[start_usage:])})
    current["phase"] = "finalize"
    start_events = len(events)
    trader.cancel_all_requests()
    account = _account(trader, fixture["currency"], quote)
    values = [fixture["initial_cash"]] + [row["account"]["equity"] for row in rows]
    peak, drawdown = values[0], 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = max(drawdown, (peak - value) / peak)
    latencies = [r["local_decision_latency_ms"] for r in rows
                 if r["local_decision_latency_ms"] is not None]
    counts = Counter(r["outcome"] for r in rows)
    results = [e["result"] for e in events]
    token_totals = {key: sum(u.get(key, 0) for u in usage_events)
                    for key in ("input_tokens", "output_tokens")}
    return {"strategy": name, "client_kind": "none" if name == "BNH" else "scripted_fake",
            "ticks": rows, "finalization_events": events[start_events:],
            "summary": {"final_account": account,
                        "return_fraction": account["equity"] / fixture["initial_cash"] - 1,
                        "max_sampled_drawdown_fraction": drawdown,
                        "outcome_counts": dict(counts),
                        "filled_orders": sum(r["state"] == "done" and r["msg"] == "success" for r in results),
                        "failed_orders": sum(r["state"] == "failed" for r in results),
                        "canceled_orders": sum(r["msg"] == "canceled" for r in results),
                        "fake_call_count": len(client.calls),
                        "scripted_token_totals": token_totals,
                        "usage_missing_call_count": len(client.calls) - len(usage_events) +
                            sum(not all(k in u for k in token_totals) for u in usage_events),
                        "model_cost": None, "model_cost_status": "not_applicable_fake_client",
                        "local_decision_latency_ms": {"samples": len(latencies),
                            "total": sum(latencies),
                            "mean": sum(latencies) / len(latencies) if latencies else None,
                            "max": max(latencies) if latencies else None}}}


def evaluate(fixture):
    """Return a JSON report with deterministic semantics and measured timings."""
    fixture = copy.deepcopy(fixture)
    validate_fixture(fixture)
    fixture = json.loads(canonical_bytes(fixture))  # Stable dict repr in real prompts.
    sources = ["smtm/" + n.replace(".", "/") + ".py" for n in SOURCE_MODULES]
    sources.append("tools/evaluate_offline.py")
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources}
    with load_components() as components:
        arms = [_run_arm(fixture, components, name) for name in ("BNH", "LLM")]
    report = {"schema_version": 1, "evaluation_kind": "offline_scripted_plumbing",
              "scenario_id": fixture["scenario_id"], "data_kind": fixture["data_kind"],
              "provenance": fixture["provenance"], "fixture_sha256": digest(fixture),
              "source_sha256": hashes, "source_bundle_sha256": digest(hashes),
              "runtime": {"python": platform.python_version(), "platform": sys.platform,
                          "created_at_utc": datetime.now(timezone.utc).isoformat()},
              "config": {"initial_cash": fixture["initial_cash"], "currency": fixture["currency"],
                         "min_order_value": fixture["min_order_value"], "cash_accounting": "fractional",
                         "fees": 0, "slippage": "not_modeled", "timestamp_timezone": "UTC",
                         "execution": "current_close", "end_policy": "cancel_pending_mark_to_market"},
              "limitations": LIMITATIONS[:], "arms": arms}
    canonical_bytes(report)  # Never emit nonstandard JSON or overflowed metrics.
    return report


def main(argv=None):
    """Run the guarded CLI; refuse to overwrite an existing report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    install_offline_guard()
    try:
        fixture_bytes = args.fixture.read_bytes()
        report = evaluate(json.loads(fixture_bytes))
        report["fixture_file_sha256"] = hashlib.sha256(fixture_bytes).hexdigest()
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(report, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
    except (ValueError, TypeError, OverflowError, OSError, RuntimeError, ImportError) as error:
        parser.exit(2, "Offline evaluation failed: " + str(error) + "\n")
    print("Offline scripted evaluation written to " + str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
