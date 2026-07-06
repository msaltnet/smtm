import json
import os
import re
from .log_manager import LogManager


class ProfileStore:
    """계좌 프로파일(실행 프리셋 번들) JSON 영속화 저장소.

    파일 1개 = 프로파일 1개, 경로: <dir_path>/<name>.json
    """

    ALLOWED_FIELDS = {
        "name", "exchange", "currency", "budget", "virtual",
        "term", "strategy", "strategy_params", "safety",
    }
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    def __init__(self, dir_path="config/profiles"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.dir_path = dir_path

    def validate(self, profile: dict):
        if not isinstance(profile, dict):
            raise ValueError("프로파일은 딕셔너리여야 합니다")
        name = profile.get("name")
        if not name or not self.NAME_PATTERN.match(str(name)):
            raise ValueError(
                "프로파일 이름은 영문/숫자/-/_ 1~64자여야 합니다")
        unknown = set(profile.keys()) - self.ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"알 수 없는 프로파일 필드: {', '.join(sorted(unknown))}")

    def save(self, profile: dict) -> dict:
        self.validate(profile)
        os.makedirs(self.dir_path, exist_ok=True)
        with open(self._path(profile["name"]), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        return profile

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            raise ValueError(f"프로파일을 찾을 수 없습니다: {name}")
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        self.validate(profile)
        return profile

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            return False
        os.remove(path)
        return True

    def list_profiles(self) -> list:
        if not os.path.isdir(self.dir_path):
            return []
        summaries = []
        for filename in sorted(os.listdir(self.dir_path)):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.dir_path, filename), "r",
                          encoding="utf-8") as f:
                    profile = json.load(f)
                if not isinstance(profile, dict):
                    self.logger.warning(f"invalid profile file {filename}: not a dict")
                    continue
                summaries.append({
                    "name": profile.get("name"),
                    "strategy": profile.get("strategy"),
                    "exchange": profile.get("exchange"),
                    "virtual": profile.get("virtual"),
                })
            except (json.JSONDecodeError, OSError) as err:
                self.logger.warning(f"invalid profile file {filename}: {err}")
        return summaries

    def _path(self, name: str) -> str:
        return os.path.join(self.dir_path, f"{name}.json")
