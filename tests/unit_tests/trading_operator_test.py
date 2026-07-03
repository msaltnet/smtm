import unittest
from unittest.mock import MagicMock
from smtm import TradingOperator, Analyzer, StrategyBuyAndHold
from smtm.trader.simulation_trader import SimulationTrader
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig
from smtm.llm.system_monitor import SystemMonitor


class FakeDataProvider:
    def __init__(self, closing_price=50000):
        self.closing_price = closing_price

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-03T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": self.closing_price,
            "acc_price": 1000000000, "acc_volume": 200,
        }]


def make_operator(budget=500000, max_trade_amount=1000000, closing_price=50000):
    monitor = SystemMonitor()
    analyzer = Analyzer(monitor)
    trader = SimulationTrader(budget=budget, currency="BTC")
    strategy = StrategyBuyAndHold()
    guard = SafetyGuard(SafetyConfig(
        max_trade_amount=max_trade_amount, max_daily_trades=20,
        max_loss_ratio=-0.9, initial_budget=budget,
    ))
    operator = TradingOperator(interval=60, currency="BTC")
    operator.initialize(
        FakeDataProvider(closing_price), strategy, trader, analyzer, guard,
        budget=budget,
    )
    return operator, trader, strategy, monitor


class TradingOperatorInitTests(unittest.TestCase):
    def test_initialize_sets_state_ready_and_initializes_components(self):
        operator, _, strategy, _ = make_operator()
        self.assertEqual(operator.state, "ready")
        self.assertTrue(strategy.is_initialized)

    def test_initialize_twice_is_noop(self):
        operator, _, _, _ = make_operator()
        operator.initialize(None, None, None, None, None)  # 무시되어야 함
        self.assertEqual(operator.state, "ready")
        self.assertIsNotNone(operator.strategy)


class TradingOperatorTickTests(unittest.TestCase):
    def test_tick_executes_full_pipeline_and_buys(self):
        operator, trader, _, monitor = make_operator()
        operator.state = "running"
        operator._execute_trading(None)
        # BnH는 예산의 1/5 매수 → SimulationTrader 잔고 감소
        self.assertLess(trader.balance, 500000)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["state"], "done")
        # 기록 확인
        self.assertEqual(len(monitor.market_data_log), 1)
        self.assertEqual(len(monitor.trade_request_log), 1)
        self.assertEqual(len(monitor.trade_result_log), 1)

    def test_tick_injects_quote_into_simulation_trader(self):
        operator, trader, _, _ = make_operator(closing_price=42000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(trader.quotes["BTC"], 42000)
        # 체결가는 주입된 시세를 따른다
        self.assertEqual(trader.order_history[0]["price"], 42000)

    def test_tick_is_noop_for_trader_without_update_quote(self):
        operator, _, _, _ = make_operator()
        real_trader = MagicMock(spec=["send_request", "cancel_request",
                                      "cancel_all_requests", "get_account_info"])
        operator.trader = real_trader
        operator.state = "running"
        operator._execute_trading(None)  # AttributeError 없이 통과해야 함

    def test_safety_guard_blocks_oversized_request(self):
        # max_trade_amount=1000 → BnH의 10만원 매수 차단
        operator, trader, _, monitor = make_operator(max_trade_amount=1000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)
        self.assertEqual(trader.balance, 500000)
        self.assertEqual(len(monitor.safety_event_log), 1)

    def test_empty_data_does_not_crash(self):
        operator, trader, _, _ = make_operator()
        operator.data_provider = MagicMock(get_info=MagicMock(return_value=[]))
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)


class TradingOperatorLifecycleTests(unittest.TestCase):
    def test_start_stop_start_cycle(self):
        operator, _, _, _ = make_operator()
        self.assertTrue(operator.start())
        self.assertEqual(operator.state, "running")
        operator.stop()
        self.assertEqual(operator.state, "ready")
        self.assertTrue(operator.start())
        operator.stop()

    def test_start_when_not_ready_returns_false(self):
        operator, _, _, _ = make_operator()
        operator.start()
        self.assertFalse(operator.start())
        operator.stop()
