import threading
from .log_manager import LogManager
from .worker import Worker


class TradingOperator:
    """고정 주기로 DataProvider → Strategy → SafetyGuard → Trader → Analyzer
    파이프라인을 수행하는 트레이딩 오퍼레이터"""

    def __init__(self, interval=60, currency="BTC"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.interval = float(interval)
        self.currency = currency
        self.data_provider = None
        self.strategy = None
        self.trader = None
        self.analyzer = None
        self.safety_guard = None
        self.state = None
        self.timer = None
        self.is_timer_running = False
        self.worker = Worker("TradingOperator-Worker")

    def initialize(self, data_provider, strategy, trader, analyzer, safety_guard,
                   budget=500000):
        if self.state is not None:
            return
        self.data_provider = data_provider
        self.strategy = strategy
        self.trader = trader
        self.analyzer = analyzer
        self.safety_guard = safety_guard
        strategy.initialize(
            budget,
            add_spot_callback=analyzer.add_drawing_spot,
            add_line_callback=analyzer.add_value_for_line_graph,
            alert_callback=lambda msg: self.logger.warning(f"strategy alert: {msg}"),
        )
        analyzer.initialize(trader.get_account_info)
        self.state = "ready"

    def start(self) -> bool:
        if self.state != "ready" or self.is_timer_running:
            return False
        self.logger.info("===== TradingOperator Start =====")
        self.state = "running"
        self.analyzer.make_start_point()
        self.worker.start()
        self.worker.post_task({"runnable": self._execute_trading})
        return True

    def stop(self):
        if self.state != "running":
            return
        if self.timer is not None:
            self.timer.cancel()
        self.is_timer_running = False
        self.trader.cancel_all_requests()
        self.logger.info("===== TradingOperator Stop =====")
        self.state = "ready"
        self.worker.stop()

    def get_score(self) -> dict:
        return self.analyzer.get_return_report()

    def _execute_trading(self, task):
        del task
        self.is_timer_running = False
        if self.state != "running":
            return
        try:
            info = self.data_provider.get_info()
            self._sync_trader_quote(info)
            self.strategy.update_trading_info(info)
            self.analyzer.put_trading_info(info)

            requests = self.strategy.get_request()
            if requests:
                self._send_requests(requests)

            self.safety_guard.update_portfolio_value(
                self.analyzer.current_account_value()
            )
        except Exception as err:
            self.logger.error(f"trading tick error: {err}")
        self._start_timer()

    def _send_requests(self, requests):
        allowed = []
        for request in requests:
            verdict = self.safety_guard.check_request(request)
            if verdict.allowed:
                allowed.append(request)
            else:
                self.analyzer.put_safety_event({
                    "type": "blocked", "request": request, "reason": verdict.reason,
                })
        if not allowed:
            return

        def callback(result):
            self.strategy.update_result(result)
            if result.get("state") == "requested":
                return
            self.analyzer.put_result(result)
            if result.get("state") == "done" and result.get("type") in ("buy", "sell"):
                self.safety_guard.record_trade(result)

        self.trader.send_request(allowed, callback)
        self.analyzer.put_requests(allowed)

    def _sync_trader_quote(self, market_data):
        """가상매매 트레이더에 최신 종가 주입 (덕 타이핑 — 실거래 트레이더는 no-op)"""
        if not hasattr(self.trader, "update_quote") or not market_data:
            return
        for item in market_data:
            if isinstance(item, dict) and item.get("type") == "primary_candle":
                currency = item.get("market", self.currency)
                price = item.get("closing_price")
                if currency and price is not None:
                    self.trader.update_quote(currency, price)
                return

    def _start_timer(self):
        if self.is_timer_running or self.state != "running":
            return

        def on_timer_expired():
            self.worker.post_task({"runnable": self._execute_trading})

        self.timer = threading.Timer(self.interval, on_timer_expired)
        self.timer.daemon = True
        self.timer.start()
        self.is_timer_running = True
