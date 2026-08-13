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
    def _make(self, **kwargs):
        operator_tuple = make_operator(**kwargs)
        if not hasattr(self, "_operators"):
            self._operators = []
        self._operators.append(operator_tuple[0])
        return operator_tuple

    def tearDown(self):
        # 직접 틱 호출로 시작된 타이머 정리
        if hasattr(self, "_operators"):
            for operator in self._operators:
                if operator.timer is not None:
                    operator.timer.cancel()

    def test_tick_executes_full_pipeline_and_buys(self):
        operator, trader, strategy, monitor = self._make()
        operator.state = "running"
        operator._execute_trading(None)
        # BnH는 예산의 1/5 매수 → SimulationTrader 잔고 감소
        self.assertLess(trader.balance, 500000)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["state"], "done")
        self.assertEqual(strategy.balance, trader.balance)
        self.assertEqual(trader.order_history[0]["fee"], 0)
        # 기록 확인
        self.assertEqual(len(monitor.market_data_log), 1)
        self.assertEqual(len(monitor.trade_request_log), 1)
        self.assertEqual(len(monitor.trade_result_log), 1)

    def test_tick_injects_quote_into_simulation_trader(self):
        operator, trader, _, _ = self._make(closing_price=42000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(trader.quotes["BTC"], 42000)
        # 체결가는 주입된 시세를 따른다
        self.assertEqual(trader.order_history[0]["price"], 42000)

    def test_tick_is_noop_for_trader_without_update_quote(self):
        operator, _, _, _ = self._make()
        real_trader = MagicMock(spec=["send_request", "cancel_request",
                                      "cancel_all_requests", "get_account_info"])
        operator.trader = real_trader
        operator.state = "running"
        operator._execute_trading(None)  # AttributeError 없이 통과해야 함

    def test_safety_guard_blocks_oversized_request(self):
        # max_trade_amount=1000 → BnH의 10만원 매수 차단
        operator, trader, _, monitor = self._make(max_trade_amount=1000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)
        self.assertEqual(trader.balance, 500000)
        self.assertEqual(len(monitor.safety_event_log), 1)

    def test_empty_data_does_not_crash(self):
        operator, trader, _, _ = self._make()
        operator.data_provider = MagicMock(get_info=MagicMock(return_value=[]))
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)

    def test_failed_trade_is_logged_without_consuming_daily_quota(self):
        operator, trader, _, monitor = self._make()
        operator.state = "running"
        trader.update_quote("BTC", 50000)
        # 보유 수량 없이 매도 → SimulationTrader가 failed 결과 반환
        operator._send_requests([{
            "id": "t1", "type": "sell", "price": 50000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }])
        self.assertEqual(operator.safety_guard.daily_trade_count, 0)
        self.assertEqual(monitor.trade_result_log[-1]["result"]["state"], "failed")

    def test_limit_order_is_logged_only_after_quote_fills_it(self):
        operator, trader, _, monitor = self._make()
        operator._send_requests([{
            "id": "limit-buy", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }])

        self.assertIn("limit-buy", trader.pending_orders)
        self.assertIn("limit-buy", operator.strategy.waiting_requests)
        self.assertEqual(monitor.trade_result_log, [])

        operator._sync_trader_quote([{
            "type": "primary_candle", "market": "BTC", "closing_price": 39000,
        }])

        self.assertNotIn("limit-buy", trader.pending_orders)
        self.assertEqual(monitor.trade_result_log[-1]["result"]["state"], "done")
        self.assertEqual(operator.safety_guard.daily_trade_count, 1)

    def test_cancelled_limit_order_is_logged_without_consuming_daily_quota(self):
        operator, trader, _, monitor = self._make()
        operator._send_requests([{
            "id": "cancel-buy", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }])

        trader.cancel_request("cancel-buy")

        result = monitor.trade_result_log[-1]["result"]
        self.assertEqual(result["msg"], "canceled")
        self.assertEqual(operator.safety_guard.daily_trade_count, 0)

    def test_stop_loss_and_take_profit_fill_after_operator_quote_sync(self):
        for request_id, ord_type, trigger, closing_price in (
            ("stop-loss", "stop_loss", 45000, 44000),
            ("take-profit", "take_profit", 55000, 56000),
        ):
            with self.subTest(ord_type=ord_type):
                operator, trader, _, monitor = self._make()
                trader.assets["BTC"] = (50000, 1.0)
                trader.update_quote("BTC", 50000)

                operator._send_requests([{
                    "id": request_id, "type": "sell", "ord_type": ord_type,
                    "trigger": trigger, "price": 0, "amount": 1.0,
                    "date_time": "2026-07-03T12:00:00",
                }])
                operator._sync_trader_quote([{
                    "type": "primary_candle", "market": "BTC",
                    "closing_price": closing_price,
                }])

                result = monitor.trade_result_log[-1]["result"]
                self.assertEqual(result["state"], "done")
                self.assertEqual(result["msg"], "success")
                self.assertEqual(operator.safety_guard.daily_trade_count, 1)

    def test_tick_is_noop_when_not_running(self):
        operator, trader, _, _ = self._make()
        # state가 ready(정지 상태)이면 틱이 아무 것도 하지 않는다
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)

    def test_error_string_callback_does_not_crash(self):
        operator, _, strategy, _ = self._make()
        operator.state = "running"
        error_trader = MagicMock(spec=["send_request", "cancel_request",
                                       "cancel_all_requests", "get_account_info"])
        error_trader.send_request.side_effect = (
            lambda requests, callback: callback("error!"))
        operator.trader = error_trader
        # 가드가 없으면 AttributeError가 여기서 전파된다 (_send_requests는 try 밖)
        operator._send_requests([{
            "id": "t1", "type": "buy", "price": 50000, "amount": 0.5,
            "date_time": "2026-07-03T12:00:00",
        }])

    def test_malformed_terminal_amount_is_logged_without_consuming_daily_quota(self):
        operator, _, _, monitor = self._make()
        strategy = MagicMock()
        operator.strategy = strategy
        malformed_trader = MagicMock(
            spec=["send_request", "cancel_request", "cancel_all_requests",
                  "get_account_info"]
        )
        malformed_trader.send_request.side_effect = lambda requests, callback: callback({
            "request": requests[0], "type": "buy", "price": 50000,
            "amount": "not-a-number", "msg": "success", "state": "done",
        })
        operator.trader = malformed_trader

        operator._send_requests([{
            "id": "malformed-fill", "type": "buy", "price": 50000,
            "amount": 0.5, "date_time": "2026-07-03T12:00:00",
        }])

        self.assertEqual(monitor.trade_result_log[-1]["result"]["state"], "done")
        self.assertEqual(operator.safety_guard.daily_trade_count, 0)
        strategy.update_result.assert_called_once()

    def test_zero_amount_terminal_success_does_not_consume_daily_quota(self):
        operator, _, _, monitor = self._make()
        operator.strategy = MagicMock()
        zero_fill_trader = MagicMock(
            spec=["send_request", "cancel_request", "cancel_all_requests",
                  "get_account_info"]
        )
        zero_fill_trader.send_request.side_effect = lambda requests, callback: callback({
            "request": requests[0], "type": "buy", "price": 50000,
            "amount": 0, "msg": "success", "state": "done",
        })
        operator.trader = zero_fill_trader

        operator._send_requests([{
            "id": "zero-fill", "type": "buy", "price": 50000,
            "amount": 0.5, "date_time": "2026-07-03T12:00:00",
        }])

        self.assertEqual(monitor.trade_result_log[-1]["result"]["state"], "done")
        self.assertEqual(operator.safety_guard.daily_trade_count, 0)

    def test_invalid_terminal_amounts_are_logged_without_consuming_daily_quota(self):
        for amount in (True, float("nan"), float("inf"), float("-inf")):
            with self.subTest(amount=amount):
                operator, _, _, monitor = self._make()
                strategy = MagicMock()
                operator.strategy = strategy
                callback_result = {
                    "type": "buy", "price": 50000, "amount": amount,
                    "msg": "success", "state": "done",
                }
                callback_trader = MagicMock(
                    spec=["send_request", "cancel_request", "cancel_all_requests",
                          "get_account_info"]
                )

                def send_request(requests, callback):
                    callback_result["request"] = requests[0]
                    callback(callback_result)

                callback_trader.send_request.side_effect = send_request
                operator.trader = callback_trader
                operator._send_requests([{
                    "id": "invalid-fill", "type": "buy", "price": 50000,
                    "amount": 0.5, "date_time": "2026-07-03T12:00:00",
                }])

                strategy.update_result.assert_called_once_with(callback_result)
                self.assertEqual(monitor.trade_result_log[-1]["result"], callback_result)
                self.assertEqual(operator.safety_guard.daily_trade_count, 0)


class TradingOperatorLifecycleTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, "operator"):
            self.operator.stop()

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

    def test_stop_cancels_queued_orders_after_worker_start(self):
        self.operator, trader, _, _ = make_operator()
        self.operator._send_requests([{
            "id": "queued-buy", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }])
        self.assertIn("queued-buy", trader.pending_orders)

        self.assertTrue(self.operator.start())
        self.operator.stop()

        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
