"""BNH sizing for the explicitly enabled public-rule PAPER path."""
from datetime import datetime
from .strategy_bnh import StrategyBuyAndHold
from ..date_converter import DateConverter
from ..trader.paper_rules import PaperRulesError


class StrategyPaperBuyAndHold(StrategyBuyAndHold):
    def __init__(self, trader):
        super().__init__()
        self.paper_trader = trader
        self.blocked_reason = None

    def get_request(self):
        if not self.is_initialized or not self.data:
            return None
        try:
            rules = self.paper_trader.rules_reader.require_fresh()
            price, amount = rules.size_buy(self.data[-1]["closing_price"],
                                           min(self.budget / 5, self.balance))
            self.blocked_reason = None
            now = datetime.now().strftime(self.ISO_DATEFORMAT)
            requests = [{"id": key, "type": "cancel", "price": 0, "amount": 0,
                         "date_time": now} for key in self.waiting_requests]
            requests.append({"id": DateConverter.timestamp_id(), "type": "buy",
                             "price": price, "amount": amount, "date_time": now})
            return requests
        except (PaperRulesError, ValueError, KeyError, TypeError) as error:
            self.blocked_reason = "PAPER rules blocked: " + str(error)
            self.logger.warning(self.blocked_reason)
            return None

    def update_result(self, result):
        if result.get("state") == "failed":
            self.waiting_requests.pop(result.get("request", {}).get("id"), None)
        super().update_result(result)
