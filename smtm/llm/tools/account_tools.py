from ..tool import Tool, ToolResult

ACCOUNT_PROPERTIES = {
    "name": {"type": "string", "description": "계좌 별칭 (영문/숫자/-/_)"},
    "exchange": {"type": "string", "description": "거래소 코드 예: UPB"},
    "access_key_env": {"type": "string",
                       "description": "액세스 키가 담긴 환경변수 이름 (키 값 아님)"},
    "secret_key_env": {"type": "string",
                       "description": "시크릿 키가 담긴 환경변수 이름 (키 값 아님)"},
}


class RegisterAccountTool(Tool):
    name = "register_account"
    description = ("계좌를 등록합니다. API 키 '값'이 아니라 키가 저장된 환경변수의"
                   " '이름'을 등록합니다. 키 값을 대화로 받지 마세요.")
    input_schema = {
        "type": "object",
        "properties": ACCOUNT_PROPERTIES,
        "required": ["name", "exchange", "access_key_env", "secret_key_env"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            account = self.store.save(dict(arguments))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        missing = self.store.missing_env_vars(account)
        data = {"account": account, "env_ready": len(missing) == 0}
        if missing:
            data["warning"] = (f"다음 환경변수가 아직 설정되지 않았습니다: "
                               f"{', '.join(missing)}. 실거래 세션 생성 전에 설정하세요.")
        return ToolResult(success=True, data=data)


class ListAccountsTool(Tool):
    name = "list_accounts"
    description = "등록된 계좌 목록을 조회합니다 (키 값은 절대 포함되지 않음)"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True, data={"accounts": self.store.list_accounts()})


class DeleteAccountTool(Tool):
    name = "delete_account"
    description = "계좌 등록을 삭제합니다 (해당 계좌를 사용 중인 세션이 있으면 불가)"
    input_schema = {
        "type": "object",
        "properties": {"name": ACCOUNT_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store, session_manager):
        self.store = store
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        name = arguments.get("name")
        in_use = [s.name for s in self.session_manager.sessions.values()
                  if s.account == name]
        if in_use:
            return ToolResult(
                success=False,
                error=f"계좌 '{name}'은 세션에서 사용 중입니다: {', '.join(in_use)}")
        if self.store.delete(name):
            return ToolResult(success=True, data={"deleted": name})
        return ToolResult(success=False, error=f"계좌를 찾을 수 없습니다: {name}")
