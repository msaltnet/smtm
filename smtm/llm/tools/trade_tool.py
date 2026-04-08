import time
import threading
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class TradeTool(Tool):
    """거래 실행 Tool — Trader 래핑"""

    name = "execute_trade"
    description = "거래소에 매수 또는 매도 주문을 실행합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell"], "description": "매수(buy) 또는 매도(sell)"},
            "currency": {"type": "string", "enum": ["BTC", "ETH", "DOGE", "XRP"], "description": "거래할 암호화폐"},
            "price": {"type": "number", "description": "주문 가격"},
            "amount": {"type": "number", "description": "주문 수량"},
        },
        "required": ["action", "currency", "price", "amount"],
    }

    def __init__(self, trader, system_monitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.trader = trader
        self.system_monitor = system_monitor

    def execute(self, arguments: dict) -> ToolResult:
        request = {
            "id": str(time.time()),
            "type": arguments["action"],
            "price": arguments["price"],
            "amount": arguments["amount"],
            "date_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.system_monitor.log_trade_request(request)

        result_holder = {}
        event = threading.Event()

        def callback(result):
            result_holder["result"] = result
            self.system_monitor.log_trade_result(result)
            event.set()

        try:
            self.trader.send_request([request], callback)
            event.wait(timeout=30)
            if "result" in result_holder:
                return ToolResult(success=True, data=result_holder["result"])
            return ToolResult(success=False, error="거래 요청 타임아웃")
        except Exception as e:
            self.logger.error(f"TradeTool error: {e}")
            return ToolResult(success=False, error=str(e))
