from ..tool import Tool, ToolResult


class CreateSessionTool(Tool):
    name = "create_session"
    description = ("저장된 프로파일로 새 트레이딩 세션을 생성합니다 (생성만 하며"
                   " 자동 시작하지 않음). 실거래 프로파일은 account가 필요합니다.")
    input_schema = {
        "type": "object",
        "properties": {
            "profile": {"type": "string", "description": "프로파일 이름"},
            "session": {"type": "string",
                        "description": "세션 이름 (생략 시 프로파일 이름 사용)"},
        },
        "required": ["profile"],
    }

    def __init__(self, profile_store, session_manager):
        self.profile_store = profile_store
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.profile_store.load(arguments.get("profile"))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        result = self.session_manager.create_session(
            profile, name=arguments.get("session"))
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class _SessionActionTool(Tool):
    """세션 이름 하나를 받아 SessionManager 메서드에 위임하는 공통 베이스"""
    input_schema = {
        "type": "object",
        "properties": {"session": {"type": "string", "description": "세션 이름"}},
        "required": ["session"],
    }

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def _run(self, method, arguments):
        result = method(arguments.get("session"))
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class StartSessionTool(_SessionActionTool):
    name = "start_session"
    description = "세션의 자동 매매를 시작합니다 (실거래 세션은 시작 전 사용자 확인 필수)"

    def execute(self, arguments: dict) -> ToolResult:
        return self._run(self.session_manager.start_session, arguments)


class StopSessionTool(_SessionActionTool):
    name = "stop_session"
    description = "세션의 자동 매매를 중지합니다"

    def execute(self, arguments: dict) -> ToolResult:
        return self._run(self.session_manager.stop_session, arguments)


class RemoveSessionTool(_SessionActionTool):
    name = "remove_session"
    description = "세션을 제거합니다 (매매 중이면 중지 후 제거, 계좌 할당 반환)"

    def execute(self, arguments: dict) -> ToolResult:
        return self._run(self.session_manager.remove_session, arguments)


class ListSessionsTool(Tool):
    name = "list_sessions"
    description = "전체 세션 목록을 조회합니다 (이름/상태/전략/계좌/심볼/예산/가상 여부)"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True,
                          data={"sessions": self.session_manager.list_sessions()})


class ComparePerformanceTool(Tool):
    name = "compare_performance"
    description = "모든 세션의 성과(누적 수익률)를 나란히 비교합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(
            success=True,
            data={"performance": self.session_manager.compare_performance()})
