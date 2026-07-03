import copy
import os
from datetime import datetime
from .strategy import Strategy
from ..log_manager import LogManager
from ..date_converter import DateConverter


class StrategyLlm(Strategy):
    """LLM에게 매 틱 단일 구조화 판단을 요청하는 전략.

    Tool 루프 없이 forced tool use로 submit_decision 스키마를 1회 강제한다.
    판단 실패/검증 실패 시 해당 틱은 안전하게 hold(None) 처리.
    llm_client는 덕 타이핑으로 주입된다 (create_message 프로토콜).
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    NAME = "LLM Single Decision"
    CODE = "LLM"
    CANDLE_WINDOW = 20
    RESULT_WINDOW = 10

    DECISION_TOOL = {
        "name": "submit_decision",
        "description": "시장 분석 결과에 따른 매매 판단을 제출합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["buy", "sell", "hold"],
                           "description": "매매 판단"},
                "price": {"type": ["number", "null"], "description": "주문 가격 (hold면 null)"},
                "amount": {"type": ["number", "null"], "description": "주문 수량 (hold면 null)"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1,
                               "description": "판단 확신도"},
                "reason": {"type": "string", "description": "판단 근거"},
            },
            "required": ["action", "reason"],
        },
    }

    def __init__(self, llm_client=None, strategy_files=None):
        self.llm_client = llm_client
        self.is_initialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0.0
        self.asset_amount = 0.0
        self.min_price = 0
        self.result = []
        self.waiting_requests = {}
        self.logger = LogManager.get_logger(__class__.__name__)
        self.strategy_knowledge = self._load_strategy_knowledge(strategy_files or [])

    def initialize(self, budget, min_price=5000, add_spot_callback=None,
                   add_line_callback=None, alert_callback=None):
        if self.is_initialized:
            return
        self.is_initialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price

    def update_trading_info(self, info):
        if self.is_initialized is not True or info is None:
            return
        for item in info:
            if item.get("type") == "primary_candle":
                self.data.append(copy.deepcopy(item))
                break
        if len(self.data) > self.CANDLE_WINDOW:
            self.data = self.data[-self.CANDLE_WINDOW:]

    def update_result(self, result):
        if self.is_initialized is not True:
            return
        try:
            request = result["request"]
            if result["state"] == "requested":
                self.waiting_requests[request["id"]] = result
                return
            if result["state"] == "done" and request["id"] in self.waiting_requests:
                del self.waiting_requests[request["id"]]

            price = float(result["price"])
            amount = float(result["amount"])
            total = price * amount
            fee = total * self.COMMISSION_RATIO
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            if result["msg"] == "success":
                if result["type"] == "buy":
                    self.asset_amount = round(self.asset_amount + amount, 6)
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)

            self.result.append(copy.deepcopy(result))
            if len(self.result) > self.RESULT_WINDOW:
                self.result = self.result[-self.RESULT_WINDOW:]
        except (AttributeError, TypeError, KeyError) as msg:
            self.logger.error(msg)

    def get_request(self):
        if self.is_initialized is not True or not self.data or self.llm_client is None:
            return None

        decision = self._request_decision()
        if decision is None or decision.get("action") == "hold":
            return None

        request = self._decision_to_request(decision)
        if request is None:
            return None

        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        if self.is_simulation:
            now = self.data[-1]["date_time"]
        request["date_time"] = now

        final_requests = []
        for request_id in self.waiting_requests:
            final_requests.append({
                "id": request_id, "type": "cancel",
                "price": 0, "amount": 0, "date_time": now,
            })
        final_requests.append(request)
        return final_requests

    def _request_decision(self):
        """LLM에 단일 구조화 판단 요청. 실패 시 None(hold)"""
        try:
            response = self.llm_client.create_message(
                self._build_system_prompt(),
                [{"role": "user", "content": self._build_prompt()}],
                [self.DECISION_TOOL],
                tool_choice={"type": "tool", "name": "submit_decision"},
            )
        except Exception as err:
            self.logger.warning(f"LLM decision request failed, fallback to hold: {err}")
            return None

        if not response.tool_calls:
            self.logger.warning("LLM returned no decision tool call, fallback to hold")
            return None

        decision = response.tool_calls[0].arguments
        if decision.get("action") not in ("buy", "sell", "hold"):
            self.logger.warning(f"invalid decision action: {decision}, fallback to hold")
            return None
        self.logger.info(
            f"[LLM DECISION] {decision.get('action')} "
            f"(confidence: {decision.get('confidence')}) - {decision.get('reason')}"
        )
        return decision

    def _decision_to_request(self, decision):
        """판단을 거래 요청으로 변환 + 검증. 실패 시 None(hold)"""
        try:
            price = float(decision.get("price") or 0)
            amount = float(decision.get("amount") or 0)
        except (TypeError, ValueError):
            self.logger.warning(f"invalid price/amount: {decision}")
            return None

        if price <= 0 or amount <= 0:
            self.logger.warning(f"non-positive price/amount: {decision}")
            return None

        total_value = price * amount
        if decision["action"] == "buy":
            if total_value > self.balance or total_value < self.min_price:
                self.logger.warning(
                    f"buy validation failed: total {total_value}, balance {self.balance}")
                return None
        elif decision["action"] == "sell":
            if amount > self.asset_amount:
                self.logger.warning(
                    f"sell validation failed: amount {amount} > asset {self.asset_amount}")
                return None

        return {
            "id": DateConverter.timestamp_id(),
            "type": decision["action"],
            "price": price,
            "amount": amount,
        }

    def _build_system_prompt(self):
        parts = [
            "당신은 암호화폐 매매 판단 전략입니다.",
            "제공된 시장 데이터를 분석하여 submit_decision Tool로 판단을 제출하세요.",
            "리스크 관리를 최우선으로 고려하고, 확신이 없으면 hold를 선택하세요.",
        ]
        if self.strategy_knowledge:
            parts.append("")
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
        return "\n".join(parts)

    def _build_prompt(self):
        parts = ["[매매 판단 요청]"]
        parts.append(f"최근 캔들 데이터 (최신순 {len(self.data)}개):")
        for candle in self.data[-self.CANDLE_WINDOW:]:
            parts.append(str(candle))
        parts.append("")
        parts.append(f"현재 잔고: {self.balance:,.0f}")
        parts.append(f"보유 수량: {self.asset_amount}")
        if self.result:
            parts.append(f"최근 거래 결과: {self.result[-3:]}")
        parts.append("")
        parts.append("시장 상황을 분석하고 buy/sell/hold 판단을 제출하세요.")
        return "\n".join(parts)

    def _load_strategy_knowledge(self, strategy_files):
        parts = []
        base_dir = os.path.join(os.path.dirname(__file__), "..", "strategies")
        for filename in strategy_files:
            filepath = os.path.join(base_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            except FileNotFoundError:
                self.logger.warning(f"Strategy file not found: {filepath}")
        return "\n\n---\n\n".join(parts)
