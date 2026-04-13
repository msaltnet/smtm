"""
E2E 테스트용 Fake LLM Client

외부 LLM API를 대체하여 미리 정의된 시나리오대로 응답을 반환한다.
실제 LlmClient ABC를 상속하여 create_message 인터페이스를 구현하므로,
LlmOperator 입장에서는 실제 LLM과 동일하게 동작한다.
"""

from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class FakeLlmClient(LlmClient):
    """미리 정의된 응답 시퀀스를 순서대로 반환하는 Fake LLM Client"""

    def __init__(self, responses: list = None):
        self.responses = list(responses) if responses else []
        self.call_log = []

    def add_response(self, response: LlmResponse):
        self.responses.append(response)

    def add_responses(self, responses: list):
        self.responses.extend(responses)

    def create_message(self, system_prompt, messages, tools) -> LlmResponse:
        self.call_log.append({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
        })
        if not self.responses:
            return LlmResponse(
                text="(no more scripted responses)",
                tool_calls=[],
                stop_reason="end_turn",
                usage={"input_tokens": 0, "output_tokens": 0},
            )
        return self.responses.pop(0)


class FakeTrader:
    """거래소 API를 대체하는 Fake Trader

    send_request, get_account_info 인터페이스를 구현하며,
    내부 상태(잔고, 보유 자산)를 실제로 변경한다.
    """

    def __init__(self, balance=500000):
        self.balance = balance
        self.assets = {}  # {"BTC": (avg_price, amount)}
        self.quotes = {}  # {"BTC": current_price}
        self.order_history = []

    def send_request(self, request_list, callback):
        for req in request_list:
            trade_amount = req["price"] * req["amount"]
            result = dict(req)

            if req["type"] == "buy":
                if trade_amount > self.balance:
                    result["state"] = "failed"
                    result["msg"] = "잔고 부족"
                else:
                    self.balance -= trade_amount
                    currency = "BTC"  # default
                    if currency in self.assets:
                        old_price, old_amount = self.assets[currency]
                        new_amount = old_amount + req["amount"]
                        new_price = (old_price * old_amount + req["price"] * req["amount"]) / new_amount
                        self.assets[currency] = (new_price, new_amount)
                    else:
                        self.assets[currency] = (req["price"], req["amount"])
                    result["state"] = "done"
                    result["msg"] = "success"

            elif req["type"] == "sell":
                currency = "BTC"
                if currency not in self.assets or self.assets[currency][1] < req["amount"]:
                    result["state"] = "failed"
                    result["msg"] = "보유 수량 부족"
                else:
                    self.balance += trade_amount
                    old_price, old_amount = self.assets[currency]
                    new_amount = old_amount - req["amount"]
                    if new_amount <= 0:
                        del self.assets[currency]
                    else:
                        self.assets[currency] = (old_price, new_amount)
                    result["state"] = "done"
                    result["msg"] = "success"

            result["balance"] = self.balance
            self.order_history.append(result)
            callback(result)

    def get_account_info(self):
        return {
            "balance": self.balance,
            "asset": dict(self.assets),
            "quote": dict(self.quotes),
        }


class FakeDataProvider:
    """시장 데이터를 대체하는 Fake DataProvider"""

    def __init__(self, candles=None):
        self.candles = candles or [self._default_candle()]
        self.call_count = 0

    def get_info(self):
        self.call_count += 1
        if isinstance(self.candles, list) and len(self.candles) > 1:
            idx = min(self.call_count - 1, len(self.candles) - 1)
            return [self.candles[idx]]
        return list(self.candles)

    def set_candles(self, candles):
        self.candles = candles

    @staticmethod
    def _default_candle():
        return {
            "type": "primary_candle",
            "market": "BTC",
            "date_time": "2026-04-13T12:00:00",
            "opening_price": 50000000,
            "high_price": 51000000,
            "low_price": 49000000,
            "closing_price": 50500000,
            "acc_price": 1000000000,
            "acc_volume": 200,
        }
