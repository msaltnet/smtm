from ..tool import Tool, ToolResult

PROFILE_PROPERTIES = {
    "name": {"type": "string", "description": "프로파일 이름 (영문/숫자/-/_)"},
    "exchange": {"type": "string", "description": "거래소 코드 예: UPB"},
    "currency": {"type": "string", "description": "거래 통화 예: BTC"},
    "budget": {"type": "number", "description": "초기 예산"},
    "virtual": {"type": "boolean", "description": "가상매매 여부"},
    "term": {"type": "number", "description": "매매 주기(초)"},
    "strategy": {"type": "string", "description": "전략 코드 예: BNH/RSI/SMA/LLM"},
    "strategy_params": {"type": "object", "description": "전략 파라미터"},
    "safety": {"type": "object", "description": "안전장치 설정"},
    "account": {"type": "string", "description": "계좌 별칭 (실거래 세션에 필요, 가상매매는 불필요)"},
}


class ListProfilesTool(Tool):
    name = "list_profiles"
    description = "저장된 계좌 프로파일 목록을 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True,
                          data={"profiles": self.store.list_profiles()})


class DescribeProfileTool(Tool):
    name = "describe_profile"
    description = "특정 프로파일의 전체 내용을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class CreateProfileTool(Tool):
    name = "create_profile"
    description = "새 계좌 프로파일(실행 프리셋)을 생성하여 저장합니다"
    input_schema = {
        "type": "object",
        "properties": PROFILE_PROPERTIES,
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.save(dict(arguments))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class UpdateProfileTool(Tool):
    name = "update_profile"
    description = "기존 프로파일의 일부 필드를 수정합니다 (미지정 필드는 유지)"
    input_schema = {
        "type": "object",
        "properties": PROFILE_PROPERTIES,
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
            profile.update(arguments)
            profile = self.store.save(profile)
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class DeleteProfileTool(Tool):
    name = "delete_profile"
    description = "프로파일을 삭제합니다"
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        if self.store.delete(arguments.get("name")):
            return ToolResult(success=True, data={"deleted": arguments.get("name")})
        return ToolResult(success=False,
                          error=f"프로파일을 찾을 수 없습니다: {arguments.get('name')}")


class SwitchProfileTool(Tool):
    name = "switch_profile"
    description = ("프로파일을 로드하여 시스템 구성을 전환합니다. "
                   "매매 중이면 중지 후 적용되며, 재시작은 별도로 start_trading을 호출해야 합니다")
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store, operator):
        self.store = store
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        result = self.operator.apply_profile(profile)
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))
