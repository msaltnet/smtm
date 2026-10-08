"""Opt-in validation and offline profile -> session -> operator -> fill chain."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from smtm.profile_store import ProfileStore
from smtm.session_manager import SessionManager, TradingSession
from smtm.trading_operator import TradingOperator
from smtm.trader.simulation_trader import SimulationTrader
from smtm.strategy.strategy_factory import StrategyFactory
from smtm.llm.tools.profile_tools import PROFILE_PROPERTIES, UpdateProfileTool

INVALID = [None, True, False, 0, 1, [], {}, "", "Fractional", "unknown"]
PROFILE = dict(name="fractional", exchange="OKX", currency="BTC", budget=300,
               strategy="BNH", virtual=True, cash_accounting="fractional")


@pytest.mark.parametrize("mode", INVALID)
def test_invalid_profile_save_load_and_session_before_external_work(tmp_path, mode):
    profile = dict(PROFILE, cash_accounting=mode, account="must-not-load")
    store = ProfileStore(str(tmp_path))
    with pytest.raises(ValueError, match="cash_accounting"):
        store.save(profile)
    (tmp_path / "fractional.json").write_text(json.dumps(profile))
    with pytest.raises(ValueError, match="cash_accounting"):
        store.load("fractional")
    assert_session_rejected_before_external_work(profile)


def assert_session_rejected_before_external_work(profile):
    accounts = Mock()
    manager = SessionManager(account_store=accounts, system_monitor=Mock())
    with patch("smtm.trader.trader_factory.TraderFactory.create") as trader, \
            patch("smtm.data.data_provider_factory.DataProviderFactory.create") as provider, \
            patch("smtm.worker.Worker.start") as worker:
        result = manager.create_session(profile)
    assert result["success"] is False
    assert "cash_accounting" in result["error"]
    assert accounts.mock_calls == []
    trader.assert_not_called()
    provider.assert_not_called()
    worker.assert_not_called()
    assert manager.sessions == manager.account_guards == {}


@pytest.mark.parametrize("virtual", [None, False, 0, 1, "true", "false", [], {}])
def test_fractional_requires_explicit_boolean_virtual(tmp_path, virtual):
    profile = dict(PROFILE, virtual=virtual)
    store = ProfileStore(str(tmp_path))
    with pytest.raises(ValueError, match="virtual"):
        store.save(profile)
    assert_session_rejected_before_external_work(profile)


def test_fractional_missing_virtual_rejected():
    profile = dict(PROFILE)
    del profile["virtual"]
    assert_session_rejected_before_external_work(profile)


@pytest.mark.parametrize("mode", [None, "legacy", "fractional"])
def test_profile_round_trip_preserves_omission(tmp_path, mode):
    profile = dict(PROFILE)
    if mode is None:
        del profile["cash_accounting"]
    else:
        profile["cash_accounting"] = mode
    store = ProfileStore(str(tmp_path))
    assert store.save(profile) == profile
    assert store.load("fractional") == profile
    assert PROFILE_PROPERTIES["cash_accounting"]["enum"] == ["legacy", "fractional"]


class OldSignatureStrategy:
    def initialize(self, budget, add_spot_callback=None, add_line_callback=None,
                   alert_callback=None):
        self.budget = budget


@pytest.mark.parametrize("mode", [None, "legacy"])
def test_operator_preserves_old_custom_strategy_signature(mode):
    operator = TradingOperator()
    strategy = OldSignatureStrategy()
    kwargs = {} if mode is None else {"cash_accounting": mode}
    operator.initialize(Mock(), strategy, Mock(), Mock(), Mock(), budget=300, **kwargs)
    assert operator.state == "ready"
    assert strategy.budget == 300


@pytest.mark.parametrize("mode", INVALID)
def test_operator_invalid_mode_does_not_assign_components(mode):
    operator = TradingOperator()
    before = dict(operator.__dict__)
    strategy, trader = Mock(), Mock()
    with pytest.raises(ValueError, match="cash_accounting"):
        operator.initialize(Mock(), strategy, trader, Mock(), Mock(), cash_accounting=mode)
    assert operator.__dict__ == before
    assert strategy.mock_calls == trader.mock_calls == []


def test_operator_non_simulation_rejected_before_account_access():
    operator = TradingOperator()
    before = dict(operator.__dict__)
    trader = Mock()
    with pytest.raises(ValueError, match="SimulationTrader"):
        operator.initialize(Mock(), Mock(), trader, Mock(), Mock(), cash_accounting="fractional")
    assert operator.__dict__ == before
    assert trader.mock_calls == []


def test_fractional_custom_strategy_cannot_silently_downgrade():
    operator = TradingOperator()
    analyzer = Mock()
    with pytest.raises(TypeError, match="cash_accounting"):
        operator.initialize(Mock(), OldSignatureStrategy(), SimulationTrader(), analyzer,
                            Mock(), cash_accounting="fractional")
    assert operator.state is None
    analyzer.initialize.assert_not_called()


@pytest.mark.parametrize("code", ["BNH", "SMA", "RSI", "LLM"])
def test_profile_runtime_chain_and_zero_fee_parity(code, tmp_path):
    accounts = Mock()
    manager = SessionManager(account_store=accounts, system_monitor=Mock())
    profile = dict(PROFILE, strategy=code,
                   strategy_params={"min_price": 1, "cash_accounting": "legacy"})
    with patch("smtm.data.data_provider_factory.DataProviderFactory.create", return_value=Mock()):
        assert manager.create_session(profile)["success"]
    session = manager.get_session("fractional")
    strategy = session.operator.strategy
    assert strategy.cash_accounting == "fractional"
    assert strategy.min_price == (100 if code == "RSI" else 5000)
    assert accounts.mock_calls == []
    # A recorded test request exercises the callback path without strategy sizing,
    # timers, live providers, or changing production minimum/safety defaults.
    session.operator.safety_guard = Mock()
    session.operator.safety_guard.check_request.return_value = SimpleNamespace(allowed=True)
    session.trader.update_quote("BTC", 10.25)
    request = dict(id="test-buy", type="buy", price=10.25, amount=1,
                   date_time="2026-10-08T00:00:00")
    session.operator._send_requests([request])
    assert strategy.balance == session.trader.balance == 289.75
    assert strategy.result[-1]["fee"] == 0
    session.operator._send_requests([dict(request, id="test-sell", type="sell")])
    assert strategy.balance == pytest.approx(300, rel=0, abs=1e-12)
    assert strategy.balance == pytest.approx(session.trader.balance, rel=0, abs=1e-12)
    assert session.operator.worker.thread is None
    # Persisting a mode edit does not mutate the assembled instance or migrate cash.
    store = ProfileStore(str(tmp_path))
    store.save(profile)
    assert UpdateProfileTool(store).execute(dict(name="fractional", cash_accounting="legacy")).success
    assert strategy.cash_accounting == "fractional"


def test_default_session_operator_call_shape_and_inert_strategy_params():
    manager = SessionManager()
    profile = dict(PROFILE, cash_accounting="legacy", strategy_params={"cash_accounting": "fractional"})
    with patch("smtm.data.data_provider_factory.DataProviderFactory.create", return_value=Mock()), \
            patch("smtm.trading_operator.TradingOperator.initialize") as initialize:
        assert manager.create_session(profile)["success"]
    assert initialize.call_args.kwargs == {"budget": 300.0}


def test_invalid_replacement_restores_old_session_and_allocation():
    manager = SessionManager(account_store=Mock())
    old = TradingSession("existing", dict(budget=300), Mock(state="ready"), Mock(),
                         Mock(), "existing-account", "2026-10-08")
    manager.sessions[old.name] = old
    guard = manager.get_account_guard(old.account)
    guard.allocate(old.name, 300)
    with patch("smtm.trader.trader_factory.TraderFactory.create") as factory:
        result = manager.replace_session(old.name, dict(PROFILE, virtual=False))
    assert result["success"] is False
    assert manager.sessions[old.name] is old
    assert guard.total_allocated() == 300
    factory.assert_not_called()
    old.trader.assert_not_called()
    assert old.trader.mock_calls == []


@pytest.mark.parametrize("code", ["BNH", "SMA", "RSI", "LLM"])
@pytest.mark.parametrize("existing, requested", [("legacy", "fractional"), ("fractional", "legacy")])
@pytest.mark.parametrize("simulation", [True, False])
def test_operator_rejects_preinitialized_mode_mismatch(code, existing, requested, simulation):
    strategy = StrategyFactory.create(code)
    strategy.initialize(300, cash_accounting=existing)
    trader = SimulationTrader(budget=300) if simulation else Mock()
    operator = TradingOperator()
    before = dict(operator.__dict__)
    with pytest.raises(ValueError, match="cash_accounting"):
        operator.initialize(Mock(), strategy, trader, Mock(), Mock(),
                            budget=900, cash_accounting=requested)
    assert operator.__dict__ == before
    assert strategy.balance == 300
    assert strategy.cash_accounting == existing
    if not simulation:
        assert trader.mock_calls == []


@pytest.mark.parametrize("code", ["BNH", "SMA", "RSI", "LLM"])
@pytest.mark.parametrize("mode", ["legacy", "fractional"])
def test_operator_accepts_matching_preinitialized_strategy_without_reset(code, mode):
    strategy = StrategyFactory.create(code)
    strategy.initialize(300, cash_accounting=mode)
    operator = TradingOperator()
    operator.initialize(Mock(), strategy, SimulationTrader(budget=300), Mock(), Mock(),
                        budget=900, cash_accounting=mode)
    assert operator.state == "ready"
    assert strategy.balance == 300
    assert strategy.cash_accounting == mode


@pytest.mark.parametrize("requested", ["legacy", "fractional"])
def test_initialized_custom_strategy_without_stored_mode(requested):
    """Old custom strategies cannot silently ignore an explicit fractional opt-in."""
    from smtm.strategy.strategy_bnh import StrategyBuyAndHold

    class InitializedCustomStrategy(StrategyBuyAndHold):
        def initialize(self, budget, **kwargs):
            if self.is_initialized:
                return
            self.balance = budget
            self.is_initialized = True

    strategy = InitializedCustomStrategy()
    strategy.initialize(300)
    assert not hasattr(strategy, "cash_accounting")
    operator = TradingOperator()
    before = dict(operator.__dict__)
    args = (Mock(), strategy, SimulationTrader(budget=300), Mock(), Mock())
    if requested == "fractional":
        with pytest.raises(ValueError, match="cash_accounting"):
            operator.initialize(*args, budget=900, cash_accounting=requested)
        assert operator.__dict__ == before
    else:
        operator.initialize(*args, budget=900, cash_accounting=requested)
        assert operator.state == "ready"
    assert strategy.balance == 300
    if requested == "legacy":
        strategy.update_result(dict(
            request={"id": "legacy-custom-fill"}, type="buy", price=10.25,
            amount=1, state="done", msg="success", fee=0,
            date_time="2026-10-08T00:00:00"))
        assert strategy.balance == 290
        assert len(strategy.result) == 1
