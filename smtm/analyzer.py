from .log_manager import LogManager


class Analyzer:
    """SystemMonitor 위에서 Strategy 콜백 계약과 최소 성과 집계를 제공하는 경량 분석 계층"""

    def __init__(self, system_monitor, session_name=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor
        self.session_name = session_name
        self.get_account_info_func = None
        self.start_value = None
        self.spots = []
        self.lines = []

    def initialize(self, get_account_info_func):
        self.get_account_info_func = get_account_info_func

    def make_start_point(self):
        self.start_value = self.current_account_value()

    def put_trading_info(self, info):
        self.system_monitor.log_market_data(info, session=self.session_name)

    def put_requests(self, requests):
        for request in requests:
            self.system_monitor.log_trade_request(request, session=self.session_name)

    def put_result(self, result):
        self.system_monitor.log_trade_result(result, session=self.session_name)

    def put_safety_event(self, event):
        self.system_monitor.log_safety_event(event, session=self.session_name)

    def add_drawing_spot(self, date_time, value):
        self.spots.append({"date_time": date_time, "value": value})

    def add_value_for_line_graph(self, date_time, value):
        self.lines.append({"date_time": date_time, "value": value})

    def current_account_value(self) -> float:
        if self.get_account_info_func is None:
            return 0.0
        account = self.get_account_info_func()
        value = float(account.get("balance", 0))
        quotes = account.get("quote", {}) or {}
        for currency, (avg_price, amount) in (account.get("asset", {}) or {}).items():
            price = quotes.get(currency, avg_price)
            value += float(price) * float(amount)
        return value

    def get_return_report(self) -> dict:
        current_value = self.current_account_value()
        start_value = self.start_value
        if not start_value:
            return {"start_value": current_value, "current_value": current_value,
                    "cumulative_return": 0}
        cumulative_return = round((current_value - start_value) / start_value * 100, 3)
        return {"start_value": start_value, "current_value": current_value,
                "cumulative_return": cumulative_return}
