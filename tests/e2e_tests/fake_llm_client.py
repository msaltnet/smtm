"""
E2E 테스트용 Fake LLM Client

외부 LLM API를 대체하여 미리 정의된 시나리오대로 응답을 반환한다.
실제 LlmClient ABC를 상속하여 create_message 인터페이스를 구현하므로,
SystemOperator 입장에서는 실제 LLM과 동일하게 동작한다.
"""

import copy

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

    def create_message(self, system_prompt, messages, tools, tool_choice=None) -> LlmResponse:
        self.call_log.append(copy.deepcopy({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
        }))
        if not self.responses:
            return LlmResponse(
                text="(no more scripted responses)",
                tool_calls=[],
                stop_reason="end_turn",
                usage={"input_tokens": 0, "output_tokens": 0},
            )
        return self.responses.pop(0)

class FakeSnapshotDataProvider:
    """Replay complete typed snapshots; repeat the last, or [] for no snapshots.

    Each input element is one get_info() result, including an empty list.
    The timeline and every returned snapshot are deeply detached. This explicit
    API does not reinterpret FakeDataProvider's legacy candle-sequence input.
    """

    def __init__(self, snapshots):
        if (not isinstance(snapshots, list)
                or any(not isinstance(snapshot, list) for snapshot in snapshots)
                or any(not isinstance(item, dict)
                       for snapshot in snapshots for item in snapshot)):
            raise TypeError("snapshots must be a list of lists of typed dictionaries")
        self._snapshots = copy.deepcopy(snapshots)
        self.call_count = 0

    def get_info(self):
        """Return one detached snapshot and advance by exactly one call."""
        index = self.call_count
        self.call_count += 1
        if not self._snapshots:
            return []
        return copy.deepcopy(self._snapshots[min(index, len(self._snapshots) - 1)])


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
            "closing_price": 50000,
            "acc_price": 1000000000,
            "acc_volume": 200,
        }

