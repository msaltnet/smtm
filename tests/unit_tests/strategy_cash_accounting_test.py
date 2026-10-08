"""Cash-only contract: no strategy sizing, exchange calls, or real orders."""
import pytest

from smtm.strategy.strategy_bnh import StrategyBuyAndHold
from smtm.strategy.strategy_sma import StrategySma
from smtm.strategy.strategy_rsi import StrategyRsi
from smtm.strategy.strategy_llm import StrategyLlm

STRATEGIES = [StrategyBuyAndHold, StrategySma, StrategyRsi, StrategyLlm]
MISSING = object()


def fill(side="buy", total=10.25, fee=0, state="done"):
    result = dict(request={"id": "fill"}, type=side, price=total, amount=1,
                  state=state, msg="success", date_time="2026-10-08T00:00:00")
    if fee is not MISSING:
        result["fee"] = fee
    return result


@pytest.mark.parametrize("strategy_class", STRATEGIES)
@pytest.mark.parametrize("mode", [None, "legacy", "fractional"])
@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("total", [10.25, 10.5, 11.5, 0.25, 0])
@pytest.mark.parametrize("fee", [0, .01, MISSING])
def test_cash_delta_contract(strategy_class, mode, side, total, fee):
    strategy = strategy_class()
    kwargs = {} if mode is None else {"cash_accounting": mode}
    strategy.initialize(300.125, **kwargs)
    strategy.update_result(fill(side, total, fee))
    effective_fee = total * strategy.COMMISSION_RATIO if fee is MISSING else fee
    delta = total + effective_fee if side == "buy" else total - effective_fee
    delta = delta if mode == "fractional" else round(delta)
    expected = 300.125 - delta if side == "buy" else 300.125 + delta
    if mode == "fractional":
        assert strategy.balance == pytest.approx(expected, rel=0, abs=1e-12)
    else:
        assert strategy.balance == expected
    assert strategy.min_price == (100 if strategy_class is StrategyRsi else 5000)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
@pytest.mark.parametrize("mode", [None, True, False, 1, [], {}, "", "Fractional"])
def test_invalid_mode_does_not_initialize(strategy_class, mode):
    strategy = strategy_class()
    before = dict(strategy.__dict__)
    with pytest.raises(ValueError, match="cash_accounting"):
        strategy.initialize(300, cash_accounting=mode)
    assert strategy.__dict__ == before


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_fractional_zero_fee_and_reinitialize(strategy_class):
    strategy = strategy_class()
    strategy.initialize(300, cash_accounting="fractional")
    strategy.initialize(900, cash_accounting="legacy")
    strategy.update_result(fill(state="requested"))
    assert strategy.balance == 300
    strategy.update_result(fill())
    assert strategy.balance == 289.75
    strategy.update_result(fill("sell"))
    assert strategy.balance == pytest.approx(300, rel=0, abs=1e-12)
    strategy.update_result(fill(total=0))
    assert strategy.balance == pytest.approx(300, rel=0, abs=1e-12)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_fractional_missing_fee_round_trip(strategy_class):
    strategy = strategy_class()
    strategy.initialize(300, cash_accounting="fractional")
    strategy.update_result(fill(fee=MISSING))
    assert strategy.balance == pytest.approx(289.744875, rel=0, abs=1e-12)
    strategy.update_result(fill("sell", fee=MISSING))
    assert strategy.balance == pytest.approx(299.98975, rel=0, abs=1e-12)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_old_positional_arguments_and_legacy_reinitialize(strategy_class):
    strategy = strategy_class()
    strategy.initialize(300, 42, None, None, None)
    strategy.initialize(900, cash_accounting="fractional")
    strategy.update_result(fill())
    assert strategy.balance == 290
    assert strategy.min_price == 42
    assert strategy.cash_accounting == "legacy"


@pytest.mark.parametrize("strategy_class", STRATEGIES)
@pytest.mark.parametrize("fee", [None, "", "0", "0.01"])
def test_existing_fee_coercion_preserved(strategy_class, fee):
    strategy = strategy_class()
    strategy.initialize(300, cash_accounting="fractional")
    strategy.update_result(fill(fee=fee))
    assert strategy.balance == pytest.approx(289.75 - float(fee or 0), rel=0, abs=1e-12)
