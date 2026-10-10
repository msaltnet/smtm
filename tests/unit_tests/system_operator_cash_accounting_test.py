"""Offline coverage of accounting selection through default-session orchestration."""
import copy
from unittest.mock import Mock, patch

import pytest

from smtm.llm.system_operator import SystemOperator
from smtm.profile_store import ProfileStore


INVALID_MODES = [None, True, False, 0, 1, [], {}, "", "Fractional", "unknown"]
INVALID_VIRTUAL = [None, False, 0, 1, "true", "false", [], {}]
STRATEGIES = ["BNH", "SMA", "RSI", "LLM"]


@pytest.fixture
def make_operator(tmp_path):
    with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
               return_value=Mock()) as provider, \
            patch("smtm.worker.Worker.start") as start_worker:
        def make(extra=None, setup=True):
            config = dict(exchange="OKX", currency="BTC", budget=300,
                          interval=60, virtual=True, strategy="BNH")
            config.update(extra or {})
            operator = SystemOperator(
                Mock(), config, profile_store=ProfileStore(str(tmp_path)),
                account_store=Mock())
            if setup:
                operator.setup()
            return operator

        yield make
        start_worker.assert_not_called()
        # All created providers are fakes; no tick or market-data request is run.
        provider.return_value.get_info.assert_not_called()


def get_strategy(operator):
    return operator.session_manager.get_session("default").operator.strategy


def buy_fill(strategy):
    strategy.update_result(dict(
        request={"id": "synthetic-buy"}, type="buy", price=10.25, amount=1,
        state="done", msg="success", fee=0, date_time="2026-10-09T00:00:00"))


@pytest.mark.parametrize("code", STRATEGIES)
@pytest.mark.parametrize("mode", [None, "legacy", "fractional"])
def test_setup_preserves_accounting_selection(make_operator, code, mode):
    extra = {"strategy": code}
    if mode is not None:
        extra["cash_accounting"] = mode
    operator = make_operator(extra)
    profile = operator.session_manager.get_session("default").profile
    strategy = get_strategy(operator)
    assert strategy.cash_accounting == (mode or "legacy")
    assert ("cash_accounting" in profile) == (mode is not None)
    buy_fill(strategy)
    assert strategy.balance == (289.75 if mode == "fractional" else 290)
    assert operator.account_store.mock_calls == operator.llm_client.mock_calls == []


@pytest.mark.parametrize("mode", INVALID_MODES)
def test_setup_rejects_invalid_mode_before_factories(make_operator, mode):
    operator = make_operator({"cash_accounting": mode}, setup=False)
    config_before = copy.deepcopy(operator.config)
    with patch("smtm.trader.trader_factory.TraderFactory.create") as trader, \
            patch("smtm.data.data_provider_factory.DataProviderFactory.create") as provider:
        with pytest.raises(ValueError, match="cash_accounting"):
            operator.setup()
    trader.assert_not_called()
    provider.assert_not_called()
    assert operator.account_store.mock_calls == []
    assert operator.session_manager.sessions == operator.session_manager.account_guards == {}
    assert operator.config == config_before


@pytest.mark.parametrize("virtual", INVALID_VIRTUAL)
def test_setup_fractional_requires_actual_virtual_boolean(make_operator, virtual):
    operator = make_operator({"cash_accounting": "fractional", "virtual": virtual},
                             setup=False)
    with patch("smtm.trader.trader_factory.TraderFactory.create") as trader:
        with pytest.raises(ValueError, match="cash_accounting"):
            operator.setup()
    trader.assert_not_called()
    assert operator.account_store.mock_calls == []
    assert operator.session_manager.sessions == {}


@pytest.mark.parametrize("code", STRATEGIES)
def test_saved_profile_switch_and_strategy_rebuild_preserve_fractional(make_operator, code):
    operator = make_operator()
    operator.profile_store.save(dict(name="fractional", strategy=code, budget=300,
                                    virtual=True, cash_accounting="fractional"))
    result = operator.tool_router.tools["switch_profile"].execute({"name": "fractional"})
    assert result.success
    assert operator.config["cash_accounting"] == "fractional"
    assert operator._config_to_profile()["cash_accounting"] == "fractional"
    strategy = get_strategy(operator)
    assert strategy.cash_accounting == "fractional"
    buy_fill(strategy)
    assert strategy.balance == 289.75
    assert operator.select_strategy("RSI" if code != "RSI" else "BNH")["success"]
    replacement = get_strategy(operator)
    assert replacement is not strategy
    assert replacement.cash_accounting == "fractional"
    # Existing replacement semantics start from the configured budget, not old cash.
    assert replacement.balance == 300
    assert operator.account_store.mock_calls == operator.llm_client.mock_calls == []


def test_partial_profile_inherits_mode_and_explicit_legacy_resets_it(make_operator):
    operator = make_operator({"cash_accounting": "fractional"})
    assert operator.apply_profile({"strategy": "RSI"})["success"]
    assert get_strategy(operator).cash_accounting == "fractional"
    assert operator.config["cash_accounting"] == "fractional"
    assert operator.apply_profile({"cash_accounting": "legacy"})["success"]
    assert get_strategy(operator).cash_accounting == "legacy"
    assert operator.config["cash_accounting"] == "legacy"
    assert operator.select_strategy("BNH")["success"]
    buy_fill(get_strategy(operator))
    assert get_strategy(operator).balance == 290


def assert_rejected_profile_preserves_session(operator, profile):
    old = operator.session_manager.get_session("default")
    buy_fill(old.operator.strategy)
    old.session_guard.daily_trade_count = 3
    config_before = copy.deepcopy(operator.config)
    profile_before = copy.deepcopy(old.profile)
    balance_before = old.operator.strategy.balance
    with patch("smtm.trader.trader_factory.TraderFactory.create") as trader, \
            patch("smtm.data.data_provider_factory.DataProviderFactory.create") as provider, \
            patch.object(operator.session_manager, "_discard_trader") as discard:
        result = operator.apply_profile(profile)
    assert result["success"] is False
    assert "cash_accounting" in result["error"]
    trader.assert_not_called()
    provider.assert_not_called()
    discard.assert_not_called()
    assert operator.account_store.mock_calls == []
    assert operator.config == config_before
    assert operator.session_manager.get_session("default") is old
    assert old.profile == profile_before
    assert old.operator.strategy.balance == balance_before
    assert old.session_guard.daily_trade_count == 3


@pytest.mark.parametrize("mode", INVALID_MODES)
def test_invalid_profile_overlay_preserves_existing_session(make_operator, mode):
    operator = make_operator({"cash_accounting": "fractional"})
    assert_rejected_profile_preserves_session(operator, {"cash_accounting": mode})


@pytest.mark.parametrize("virtual", INVALID_VIRTUAL)
def test_fractional_profile_overlay_requires_actual_virtual_boolean(make_operator, virtual):
    operator = make_operator()
    assert_rejected_profile_preserves_session(
        operator, {"cash_accounting": "fractional", "virtual": virtual})


def test_inherited_fractional_blocks_switch_to_live_before_account_access(make_operator):
    operator = make_operator({"cash_accounting": "fractional"})
    assert_rejected_profile_preserves_session(operator, {"virtual": False})


@pytest.mark.parametrize("profile", [
    {"cash_accounting": "fractional", "strategy": "NOPE"},
    {"cash_accounting": "fractional", "safety": {"unknown_limit": 1}},
])
def test_post_validation_failure_does_not_sync_accounting_config(make_operator, profile):
    operator = make_operator()
    old = operator.session_manager.get_session("default")
    before = copy.deepcopy(operator.config)
    assert operator.apply_profile(profile)["success"] is False
    assert operator.config == before
    assert operator.session_manager.get_session("default") is old
    assert old.operator.strategy.cash_accounting == "legacy"


def test_running_session_rejects_mode_switch_without_changing_config(make_operator):
    operator = make_operator()
    old = operator.session_manager.get_session("default")
    before = copy.deepcopy(operator.config)
    # Mark state only; no timer, thread, provider or LLM call is started.
    old.operator.state = "running"
    assert operator.apply_profile({"cash_accounting": "fractional"})["success"] is False
    assert operator.config == before
    assert operator.session_manager.get_session("default") is old
    assert old.operator.strategy.cash_accounting == "legacy"


def test_named_session_mode_is_independent_of_default_replacement(make_operator):
    operator = make_operator()
    manager = operator.session_manager
    assert manager.create_session(dict(name="named", exchange="OKX", virtual=True,
                                       budget=300, cash_accounting="legacy"))["success"]
    named = manager.get_session("named")
    assert operator.apply_profile({"cash_accounting": "fractional"})["success"]
    assert get_strategy(operator).cash_accounting == "fractional"
    assert manager.get_session("named") is named
    assert named.operator.strategy.cash_accounting == "legacy"
