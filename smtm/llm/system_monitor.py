from datetime import datetime
from typing import List
from ..log_manager import LogManager


class SystemMonitor:
    """독립 시스템 모니터 — LLM 바깥에서 모든 활동을 기록"""

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, storage_path: str = "output/monitor/"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.storage_path = storage_path
        self.market_data_log: List[dict] = []
        self.trade_request_log: List[dict] = []
        self.trade_result_log: List[dict] = []
        self.tool_call_log: List[dict] = []
        self.llm_interaction_log: List[dict] = []
        self.safety_event_log: List[dict] = []
        self.snapshots: List[dict] = []

    def _timestamp(self) -> str:
        return datetime.now().strftime(self.ISO_DATEFORMAT)

    def log_market_data(self, data: list):
        self.market_data_log.append({"timestamp": self._timestamp(), "data": data})

    def log_trade_request(self, request: dict):
        self.trade_request_log.append({"timestamp": self._timestamp(), "request": request})

    def log_trade_result(self, result: dict):
        self.trade_result_log.append({"timestamp": self._timestamp(), "result": result})

    def log_tool_call(self, tool_name: str, arguments: dict, result: dict):
        self.tool_call_log.append({
            "timestamp": self._timestamp(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
        })

    def log_llm_interaction(self, request: dict, response_text: str, usage: dict):
        self.llm_interaction_log.append({
            "timestamp": self._timestamp(),
            "request": request,
            "response_text": response_text,
            "usage": usage,
        })

    def log_safety_event(self, event: dict):
        self.safety_event_log.append({"timestamp": self._timestamp(), "event": event})

    def take_snapshot(self, portfolio: dict):
        self.snapshots.append({"timestamp": self._timestamp(), "portfolio": portfolio})

    def get_trade_log(self, start_time=None, end_time=None) -> list:
        return self.trade_result_log

    def get_snapshots(self, start_time=None, end_time=None) -> list:
        return self.snapshots

    def get_llm_usage(self) -> dict:
        total_input = sum(log["usage"].get("input_tokens", 0) for log in self.llm_interaction_log)
        total_output = sum(log["usage"].get("output_tokens", 0) for log in self.llm_interaction_log)
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "call_count": len(self.llm_interaction_log),
        }
