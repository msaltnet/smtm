import json
import os
import re
from .log_manager import LogManager


class AccountStore:
    """계좌 자격증명 레지스트리.

    키 원문이 아닌 환경변수 '이름'만 저장한다. 파일 1개 = 계좌 1개,
    경로: <dir_path>/<name>.json
    """

    ALLOWED_FIELDS = {"name", "exchange", "access_key_env", "secret_key_env"}
    REQUIRED_FIELDS = ("name", "exchange", "access_key_env", "secret_key_env")
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    def __init__(self, dir_path="config/accounts"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.dir_path = dir_path

    def validate(self, account: dict):
        if not isinstance(account, dict):
            raise ValueError("계좌 정보는 딕셔너리여야 합니다")
        name = account.get("name")
        if not name or not self.NAME_PATTERN.match(str(name)):
            raise ValueError("계좌 별칭은 영문/숫자/-/_ 1~64자여야 합니다")
        unknown = set(account.keys()) - self.ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"알 수 없는 계좌 필드: {', '.join(sorted(unknown))}")
        for key in self.REQUIRED_FIELDS:
            if not account.get(key):
                raise ValueError(f"필수 계좌 필드가 없습니다: {key}")

    def missing_env_vars(self, account: dict) -> list:
        """설정되지 않은 키 환경변수 '이름' 목록 (값은 읽지 않는다)"""
        return [
            account[key]
            for key in ("access_key_env", "secret_key_env")
            if not os.environ.get(account.get(key, ""), "")
        ]

    def save(self, account: dict) -> dict:
        self.validate(account)
        os.makedirs(self.dir_path, exist_ok=True)
        with open(self._path(account["name"]), "w", encoding="utf-8") as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
        return account

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            raise ValueError(f"계좌를 찾을 수 없습니다: {name}")
        with open(path, "r", encoding="utf-8") as f:
            account = json.load(f)
        self.validate(account)
        return account

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            return False
        os.remove(path)
        return True

    def list_accounts(self) -> list:
        if not os.path.isdir(self.dir_path):
            return []
        summaries = []
        for filename in sorted(os.listdir(self.dir_path)):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.dir_path, filename), "r",
                          encoding="utf-8") as f:
                    account = json.load(f)
                if not isinstance(account, dict):
                    self.logger.warning(f"invalid account file {filename}: not a dict")
                    continue
                summaries.append({
                    "name": account.get("name"),
                    "exchange": account.get("exchange"),
                    "access_key_env": account.get("access_key_env"),
                    "secret_key_env": account.get("secret_key_env"),
                    "env_ready": len(self.missing_env_vars(account)) == 0,
                })
            except (json.JSONDecodeError, OSError) as err:
                self.logger.warning(f"invalid account file {filename}: {err}")
        return summaries

    def _path(self, name: str) -> str:
        return os.path.join(self.dir_path, f"{name}.json")
