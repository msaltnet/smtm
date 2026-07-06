from ..tool import Tool, ToolResult


class ListStrategiesTool(Tool):
    name = "list_strategies"
    description = "사용 가능한 매매 전략 목록을 조회합니다 (코드/이름)"
    input_schema = {"type": "object", "properties": {}}

    def execute(self, arguments: dict) -> ToolResult:
        from ...strategy.strategy_factory import StrategyFactory
        strategies = [
            {"code": info["code"], "name": info["name"]}
            for info in StrategyFactory.get_all_strategy_info()
        ]
        return ToolResult(success=True, data={"strategies": strategies})


class DescribeStrategyTool(Tool):
    name = "describe_strategy"
    description = "특정 전략의 상세 설명을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "전략 코드"}},
        "required": ["code"],
    }

    def execute(self, arguments: dict) -> ToolResult:
        from ...strategy.strategy_factory import StrategyFactory
        for info in StrategyFactory.get_all_strategy_info():
            if info["code"] == arguments.get("code"):
                description = (info["class"].__doc__ or "").strip()
                return ToolResult(success=True, data={
                    "code": info["code"], "name": info["name"],
                    "description": description,
                })
        return ToolResult(success=False,
                          error=f"알 수 없는 전략 코드: {arguments.get('code')}")


class SelectStrategyTool(Tool):
    name = "select_strategy"
    description = ("매매 전략을 선택합니다. 매매 중에는 변경할 수 없으며 "
                   "먼저 stop_trading이 필요합니다")
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "전략 코드 (list_strategies로 조회)"}},
        "required": ["code"],
    }

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.select_strategy(arguments.get("code"))
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class StartTradingTool(Tool):
    name = "start_trading"
    description = "선택된 전략으로 고정 주기 자동 매매를 시작합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.start_trading()
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class StopTradingTool(Tool):
    name = "stop_trading"
    description = "자동 매매를 중지합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.stop_trading()
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class GetStatusTool(Tool):
    name = "get_status"
    description = ("시스템 상태를 조회합니다. 인자 없이 호출하면 전체 세션/계좌 요약,"
                   " session을 지정하면 해당 세션 상세를 반환합니다")
    input_schema = {
        "type": "object",
        "properties": {"session": {"type": "string",
                                   "description": "세션 이름 (선택)"}},
    }

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        status = self.operator.get_status(session=arguments.get("session"))
        if "error" in status:
            return ToolResult(success=False, error=status["error"])
        return ToolResult(success=True, data=status)
