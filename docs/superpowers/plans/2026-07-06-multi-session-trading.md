# 멀티 세션 실거래 분산 운용 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여러 전략 × 여러 계좌 × 여러 심볼을 독립 `TradingOperator` 세션으로 병렬 운영하고, LLM 오케스트레이터(SystemOperator)가 계좌/세션을 Tool로 지휘한다.

**Architecture:** `SessionManager`가 `{name: TradingSession}` N개를 보유·검증(소프트 예산 합계 ≤ 실잔고, (계좌,심볼) 충돌 방지). 계좌 자격증명은 `AccountStore`가 환경변수 **이름만** 저장. 계좌 수준 안전장치 `AccountGuard`를 세션 SafetyGuard와 `CompositeSafetyGuard`로 합성해 `TradingOperator`에 무변경 주입. 스펙: `docs/superpowers/specs/2026-07-06-multi-session-trading-design.md`

**Tech Stack:** Python, pytest(unittest 스타일), 기존 v2.0.0 스택 (TradingOperator/Strategy/ProfileStore/SystemOperator)

## Global Constraints

- 테스트 실행: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -q` (유닛 테스트에서 실 네트워크 호출 금지)
- 커밋 메시지: `[feat]`/`[fix]`/`[test]`/`[refactor]`/`[docs]` 접두사. **`Co-Authored-By` 트레일러 절대 금지**
- **키 원문 비노출**: API 키 값은 환경변수에만 존재. 파일/Tool 결과/로그/대화에는 환경변수 *이름*만
- 매매 경로는 세션 내부의 `Strategy.get_request() → Trader.send_request()` 단일 경로. 에이전트에 `execute_trade` 류 Tool 금지
- 알고리즘 전략 세션의 틱에서 LLM 호출 0회
- 안전 카운터는 세션 재생성/전환으로 리셋되지 않는다 (AccountGuard는 계좌별 공유, 세션 가드 일일 카운터는 replace 시 승계)
- 사용자/LLM 노출 문자열은 한국어
- Python 3.9 호환 문법 사용 (`Optional[str]`, `str | None` 금지)
- 레거시 실거래 기본 환경변수명: Upbit `UPBIT_OPEN_API_ACCESS_KEY`/`UPBIT_OPEN_API_SECRET_KEY`, Bithumb `BITHUMB_API_ACCESS_KEY`/`BITHUMB_API_SECRET_KEY` (SERVER_URL 환경변수는 계좌별 분리 안 함)

## 파일 구조 (전체 조망)

**Create:**

| 파일 | 책임 |
|------|------|
| `smtm/account_store.py` | `AccountStore` — 계좌 자격증명 레지스트리 (env 이름 참조) |
| `smtm/llm/account_guard.py` | `AccountGuard`(계좌 수준 안전장치) + `CompositeSafetyGuard` |
| `smtm/session_manager.py` | `TradingSession` + `SessionManager` — 병렬 세션 관리 핵심 |
| `smtm/llm/tools/account_tools.py` | 계좌 Tool 3종 |
| `smtm/llm/tools/session_tools.py` | 세션 Tool 6종 |

**Modify:** `smtm/trader/upbit_trader.py`·`bithumb_trader.py`(env 주입), `smtm/trader/trader_factory.py`(account 파라미터), `smtm/profile_store.py`·`smtm/llm/tools/profile_tools.py`(account 필드), `smtm/llm/system_monitor.py`(세션 태깅), `smtm/analyzer.py`(session_name), `smtm/llm/system_operator.py`(SessionManager 보유·레거시 위임), `smtm/llm/tools/orchestration_tools.py`(GetStatus session 인자), `smtm/llm/tools/market_data_tool.py`·`portfolio_tool.py`·`performance_tool.py`·`trade_history_tool.py`(세션 인식), `smtm/controller/controller.py`·`jpt_controller.py`·`telegram/telegram_controller.py`(shutdown·autostart 제거), `smtm/__init__.py`, README 2종

---

### Task 1: AccountStore — 계좌 자격증명 레지스트리

**Files:**
- Create: `smtm/account_store.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/account_store_test.py`

**Interfaces:**
- Consumes: `smtm.log_manager.LogManager`, `os.environ`
- Produces: `AccountStore(dir_path="config/accounts")` — `list_accounts() -> list[dict]`(요약: name/exchange/env 이름/env_ready), `load(name) -> dict`, `save(account) -> dict`, `delete(name) -> bool`, `validate(account)`(ValueError 한국어), `missing_env_vars(account) -> list[str]`. 허용 필드 4종 전부 필수: `name`, `exchange`, `access_key_env`, `secret_key_env`. 파일 1개=계좌 1개.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/account_store_test.py`:

```python
import os
import unittest
import tempfile
from unittest.mock import patch
from smtm import AccountStore


ACCOUNT = {
    "name": "main",
    "exchange": "UPB",
    "access_key_env": "SMTM_TEST_KEY_1",
    "secret_key_env": "SMTM_TEST_SECRET_1",
}


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AccountStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        self.store.save(ACCOUNT)
        self.assertEqual(self.store.load("main"), ACCOUNT)

    def test_save_never_stores_key_values(self):
        # 파일 내용에 환경변수 '이름'만 있고 값이 없어야 한다
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "REAL-KEY-VALUE"}):
            self.store.save(ACCOUNT)
        path = os.path.join(self.tmp.name, "main.json")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("SMTM_TEST_KEY_1", content)
        self.assertNotIn("REAL-KEY-VALUE", content)

    def test_missing_env_vars_reports_unset_names(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SMTM_TEST_KEY_1", None)
            os.environ.pop("SMTM_TEST_SECRET_1", None)
            missing = self.store.missing_env_vars(ACCOUNT)
        self.assertEqual(set(missing), {"SMTM_TEST_KEY_1", "SMTM_TEST_SECRET_1"})

    def test_missing_env_vars_empty_when_set(self):
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            self.assertEqual(self.store.missing_env_vars(ACCOUNT), [])

    def test_list_accounts_includes_env_ready(self):
        self.store.save(ACCOUNT)
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            accounts = self.store.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "main")
        self.assertEqual(accounts[0]["exchange"], "UPB")
        self.assertTrue(accounts[0]["env_ready"])

    def test_validate_rejects_missing_required_field(self):
        for key in ("name", "exchange", "access_key_env", "secret_key_env"):
            broken = dict(ACCOUNT)
            del broken[key]
            with self.assertRaises(ValueError):
                self.store.validate(broken)

    def test_validate_rejects_unknown_field_and_bad_name(self):
        with self.assertRaises(ValueError):
            self.store.validate({**ACCOUNT, "secret_key": "raw-value"})
        with self.assertRaises(ValueError):
            self.store.validate({**ACCOUNT, "name": "../evil"})

    def test_delete(self):
        self.store.save(ACCOUNT)
        self.assertTrue(self.store.delete("main"))
        self.assertFalse(self.store.delete("main"))

    def test_load_missing_raises(self):
        with self.assertRaises(ValueError):
            self.store.load("nope")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/account_store_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'AccountStore'`

- [ ] **Step 3: 구현**

`smtm/account_store.py`:

```python
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
```

`smtm/__init__.py`에 `from .account_store import AccountStore` 추가 (ProfileStore import 근처), `__all__`에 `"AccountStore"` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/account_store_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/account_store.py smtm/__init__.py tests/unit_tests/account_store_test.py
git commit -m "[feat] add AccountStore for env-referenced account credentials"
```

---

### Task 2: Trader 자격증명 주입

**Files:**
- Modify: `smtm/trader/upbit_trader.py`, `smtm/trader/bithumb_trader.py`, `smtm/trader/trader_factory.py`
- Test: `tests/unit_tests/trader_factory_account_test.py` (신규), 기존 `upbit_trader_test.py`/`bithumb_trader_test.py` 회귀 확인

**Interfaces:**
- Consumes: `BaseExchangeTrader.__init__(..., env_key_names=(ACCESS, SECRET, SERVER_URL))` (기존 — 변경 없음)
- Produces: `UpbitTrader(..., access_key_env=None, secret_key_env=None)` / `BithumbTrader(동일)` — 지정 시 해당 환경변수에서 키 로드, 미지정 시 레거시 기본값(하위 호환). `TraderFactory.create(code, budget, currency, commission_ratio, paper, account=None)` — account dict(`access_key_env`/`secret_key_env`)가 있으면 전달.
- 참고: `cancel_all_requests`는 `BaseExchangeTrader`가 자기 `order_map`만 순회(base_exchange_trader.py:95-101) — **이미 자기 주문 한정**. 회귀 테스트만 추가.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/trader_factory_account_test.py`:

```python
import os
import unittest
from unittest.mock import patch
from smtm.trader.trader_factory import TraderFactory
from smtm.trader.simulation_trader import SimulationTrader


class TraderFactoryAccountTests(unittest.TestCase):
    def test_create_with_account_uses_custom_env_names(self):
        with patch.dict(os.environ, {
            "SMTM_KEY_9": "custom-access",
            "SMTM_SECRET_9": "custom-secret",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create(
                "UPB", budget=100000, currency="BTC",
                account={"access_key_env": "SMTM_KEY_9",
                         "secret_key_env": "SMTM_SECRET_9"})
        self.assertEqual(trader.ACCESS_KEY, "custom-access")
        self.assertEqual(trader.SECRET_KEY, "custom-secret")
        trader.worker.stop()

    def test_create_without_account_uses_legacy_env_names(self):
        with patch.dict(os.environ, {
            "UPBIT_OPEN_API_ACCESS_KEY": "legacy-access",
            "UPBIT_OPEN_API_SECRET_KEY": "legacy-secret",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create("UPB", budget=100000, currency="BTC")
        self.assertEqual(trader.ACCESS_KEY, "legacy-access")
        trader.worker.stop()

    def test_paper_ignores_account(self):
        trader = TraderFactory.create(
            "UPB", budget=100000, currency="BTC", paper=True,
            account={"access_key_env": "X", "secret_key_env": "Y"})
        self.assertIsInstance(trader, SimulationTrader)

    def test_cancel_all_requests_only_touches_own_order_map(self):
        # 자기 order_map의 주문만 취소 요청한다 (계좌 전체 취소 금지 보장)
        with patch.dict(os.environ, {
            "UPBIT_OPEN_API_ACCESS_KEY": "a", "UPBIT_OPEN_API_SECRET_KEY": "b",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create("UPB", budget=100000, currency="BTC")
        cancelled = []
        trader.cancel_request = lambda request_id: cancelled.append(request_id)
        trader.order_map = {"r1": {"uuid": "u1"}, "r2": {"uuid": "u2"}}
        trader.cancel_all_requests()
        self.assertEqual(sorted(cancelled), ["r1", "r2"])
        trader.worker.stop()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/trader_factory_account_test.py -x -q`
Expected: FAIL — `TypeError: create() got an unexpected keyword argument 'account'`

- [ ] **Step 3: 구현**

`smtm/trader/upbit_trader.py` 생성자 수정:

```python
    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.0005, opt_mode=True,
        access_key_env=None, secret_key_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="UpbitTrader",
            worker_name="UpbitTrader-Worker",
            env_key_names=(
                access_key_env or "UPBIT_OPEN_API_ACCESS_KEY",
                secret_key_env or "UPBIT_OPEN_API_SECRET_KEY",
                "UPBIT_OPEN_API_SERVER_URL",
            ),
        )
```

`smtm/trader/bithumb_trader.py` 생성자도 동일 패턴 (`access_key_env or "BITHUMB_API_ACCESS_KEY"`, `secret_key_env or "BITHUMB_API_SECRET_KEY"`, SERVER_URL은 `"BITHUMB_API_SERVER_URL"` 고정).

`smtm/trader/trader_factory.py`:

```python
    @staticmethod
    def create(code, budget=50000, currency="BTC", commission_ratio=0.0005,
               paper=False, account=None):
        if paper:
            return SimulationTrader(
                budget=budget,
                currency=currency,
                commission_ratio=commission_ratio,
            )

        for trader in TraderFactory.TRADER_LIST:
            if trader.CODE == code:
                kwargs = {
                    "budget": budget,
                    "currency": currency,
                    "commission_ratio": commission_ratio,
                }
                if account:
                    kwargs["access_key_env"] = account.get("access_key_env")
                    kwargs["secret_key_env"] = account.get("secret_key_env")
                return trader(**kwargs)
        return None
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/trader_factory_account_test.py tests/unit_tests/upbit_trader_test.py tests/unit_tests/bithumb_trader_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/trader/ tests/unit_tests/trader_factory_account_test.py
git commit -m "[feat] support per-account credential env names in exchange traders"
```

---

### Task 3: AccountGuard + CompositeSafetyGuard

**Files:**
- Create: `smtm/llm/account_guard.py`
- Modify: `smtm/llm/__init__.py`
- Test: `tests/unit_tests/account_guard_test.py`

**Interfaces:**
- Consumes: `SafetyResult` (smtm/llm/safety_guard.py)
- Produces:
  - `AccountGuardConfig(max_daily_trades=60, max_total_allocation=10_000_000)`
  - `AccountGuard(config=None)` — `check_request(request) -> SafetyResult`(cancel 무조건 허용, 일일 총 횟수), `record_trade(result)`(Lock), `update_portfolio_value(v)`(no-op), `can_allocate(amount) -> SafetyResult`, `allocate(session_name, amount)`, `release(session_name)`, `total_allocated() -> float`, `get_status() -> dict`
  - `CompositeSafetyGuard(session_guard, account_guard)` — 동일 가드 인터페이스. check는 세션→계좌 순, record는 양쪽, update_portfolio_value는 세션만, `get_status()`는 `{"session":..., "account":...}`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/account_guard_test.py`:

```python
import threading
import unittest
from smtm.llm.account_guard import (
    AccountGuard, AccountGuardConfig, CompositeSafetyGuard,
)
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig


def _request(type="buy", price=50000, amount=1.0):
    return {"id": "t", "type": type, "price": price, "amount": amount,
            "date_time": "2026-07-06T12:00:00"}


class AccountGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = AccountGuard(AccountGuardConfig(
            max_daily_trades=3, max_total_allocation=1000000))

    def test_allows_within_daily_limit_blocks_after(self):
        for _ in range(3):
            self.assertTrue(self.guard.check_request(_request()).allowed)
            self.guard.record_trade({})
        verdict = self.guard.check_request(_request())
        self.assertFalse(verdict.allowed)
        self.assertIn("계좌 일일 거래횟수", verdict.reason)

    def test_cancel_always_allowed(self):
        for _ in range(3):
            self.guard.record_trade({})
        self.assertTrue(self.guard.check_request(_request(type="cancel")).allowed)

    def test_allocation_lifecycle(self):
        self.assertTrue(self.guard.can_allocate(600000).allowed)
        self.guard.allocate("s1", 600000)
        self.assertEqual(self.guard.total_allocated(), 600000)
        verdict = self.guard.can_allocate(500000)  # 600000+500000 > 1000000
        self.assertFalse(verdict.allowed)
        self.assertIn("할당 총액", verdict.reason)
        self.guard.release("s1")
        self.assertTrue(self.guard.can_allocate(500000).allowed)

    def test_release_unknown_session_is_noop(self):
        self.guard.release("nope")
        self.assertEqual(self.guard.total_allocated(), 0)

    def test_record_trade_is_thread_safe(self):
        guard = AccountGuard(AccountGuardConfig(max_daily_trades=100000))
        threads = [threading.Thread(
            target=lambda: [guard.record_trade({}) for _ in range(500)])
            for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(guard.daily_trade_count, 2000)

    def test_get_status_summarizes(self):
        self.guard.allocate("s1", 300000)
        self.guard.record_trade({})
        status = self.guard.get_status()
        self.assertEqual(status["daily_trades"], 1)
        self.assertEqual(status["daily_limit"], 3)
        self.assertEqual(status["total_allocated"], 300000)
        self.assertIn("s1", status["allocations"])


class CompositeSafetyGuardTests(unittest.TestCase):
    def setUp(self):
        self.session_guard = SafetyGuard(SafetyConfig(
            max_trade_amount=100000, max_daily_trades=10,
            max_loss_ratio=-0.5, initial_budget=500000))
        self.account_guard = AccountGuard(AccountGuardConfig(max_daily_trades=2))
        self.composite = CompositeSafetyGuard(self.session_guard, self.account_guard)

    def test_passes_when_both_allow(self):
        self.assertTrue(self.composite.check_request(_request()).allowed)

    def test_session_block_wins_first(self):
        verdict = self.composite.check_request(_request(price=200000, amount=1.0))
        self.assertFalse(verdict.allowed)
        self.assertIn("최대 거래금액", verdict.reason)  # 세션 사유

    def test_account_block_applies(self):
        self.account_guard.record_trade({})
        self.account_guard.record_trade({})
        verdict = self.composite.check_request(_request())
        self.assertFalse(verdict.allowed)
        self.assertIn("계좌 일일 거래횟수", verdict.reason)

    def test_record_trade_propagates_to_both(self):
        self.composite.record_trade({})
        self.assertEqual(self.session_guard.daily_trade_count, 1)
        self.assertEqual(self.account_guard.daily_trade_count, 1)

    def test_update_portfolio_value_only_session(self):
        self.composite.update_portfolio_value(400000)
        self.assertEqual(self.session_guard.current_value, 400000)

    def test_get_status_has_both(self):
        status = self.composite.get_status()
        self.assertIn("session", status)
        self.assertIn("account", status)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/account_guard_test.py -x -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'smtm.llm.account_guard'`

- [ ] **Step 3: 구현**

`smtm/llm/account_guard.py`:

```python
import threading
from dataclasses import dataclass
from datetime import date
from ..log_manager import LogManager
from .safety_guard import SafetyResult


@dataclass
class AccountGuardConfig:
    """계좌 수준 안전장치 설정"""
    max_daily_trades: int = 60
    max_total_allocation: float = 10_000_000


class AccountGuard:
    """계좌 수준 안전장치 — 같은 계좌의 모든 실거래 세션이 공유한다.

    세션 재생성/전환으로 카운터가 리셋되지 않는다 (LLM 우회 방지).
    여러 세션의 워커 스레드가 동시 접근하므로 Lock으로 보호한다.
    """

    def __init__(self, config=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.config = config or AccountGuardConfig()
        self._lock = threading.Lock()
        self.daily_trade_count = 0
        self.daily_date = date.today()
        self.allocations = {}  # session_name -> soft budget

    def check_request(self, request: dict) -> SafetyResult:
        if request.get("type") == "cancel":
            return SafetyResult(allowed=True)
        with self._lock:
            self._reset_daily_if_needed()
            if self.daily_trade_count >= self.config.max_daily_trades:
                reason = (f"계좌 일일 거래횟수 초과 "
                          f"({self.daily_trade_count}/{self.config.max_daily_trades})")
                self.logger.warning(reason)
                return SafetyResult(allowed=False, reason=reason)
        return SafetyResult(allowed=True)

    def record_trade(self, result):
        del result
        with self._lock:
            self._reset_daily_if_needed()
            self.daily_trade_count += 1

    def update_portfolio_value(self, value):
        """계좌 가드는 세션별 포트폴리오 가치를 추적하지 않는다 (후속: 통합 손실률)"""
        del value

    def can_allocate(self, amount: float) -> SafetyResult:
        with self._lock:
            total = sum(self.allocations.values()) + float(amount)
            if total > self.config.max_total_allocation:
                reason = (f"계좌 할당 총액 초과 "
                          f"({total:,.0f} > {self.config.max_total_allocation:,.0f})")
                self.logger.warning(reason)
                return SafetyResult(allowed=False, reason=reason)
        return SafetyResult(allowed=True)

    def allocate(self, session_name: str, amount: float):
        with self._lock:
            self.allocations[session_name] = float(amount)

    def release(self, session_name: str):
        with self._lock:
            self.allocations.pop(session_name, None)

    def total_allocated(self) -> float:
        with self._lock:
            return sum(self.allocations.values())

    def get_status(self) -> dict:
        with self._lock:
            self._reset_daily_if_needed()
            return {
                "daily_trades": self.daily_trade_count,
                "daily_limit": self.config.max_daily_trades,
                "total_allocated": sum(self.allocations.values()),
                "max_total_allocation": self.config.max_total_allocation,
                "allocations": dict(self.allocations),
            }

    def _reset_daily_if_needed(self):
        today = date.today()
        if self.daily_date != today:
            self.daily_trade_count = 0
            self.daily_date = today


class CompositeSafetyGuard:
    """세션 가드 + 계좌 가드 합성 — TradingOperator는 단일 가드 인터페이스만 본다"""

    def __init__(self, session_guard, account_guard):
        self.session_guard = session_guard
        self.account_guard = account_guard

    def check_request(self, request: dict) -> SafetyResult:
        for guard in (self.session_guard, self.account_guard):
            verdict = guard.check_request(request)
            if not verdict.allowed:
                return verdict
        return SafetyResult(allowed=True)

    def record_trade(self, result):
        self.session_guard.record_trade(result)
        self.account_guard.record_trade(result)

    def update_portfolio_value(self, value):
        self.session_guard.update_portfolio_value(value)

    def get_status(self) -> dict:
        return {
            "session": self.session_guard.get_status(),
            "account": self.account_guard.get_status(),
        }
```

`smtm/llm/__init__.py`에 추가:

```python
from .account_guard import AccountGuard, AccountGuardConfig, CompositeSafetyGuard
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/account_guard_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/llm/account_guard.py smtm/llm/__init__.py tests/unit_tests/account_guard_test.py
git commit -m "[feat] add AccountGuard and CompositeSafetyGuard for account-level limits"
```

---

### Task 4: 프로파일 스키마에 account 필드 추가

**Files:**
- Modify: `smtm/profile_store.py`, `smtm/llm/tools/profile_tools.py`
- Test: `tests/unit_tests/profile_store_test.py` (테스트 추가)

**Interfaces:**
- Produces: `ProfileStore.ALLOWED_FIELDS`에 `account` 추가. `PROFILE_PROPERTIES`에 `"account": {"type": "string", "description": "계좌 별칭 (실거래 세션에 필요, 가상은 불필요)"}` 추가.

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/unit_tests/profile_store_test.py`의 `ProfileStoreTests`에:

```python
    def test_account_field_is_allowed(self):
        profile = {**PROFILE, "account": "main"}
        self.store.save(profile)
        self.assertEqual(self.store.load(PROFILE["name"])["account"], "main")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/profile_store_test.py -x -q`
Expected: FAIL — `ValueError: 알 수 없는 프로파일 필드: account`

- [ ] **Step 3: 구현**

`smtm/profile_store.py`의 `ALLOWED_FIELDS`에 `"account"` 추가:

```python
    ALLOWED_FIELDS = {
        "name", "exchange", "currency", "budget", "virtual",
        "term", "strategy", "strategy_params", "safety", "account",
    }
```

`smtm/llm/tools/profile_tools.py`의 `PROFILE_PROPERTIES`에 추가:

```python
    "account": {"type": "string",
                "description": "계좌 별칭 (실거래 세션에 필요, 가상매매는 불필요)"},
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/profile_store_test.py tests/unit_tests/profile_tools_test.py -q` → PASS

```bash
git add smtm/profile_store.py smtm/llm/tools/profile_tools.py tests/unit_tests/profile_store_test.py
git commit -m "[feat] add account field to profile schema"
```

---

### Task 5: SystemMonitor 세션 태깅 + Analyzer session_name

**Files:**
- Modify: `smtm/llm/system_monitor.py`, `smtm/analyzer.py`
- Test: `tests/unit_tests/system_monitor_test.py`, `tests/unit_tests/analyzer_test.py` (테스트 추가)

**Interfaces:**
- Produces: `SystemMonitor.log_market_data(data, session=None)`, `log_trade_request(request, session=None)`, `log_trade_result(result, session=None)`, `log_safety_event(event, session=None)` — 기록 dict에 `"session"` 키 추가. `get_trade_log(start_time=None, end_time=None, session=None)` — session 지정 시 필터. `Analyzer(system_monitor, session_name=None)` — put_* 호출 시 세션 이름 전달. **모두 기본값 None으로 하위 호환.**

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/unit_tests/system_monitor_test.py` 끝에 (기존 import 스타일 확인 후):

```python
class SystemMonitorSessionTagTests(unittest.TestCase):
    def setUp(self):
        from smtm.llm.system_monitor import SystemMonitor
        self.monitor = SystemMonitor()

    def test_logs_carry_session_tag(self):
        self.monitor.log_market_data([{"type": "primary_candle"}], session="s1")
        self.monitor.log_trade_request({"id": "r1"}, session="s1")
        self.monitor.log_trade_result({"state": "done"}, session="s1")
        self.monitor.log_safety_event({"type": "blocked"}, session="s1")
        self.assertEqual(self.monitor.market_data_log[0]["session"], "s1")
        self.assertEqual(self.monitor.trade_request_log[0]["session"], "s1")
        self.assertEqual(self.monitor.trade_result_log[0]["session"], "s1")
        self.assertEqual(self.monitor.safety_event_log[0]["session"], "s1")

    def test_untagged_logs_default_to_none(self):
        self.monitor.log_trade_result({"state": "done"})
        self.assertIsNone(self.monitor.trade_result_log[0]["session"])

    def test_get_trade_log_filters_by_session(self):
        self.monitor.log_trade_result({"n": 1}, session="s1")
        self.monitor.log_trade_result({"n": 2}, session="s2")
        logs = self.monitor.get_trade_log(session="s1")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["result"]["n"], 1)
        self.assertEqual(len(self.monitor.get_trade_log()), 2)
```

`tests/unit_tests/analyzer_test.py`의 `AnalyzerTests`에:

```python
    def test_analyzer_tags_session_name(self):
        from smtm import Analyzer
        analyzer = Analyzer(self.monitor, session_name="s9")
        analyzer.put_result({"state": "done"})
        self.monitor.log_trade_result.assert_called_once_with(
            {"state": "done"}, session="s9")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/system_monitor_test.py tests/unit_tests/analyzer_test.py -x -q`
Expected: FAIL — `TypeError: log_market_data() got an unexpected keyword argument 'session'`

- [ ] **Step 3: 구현**

`smtm/llm/system_monitor.py` — 4개 메서드에 `session=None` 파라미터 추가, 기록 dict에 `"session": session` 포함:

```python
    def log_market_data(self, data: list, session=None):
        self.market_data_log.append(
            {"timestamp": self._timestamp(), "session": session, "data": data})

    def log_trade_request(self, request: dict, session=None):
        self.trade_request_log.append(
            {"timestamp": self._timestamp(), "session": session, "request": request})

    def log_trade_result(self, result: dict, session=None):
        self.trade_result_log.append(
            {"timestamp": self._timestamp(), "session": session, "result": result})

    def log_safety_event(self, event: dict, session=None):
        self.safety_event_log.append(
            {"timestamp": self._timestamp(), "session": session, "event": event})

    def get_trade_log(self, start_time=None, end_time=None, session=None) -> list:
        if session is None:
            return self.trade_result_log
        return [log for log in self.trade_result_log if log.get("session") == session]
```

`smtm/analyzer.py` — 생성자와 put 4종 수정:

```python
    def __init__(self, system_monitor, session_name=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor
        self.session_name = session_name
        ...  # (이하 기존 동일)

    def put_trading_info(self, info):
        self.system_monitor.log_market_data(info, session=self.session_name)

    def put_requests(self, requests):
        for request in requests:
            self.system_monitor.log_trade_request(request, session=self.session_name)

    def put_result(self, result):
        self.system_monitor.log_trade_result(result, session=self.session_name)

    def put_safety_event(self, event):
        self.system_monitor.log_safety_event(event, session=self.session_name)
```

주의: 기존 `analyzer_test.py`의 delegate 테스트가 `assert_called_once()` 형태면 그대로 통과. 위치 인자 검증이 있으면 kwargs에 맞게 갱신.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/system_monitor_test.py tests/unit_tests/analyzer_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/llm/system_monitor.py smtm/analyzer.py tests/unit_tests/
git commit -m "[feat] tag monitor logs with session name"
```

---

### Task 6: SessionManager + TradingSession (핵심)

**Files:**
- Create: `smtm/session_manager.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/session_manager_test.py`

**Interfaces:**
- Consumes: Task 1~5 전부 + `TradingOperator`/`StrategyFactory`/`DataProviderFactory`/`TraderFactory`/`Analyzer`/`SafetyGuard`
- Produces:

```python
@dataclass
class TradingSession:
    name: str
    profile: dict           # 생성 시점 스냅샷
    operator: object        # TradingOperator
    trader: object
    session_guard: object   # 세션 SafetyGuard (composite 내부의 세션 측)
    account: Optional[str]  # 가드 별칭 (실거래: 계좌 별칭 또는 "legacy", 가상: None)
    created_at: str
    # .state 프로퍼티 → operator.state

class SessionManager:
    DEFAULT_SESSION = "default"
    def __init__(self, account_store=None, llm_client=None, system_monitor=None)
    def create_session(self, profile: dict, name=None) -> dict
    def replace_session(self, name, profile) -> dict   # stopped 세션 교체, 세션가드 일일카운터 승계
    def start_session(self, name) -> dict
    def stop_session(self, name) -> dict
    def remove_session(self, name) -> dict
    def stop_all(self)
    def list_sessions(self) -> list
    def get_session(self, name) -> TradingSession     # 없으면 ValueError(한국어)
    def get_session_status(self, name) -> dict
    def get_performance(self, name) -> dict
    def compare_performance(self) -> list
    def get_account_guard(self, alias) -> AccountGuard  # 별칭당 1개 유지
```

- 검증 규칙 (스펙 3.6): 이름 유일성/패턴 → 전략·거래소 유효 → 실거래면 (계좌 로드+거래소 일치+env 존재) → (계좌,심볼) 충돌 → 실잔고+할당 검사 → 조립. **실패 시 무부작용** (생성한 trader worker는 stop).
- default 특례: `account` 미지정 실거래는 `name == "default"`만 허용, 별칭 `"legacy"`, 실잔고 검증 생략(can_allocate 총액 검사는 수행).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/session_manager_test.py`:

```python
import os
import time
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from smtm import SessionManager, AccountStore
from smtm.llm.system_monitor import SystemMonitor


class StubDataProvider:
    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-06T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


VIRTUAL_PROFILE = {
    "name": "v1", "exchange": "UPB", "currency": "BTC",
    "budget": 500000, "virtual": True, "term": 60, "strategy": "BNH",
}


def make_manager(tmp_dir):
    store = AccountStore(dir_path=tmp_dir)
    manager = SessionManager(
        account_store=store, llm_client=None,
        system_monitor=SystemMonitor())
    return manager, store


class SessionManagerVirtualTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager, self.store = make_manager(self.tmp.name)
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.manager.stop_all()
        self.tmp.cleanup()

    def test_create_and_start_two_virtual_sessions_independently(self):
        r1 = self.manager.create_session(VIRTUAL_PROFILE)
        r2 = self.manager.create_session(
            {**VIRTUAL_PROFILE, "name": "v2", "strategy": "RSI"})
        self.assertTrue(r1["success"] and r2["success"])
        self.assertTrue(self.manager.start_session("v1")["success"])
        self.assertTrue(self.manager.start_session("v2")["success"])
        # start()가 워커에 첫 틱을 즉시 post하므로 수동 틱 대신 폴링으로
        # 첫 체결을 기다린다 (interval=60 → 두 번째 틱 없음)
        s1 = self.manager.get_session("v1")
        s2 = self.manager.get_session("v2")
        deadline = time.time() + 5
        while time.time() < deadline and len(s1.trader.order_history) == 0:
            time.sleep(0.05)
        self.assertEqual(len(s1.trader.order_history), 1)  # BnH 첫 틱 매수
        # v2(RSI)는 캔들 부족으로 주문 없음 — 서로 간섭 없음 확인이 핵심
        self.assertEqual(s2.trader.balance, 500000)
        self.manager.stop_session("v1")
        self.manager.stop_session("v2")

    def test_duplicate_name_rejected(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        result = self.manager.create_session(VIRTUAL_PROFILE)
        self.assertFalse(result["success"])
        self.assertIn("이미 존재", result["error"])

    def test_invalid_strategy_rejected_without_side_effects(self):
        result = self.manager.create_session({**VIRTUAL_PROFILE, "strategy": "NOPE"})
        self.assertFalse(result["success"])
        self.assertEqual(self.manager.list_sessions(), [])

    def test_remove_running_session_stops_first(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.start_session("v1")
        result = self.manager.remove_session("v1")
        self.assertTrue(result["success"])
        self.assertEqual(self.manager.list_sessions(), [])

    def test_list_sessions_summary(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        summary = self.manager.list_sessions()[0]
        self.assertEqual(summary["name"], "v1")
        self.assertEqual(summary["state"], "ready")
        self.assertEqual(summary["strategy"], "BNH")
        self.assertTrue(summary["virtual"])

    def test_compare_performance_covers_all_sessions(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.create_session({**VIRTUAL_PROFILE, "name": "v2"})
        rows = self.manager.compare_performance()
        self.assertEqual({r["session"] for r in rows}, {"v1", "v2"})
        self.assertIn("cumulative_return", rows[0])

    def test_replace_session_preserves_daily_count_and_rolls_back(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.get_session("v1").session_guard.record_trade({})
        # 교체 성공: 카운터 승계
        result = self.manager.replace_session(
            "v1", {**VIRTUAL_PROFILE, "strategy": "RSI"})
        self.assertTrue(result["success"])
        self.assertEqual(
            self.manager.get_session("v1").session_guard.daily_trade_count, 1)
        # 교체 실패: 기존 세션 유지
        result = self.manager.replace_session(
            "v1", {**VIRTUAL_PROFILE, "strategy": "NOPE"})
        self.assertFalse(result["success"])
        self.assertEqual(self.manager.get_session("v1").profile["strategy"], "RSI")


class SessionManagerRealTradeValidationTests(unittest.TestCase):
    """실거래 검증 경로 — Trader/잔고는 전부 mock"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager, self.store = make_manager(self.tmp.name)
        self.store.save({"name": "main", "exchange": "UPB",
                         "access_key_env": "SMTM_T_K1",
                         "secret_key_env": "SMTM_T_S1"})
        self.real_profile = {
            "name": "r1", "exchange": "UPB", "currency": "BTC",
            "budget": 300000, "virtual": False, "term": 60,
            "strategy": "BNH", "account": "main",
        }
        self.fake_trader = MagicMock()
        self.fake_trader.get_account_info.return_value = {
            "balance": 1000000, "asset": {}, "quote": {}}
        dp = patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: StubDataProvider())
        tf = patch("smtm.trader.trader_factory.TraderFactory.create",
                   return_value=self.fake_trader)
        env = patch.dict(os.environ, {"SMTM_T_K1": "k", "SMTM_T_S1": "s"})
        for p in (dp, tf, env):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.manager.stop_all()
        self.tmp.cleanup()

    def test_real_session_created_with_composite_guard_and_allocation(self):
        result = self.manager.create_session(self.real_profile)
        self.assertTrue(result["success"])
        guard = self.manager.get_account_guard("main")
        self.assertEqual(guard.total_allocated(), 300000)
        from smtm.llm.account_guard import CompositeSafetyGuard
        session = self.manager.get_session("r1")
        self.assertIsInstance(session.operator.safety_guard, CompositeSafetyGuard)

    def test_missing_account_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r2", "account": "ghost"})
        self.assertFalse(result["success"])

    def test_missing_env_rejected(self):
        os.environ.pop("SMTM_T_S1", None)
        result = self.manager.create_session({**self.real_profile, "name": "r3"})
        self.assertFalse(result["success"])
        self.assertIn("SMTM_T_S1", result["error"])

    def test_exchange_mismatch_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r4", "exchange": "BTH"})
        self.assertFalse(result["success"])
        self.assertIn("거래소", result["error"])

    def test_account_symbol_conflict_rejected_but_other_symbol_ok(self):
        self.manager.create_session(self.real_profile)
        conflict = self.manager.create_session(
            {**self.real_profile, "name": "r5"})  # 같은 main+BTC
        self.assertFalse(conflict["success"])
        self.assertIn("이미 운영 중", conflict["error"])
        other = self.manager.create_session(
            {**self.real_profile, "name": "r6", "currency": "ETH"})
        self.assertTrue(other["success"])

    def test_budget_over_real_balance_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r7", "budget": 2000000})
        self.assertFalse(result["success"])
        self.assertIn("잔고", result["error"])

    def test_allocation_sum_respects_balance(self):
        self.manager.create_session(self.real_profile)  # 30만 할당
        result = self.manager.create_session(
            {**self.real_profile, "name": "r8", "currency": "ETH",
             "budget": 800000})  # 30+80 > 100만
        self.assertFalse(result["success"])

    def test_balance_query_failure_rejects_creation(self):
        self.fake_trader.get_account_info.side_effect = RuntimeError("api down")
        result = self.manager.create_session(self.real_profile)
        self.assertFalse(result["success"])
        self.assertIn("잔고 조회 실패", result["error"])

    def test_remove_releases_allocation(self):
        self.manager.create_session(self.real_profile)
        self.manager.remove_session("r1")
        self.assertEqual(self.manager.get_account_guard("main").total_allocated(), 0)

    def test_non_default_real_session_requires_account(self):
        profile = dict(self.real_profile)
        del profile["account"]
        result = self.manager.create_session(profile)
        self.assertFalse(result["success"])
        self.assertIn("account", result["error"])

    def test_default_legacy_real_session_skips_balance_check(self):
        profile = dict(self.real_profile)
        del profile["account"]
        profile["name"] = "default"
        self.fake_trader.get_account_info.side_effect = RuntimeError("no api")
        result = self.manager.create_session(profile)
        self.assertTrue(result["success"])
        self.assertEqual(self.manager.get_session("default").account, "legacy")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/session_manager_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'SessionManager'`

- [ ] **Step 3: 구현**

`smtm/session_manager.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .log_manager import LogManager


@dataclass
class TradingSession:
    """프로파일의 실행 인스턴스 — 자기 완결적 트레이딩 단위"""
    name: str
    profile: dict
    operator: object
    trader: object
    session_guard: object
    account: Optional[str]
    created_at: str

    @property
    def state(self):
        return self.operator.state


class SessionManager:
    """병렬 트레이딩 세션 관리자.

    세션 생성 검증(예산 합계 ≤ 실잔고, (계좌,심볼) 충돌 방지)과
    계좌별 AccountGuard 공유를 담당한다. 검증 실패 시 무부작용.
    """

    DEFAULT_SESSION = "default"
    LEGACY_ACCOUNT = "legacy"

    def __init__(self, account_store=None, llm_client=None, system_monitor=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.account_store = account_store
        self.llm_client = llm_client
        self.system_monitor = system_monitor
        self.sessions = {}        # name -> TradingSession
        self.account_guards = {}  # alias -> AccountGuard

    # ------------------------------------------------------------------
    # 생성/교체
    # ------------------------------------------------------------------
    def create_session(self, profile: dict, name=None) -> dict:
        from .profile_store import ProfileStore
        from .trader.trader_factory import TraderFactory

        name = name or profile.get("name") or self.DEFAULT_SESSION
        if name in self.sessions:
            return {"success": False, "error": f"이미 존재하는 세션입니다: {name}"}
        if not ProfileStore.NAME_PATTERN.match(str(name)):
            return {"success": False,
                    "error": "세션 이름은 영문/숫자/-/_ 1~64자여야 합니다"}

        exchange = profile.get("exchange", "UPB")
        currency = profile.get("currency", "BTC")
        budget = float(profile.get("budget", 500000))
        virtual = bool(profile.get("virtual", False))

        # --- 실거래 검증 (가상은 건너뜀) ---
        account = None
        guard_alias = None
        if not virtual:
            account_alias = profile.get("account")
            if account_alias:
                if self.account_store is None:
                    return {"success": False, "error": "계좌 저장소가 설정되지 않았습니다"}
                try:
                    account = self.account_store.load(account_alias)
                except ValueError as err:
                    return {"success": False, "error": str(err)}
                if account.get("exchange") != exchange:
                    return {"success": False,
                            "error": (f"계좌({account.get('exchange')})와 프로파일"
                                      f"({exchange})의 거래소가 일치하지 않습니다")}
                missing = self.account_store.missing_env_vars(account)
                if missing:
                    return {"success": False,
                            "error": f"키 환경변수 미설정: {', '.join(missing)}"}
                guard_alias = account_alias
            elif name == self.DEFAULT_SESSION:
                guard_alias = self.LEGACY_ACCOUNT  # 레거시 기본 env 사용
            else:
                return {"success": False,
                        "error": "실거래 세션에는 account(계좌 별칭)가 필요합니다"}

            # (계좌, 심볼) 충돌
            for session in self.sessions.values():
                if (session.account == guard_alias
                        and not session.profile.get("virtual")
                        and session.profile.get("currency", "BTC") == currency):
                    return {"success": False,
                            "error": (f"계좌 '{guard_alias}'의 {currency}은(는) "
                                      f"세션 '{session.name}'이 이미 운영 중입니다")}

        # --- Trader 생성 (실잔고 조회에 필요) ---
        trader = TraderFactory.create(
            exchange, budget=budget, currency=currency,
            paper=virtual, account=account)
        if trader is None:
            return {"success": False, "error": f"올바르지 않은 거래소 코드입니다: {exchange}"}

        if not virtual:
            account_guard = self.get_account_guard(guard_alias)
            if account is not None:  # legacy default는 실잔고 검증 생략
                try:
                    balance = float(trader.get_account_info().get("balance", 0))
                except Exception as err:
                    self._discard_trader(trader)
                    return {"success": False, "error": f"계좌 잔고 조회 실패: {err}"}
                if account_guard.total_allocated() + budget > balance:
                    self._discard_trader(trader)
                    return {"success": False,
                            "error": (f"계좌 잔고 부족: 할당 합계 "
                                      f"{account_guard.total_allocated() + budget:,.0f}"
                                      f" > 잔고 {balance:,.0f}")}
            verdict = account_guard.can_allocate(budget)
            if not verdict.allowed:
                self._discard_trader(trader)
                return {"success": False, "error": verdict.reason}

        # --- 나머지 컴포넌트 조립 ---
        # ValueError 외의 예외(예: 잘못된 safety 키로 인한 TypeError)도
        # 무부작용 보장을 위해 모두 흡수한다
        try:
            operator, session_guard = self._assemble(
                profile, name, trader,
                self.get_account_guard(guard_alias) if not virtual else None)
        except Exception as err:
            self._discard_trader(trader)
            return {"success": False, "error": str(err)}

        if not virtual:
            self.get_account_guard(guard_alias).allocate(name, budget)

        self.sessions[name] = TradingSession(
            name=name,
            profile=dict(profile),
            operator=operator,
            trader=trader,
            session_guard=session_guard,
            account=guard_alias,
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self.logger.info(f"session created: {name}")
        return {"success": True, "session": name,
                "virtual": virtual, "strategy": profile.get("strategy")}

    def _assemble(self, profile, name, trader, account_guard):
        """DataProvider/Strategy/Analyzer/Guard/TradingOperator 조립.
        실패 시 ValueError (호출부가 trader 정리)"""
        from .data.data_provider_factory import DataProviderFactory
        from .strategy.strategy_factory import StrategyFactory
        from .trading_operator import TradingOperator
        from .analyzer import Analyzer
        from .config import Config
        from .llm.safety_guard import SafetyGuard, SafetyConfig
        from .llm.account_guard import CompositeSafetyGuard

        exchange = profile.get("exchange", "UPB")
        currency = profile.get("currency", "BTC")
        budget = float(profile.get("budget", 500000))
        strategy_code = profile.get("strategy") or "BNH"

        data_provider = DataProviderFactory.create(
            exchange, currency=currency, interval=Config.candle_interval)
        if data_provider is None:
            raise ValueError(f"올바르지 않은 거래소 코드입니다: {exchange}")

        strategy = StrategyFactory.create(strategy_code, llm_client=self.llm_client)
        if strategy is None:
            raise ValueError(f"올바르지 않은 전략 코드입니다: {strategy_code}")

        analyzer = Analyzer(self.system_monitor, session_name=name)
        session_guard = SafetyGuard(SafetyConfig(
            initial_budget=budget, **profile.get("safety", {})))
        guard = session_guard
        if account_guard is not None:
            guard = CompositeSafetyGuard(session_guard, account_guard)

        operator = TradingOperator(
            interval=profile.get("term", 60), currency=currency)
        operator.initialize(
            data_provider, strategy, trader, analyzer, guard, budget=budget)
        return operator, session_guard

    def replace_session(self, name, profile) -> dict:
        """stopped 세션을 새 프로파일로 교체. 세션 가드 일일 카운터 승계.
        실패 시 기존 세션 유지."""
        old = self.sessions.get(name)
        if old is not None and old.state == "running":
            return {"success": False,
                    "error": "매매 중에는 세션을 교체할 수 없습니다. 먼저 중지하세요."}
        if old is not None:
            del self.sessions[name]
            if old.account:
                self.get_account_guard(old.account).release(name)

        result = self.create_session(profile, name=name)
        if not result.get("success"):
            if old is not None:  # 원복
                self.sessions[name] = old
                if old.account:
                    self.get_account_guard(old.account).allocate(
                        name, float(old.profile.get("budget", 500000)))
            return result

        if old is not None:
            new_guard = self.sessions[name].session_guard
            new_guard.daily_trade_count = old.session_guard.daily_trade_count
            new_guard.daily_date = old.session_guard.daily_date
        return result

    # ------------------------------------------------------------------
    # 수명 주기
    # ------------------------------------------------------------------
    def start_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state == "running":
            return {"success": False, "error": f"세션 '{name}'은 이미 매매 중입니다"}
        if not session.operator.start():
            return {"success": False, "error": f"세션 '{name}'을 시작할 수 없습니다"}
        return {"success": True, "session": name}

    def stop_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state != "running":
            return {"success": True, "note": f"세션 '{name}'은 매매 중이 아닙니다"}
        session.operator.stop()
        return {"success": True, "session": name}

    def remove_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state == "running":
            session.operator.stop()
        if session.account:
            self.get_account_guard(session.account).release(name)
        del self.sessions[name]
        return {"success": True, "removed": name}

    def stop_all(self):
        for session in list(self.sessions.values()):
            if session.state == "running":
                session.operator.stop()

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    def get_session(self, name) -> TradingSession:
        if name not in self.sessions:
            raise ValueError(f"세션을 찾을 수 없습니다: {name}")
        return self.sessions[name]

    def list_sessions(self) -> list:
        return [{
            "name": s.name,
            "state": s.state,
            "strategy": s.profile.get("strategy"),
            "account": s.account,
            "exchange": s.profile.get("exchange"),
            "currency": s.profile.get("currency"),
            "budget": s.profile.get("budget"),
            "virtual": bool(s.profile.get("virtual", False)),
        } for s in self.sessions.values()]

    def get_session_status(self, name) -> dict:
        session = self.get_session(name)
        return {
            "name": session.name,
            "state": session.state,
            "profile": dict(session.profile),
            "account": session.account,
            "created_at": session.created_at,
            "safety": session.operator.safety_guard.get_status(),
            "performance": session.operator.get_score(),
        }

    def get_performance(self, name) -> dict:
        session = self.get_session(name)
        return {"session": name, **session.operator.get_score()}

    def compare_performance(self) -> list:
        return [{
            "session": s.name,
            "state": s.state,
            "strategy": s.profile.get("strategy"),
            "virtual": bool(s.profile.get("virtual", False)),
            **s.operator.get_score(),
        } for s in self.sessions.values()]

    def get_account_guard(self, alias):
        from .llm.account_guard import AccountGuard
        if alias not in self.account_guards:
            self.account_guards[alias] = AccountGuard()
        return self.account_guards[alias]

    @staticmethod
    def _discard_trader(trader):
        """검증 실패로 버려지는 trader의 워커 정리 (무부작용 보장)"""
        worker = getattr(trader, "worker", None)
        if worker is not None:
            worker.stop()
```

`smtm/__init__.py`에 `from .session_manager import SessionManager, TradingSession` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/session_manager_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/session_manager.py smtm/__init__.py tests/unit_tests/session_manager_test.py
git commit -m "[feat] add SessionManager for parallel trading sessions with allocation guards"
```

---

### Task 7: SystemOperator 개편 — SessionManager 보유 + 레거시 위임

**Files:**
- Modify: `smtm/llm/system_operator.py`, `tests/unit_tests/system_operator_test.py`
- Test: 동일 파일

**Interfaces:**
- Consumes: `SessionManager`(Task 6), `AccountStore`(Task 1)
- Produces: `SystemOperator(llm_client, config, profile_store=None, account_store=None)` —
  - `setup()`: SessionManager 생성 + config→profile 변환으로 `"default"` 세션 자동 *생성*(시작 안 함) + Tool 등록. 생성 실패 시 `ValueError` (Controller 호환)
  - `session_manager` 속성 노출
  - 레거시 위임: `select_strategy(code)`(default stopped 필요, replace_session), `start_trading()`/`stop_trading()`(default 세션), `apply_profile(profile)`(default replace), `get_status(session=None)`(None=전체 요약: sessions/accounts/llm_usage, 지정=세션 상세)
  - `shutdown()`: `session_manager.stop_all()`
  - `_config_to_profile() -> dict`: `{name:"default", exchange, currency, budget, virtual, term:interval, strategy, strategy_params, safety, account}` (config에 있는 키만)
  - 시스템 프롬프트: 멀티 세션 지휘 역할 + 세션 요약
- 제거: `_build_trading_components`, `trading_operator`/`trader`/`data_provider`/`safety_guard` 직접 보유 (Tool 등록은 Task 10 전까지 default 세션의 컴포넌트로 임시 유지 — 아래 Step 3 참고)

- [ ] **Step 1: 기존 테스트 개정 + 신규 테스트 작성**

`tests/unit_tests/system_operator_test.py`를 다음 방침으로 수정한다:
- `make_operator`에 `AccountStore(tempfile dir)` 주입 + 기존 `DataProviderFactory.create` 스텁 패치 유지
- 기존 테스트 중 `operator.trading_operator` 참조는 `operator.session_manager.get_session("default").operator`로 치환
- `operator.strategy_code` 참조는 `operator.session_manager.get_session("default").profile.get("strategy")` 기반의 새 헬퍼 `operator.default_strategy()`로 치환 (아래 구현에 포함)
- `test_get_status_contains_key_fields`는 overview 구조로 재작성: `status["sessions"][0]["name"] == "default"`, `"llm_usage" in status` 검증으로 교체
- `tests/unit_tests/orchestration_tools_test.py`의 `test_start_stop_get_status_flow`에서 `status.data["trading_state"]` 검증을 `[s for s in status.data["sessions"] if s["name"] == "default"][0]["state"] == "running"`으로 교체
- `test_apply_profile_with_bad_safety_key_keeps_config`는 유지 — replace_session의 원복 경로가 이를 보장해야 한다 (create_session이 Exception 전체를 흡수하므로)
- `test_select_strategy_preserves_daily_trade_count`는 세션 가드 기준으로 유지:

```python
    def test_select_strategy_preserves_daily_trade_count(self):
        self.operator.session_manager.get_session("default").session_guard.record_trade({})
        self.operator.session_manager.get_session("default").session_guard.record_trade({})
        self.operator.select_strategy("RSI")
        self.assertEqual(
            self.operator.session_manager.get_session("default")
            .session_guard.daily_trade_count, 2)
```

- 신규 테스트 추가:

```python
class SystemOperatorMultiSessionTests(unittest.TestCase):
    def setUp(self):
        self.operator = make_operator()

    def tearDown(self):
        self.operator.shutdown()

    def test_setup_creates_default_session_not_started(self):
        session = self.operator.session_manager.get_session("default")
        self.assertEqual(session.state, "ready")

    def test_get_status_overview_lists_sessions(self):
        status = self.operator.get_status()
        names = [s["name"] for s in status["sessions"]]
        self.assertIn("default", names)
        self.assertIn("llm_usage", status)

    def test_get_status_with_session_returns_detail(self):
        status = self.operator.get_status(session="default")
        self.assertEqual(status["name"], "default")
        self.assertIn("safety", status)

    def test_shutdown_stops_all_running_sessions(self):
        self.operator.start_trading()
        self.operator.shutdown()
        self.assertEqual(
            self.operator.session_manager.get_session("default").state, "ready")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/system_operator_test.py -x -q`
Expected: FAIL — `AttributeError: 'SystemOperator' object has no attribute 'session_manager'`

- [ ] **Step 3: 구현**

`smtm/llm/system_operator.py` 개편 (chat/tool loop/이력/지식 로딩은 무변경):

```python
    def __init__(self, llm_client, config: dict, profile_store=None,
                 account_store=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.budget = config.get("budget", 500000)
        self.profile_store = profile_store
        self.account_store = account_store

        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )
        self.session_manager = None
        self.default_strategy_used = False

    def setup(self):
        """SessionManager 구성 + default 세션 생성 + Tool 등록. Controller가 호출."""
        from ..session_manager import SessionManager

        self.session_manager = SessionManager(
            account_store=self.account_store,
            llm_client=self.llm_client,
            system_monitor=self.system_monitor,
        )
        self.default_strategy_used = not self.config.get("strategy")
        result = self.session_manager.create_session(
            self._config_to_profile(), name=SessionManager.DEFAULT_SESSION)
        if not result.get("success"):
            raise ValueError(result.get("error"))
        self._register_tools()

    def _config_to_profile(self) -> dict:
        cfg = self.config
        profile = {"name": "default"}
        mapping = {
            "exchange": "exchange", "currency": "currency", "budget": "budget",
            "virtual": "virtual", "interval": "term", "strategy": "strategy",
            "strategy_params": "strategy_params", "safety": "safety",
            "account": "account",
        }
        for config_key, profile_key in mapping.items():
            if cfg.get(config_key) is not None:
                profile[profile_key] = cfg[config_key]
        profile.setdefault("strategy", self.DEFAULT_STRATEGY)
        return profile

    # ------------------------------------------------------------------
    # 레거시 위임 (default 세션)
    # ------------------------------------------------------------------
    def default_session(self):
        return self.session_manager.get_session("default")

    def default_strategy(self):
        try:
            return self.default_session().profile.get("strategy")
        except ValueError:
            return None

    def select_strategy(self, code: str) -> dict:
        previous = self.config.get("strategy")
        self.config["strategy"] = code
        result = self.session_manager.replace_session(
            "default", self._config_to_profile())
        if not result.get("success"):
            self.config["strategy"] = previous
            return result
        self.default_strategy_used = False
        return {"success": True, "strategy": code}

    def start_trading(self) -> dict:
        result = self.session_manager.start_session("default")
        if result.get("success") and self.default_strategy_used:
            result["strategy"] = self.default_strategy()
            result["note"] = "전략이 지정되지 않아 기본 전략(BNH)으로 시작했습니다"
        return result

    def stop_trading(self) -> dict:
        return self.session_manager.stop_session("default")

    def apply_profile(self, profile: dict) -> dict:
        result = self.session_manager.replace_session("default", profile)
        if result.get("success"):
            # config를 프로파일에 맞춰 동기화 (레거시 get_status 일관성)
            for key in ("exchange", "currency", "budget", "virtual",
                        "strategy", "strategy_params", "safety", "account"):
                if key in profile:
                    self.config[key] = profile[key]
            if "term" in profile:
                self.config["interval"] = profile["term"]
            self.budget = self.config.get("budget", self.budget)
            result["note"] = ("프로파일이 default 세션에 적용되었습니다. "
                              "매매를 재개하려면 start_trading을 호출하세요.")
        return result

    def get_status(self, session=None) -> dict:
        if session:
            try:
                return self.session_manager.get_session_status(session)
            except ValueError as err:
                return {"error": str(err)}
        return {
            "sessions": self.session_manager.list_sessions(),
            "accounts": {
                alias: guard.get_status()
                for alias, guard in self.session_manager.account_guards.items()
            },
            "llm_usage": self.system_monitor.get_llm_usage(),
        }

    def shutdown(self):
        if self.session_manager is not None:
            self.session_manager.stop_all()
```

`_register_tools`는 이 태스크에서 **최소 수정**: 읽기 Tool 4종은 default 세션의 컴포넌트로 임시 등록 (Task 10에서 세션 인식으로 리팩터):

```python
    def _register_tools(self):
        from .tools.market_data_tool import MarketDataTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        default = self.default_session()
        self.tool_router.register(MarketDataTool(default.operator.data_provider))
        self.tool_router.register(PortfolioTool(default.trader))
        self.tool_router.register(TradeHistoryTool(self.system_monitor))
        self.tool_router.register(PerformanceTool(
            self.system_monitor, default.trader, self.budget))
        # (orchestration/profile tool 등록 기존 유지)
        ...
```

주의: `select_strategy`/`apply_profile`로 default 세션이 교체되면 읽기 Tool이 구 세션을 가리킨다 — 교체 성공 후 `self._register_tools()` 재호출을 `select_strategy`/`apply_profile` 끝에 추가한다 (Task 10에서 세션 인식 리팩터로 근본 해결).

`_build_system_prompt`의 "## 현재 설정" 섹션을 세션 요약으로 교체:

```python
        parts.append("## 세션 현황")
        for s in self.session_manager.list_sessions():
            mode = "가상" if s["virtual"] else f"실거래({s['account']})"
            parts.append(
                f"- {s['name']}: {s['strategy']} / {s['exchange']} {s['currency']}"
                f" / 예산 {s['budget']:,.0f} / {mode} / 상태 {s['state']}")
```

시스템 프롬프트 도입부도 갱신:

```python
        parts = [
            "당신은 암호화폐 자동매매 시스템의 운영 에이전트입니다.",
            "직접 매매하지 않습니다. 매매는 각 세션의 전략이 고정 주기로 수행합니다.",
            "여러 세션(전략×계좌×심볼)을 병렬로 운영할 수 있습니다.",
            "제공된 Tool로 계좌를 등록하고, 프로파일로 세션을 생성·시작·중지하고,",
            "세션별 상태와 성과를 확인·비교하세요.",
            "위험한 변경(실거래 세션 시작/교체/제거)은 실행 전에 사용자에게 확인하세요.",
            "API 키 값은 절대 묻지도 저장하지도 마세요 — 환경변수 이름만 다룹니다.",
            "",
        ]
```

기존 `orchestration_tools.py`의 `GetStatusTool.execute`가 `operator.get_status()`를 인자 없이 호출하므로 그대로 호환 (session 인자는 Task 9에서).

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/system_operator_test.py tests/unit_tests/orchestration_tools_test.py tests/unit_tests/profile_tools_test.py tests/unit_tests/ -q → PASS`
(orchestration/profile tool 테스트의 `operator.strategy_code`/`trading_operator` 참조가 있으면 동일 방침으로 치환)

```bash
git add smtm/llm/system_operator.py tests/unit_tests/
git commit -m "[refactor] SystemOperator owns SessionManager with default-session legacy delegation"
```

---

### Task 8: 계좌 Tool 3종

**Files:**
- Create: `smtm/llm/tools/account_tools.py`
- Modify: `smtm/llm/system_operator.py` (`_register_tools`)
- Test: `tests/unit_tests/account_tools_test.py`

**Interfaces:**
- Produces: `register_account`(name/exchange/access_key_env/secret_key_env — 응답에 `env_ready`와 미설정 시 한국어 경고), `list_accounts`, `delete_account`(사용 중인 세션 있으면 거부). `account_store`가 None이면 3종 모두 미등록.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/account_tools_test.py`:

```python
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from smtm import AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class StubDataProvider:
    def get_info(self):
        return []


class AccountToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "virtual": True, "strategy": "BNH",
        }, account_store=AccountStore(dir_path=self.tmp.name))
        self.operator.setup()
        self.tools = self.operator.tool_router.tools

    def tearDown(self):
        self.operator.shutdown()
        self.tmp.cleanup()

    def test_account_tools_registered(self):
        for name in ("register_account", "list_accounts", "delete_account"):
            self.assertIn(name, self.tools)

    def test_register_and_list(self):
        with patch.dict(os.environ, {"SMTM_K1": "a", "SMTM_S1": "b"}):
            result = self.tools["register_account"].execute({
                "name": "main", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
            self.assertTrue(result.success)
            self.assertTrue(result.data["env_ready"])
            listing = self.tools["list_accounts"].execute({})
        self.assertEqual(listing.data["accounts"][0]["name"], "main")

    def test_register_with_unset_env_warns(self):
        result = self.tools["register_account"].execute({
            "name": "sub", "exchange": "UPB",
            "access_key_env": "SMTM_UNSET_K", "secret_key_env": "SMTM_UNSET_S"})
        self.assertTrue(result.success)
        self.assertFalse(result.data["env_ready"])
        self.assertIn("환경변수", result.data["warning"])

    def test_register_never_returns_key_values(self):
        with patch.dict(os.environ, {"SMTM_K1": "SECRET-VALUE", "SMTM_S1": "b"}):
            result = self.tools["register_account"].execute({
                "name": "main", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
        self.assertNotIn("SECRET-VALUE", str(result.data))

    def test_delete_account(self):
        self.tools["register_account"].execute({
            "name": "gone", "exchange": "UPB",
            "access_key_env": "K", "secret_key_env": "S"})
        result = self.tools["delete_account"].execute({"name": "gone"})
        self.assertTrue(result.success)
        result = self.tools["delete_account"].execute({"name": "gone"})
        self.assertFalse(result.success)

    def test_delete_account_in_use_rejected(self):
        with patch.dict(os.environ, {"SMTM_K1": "a", "SMTM_S1": "b"}):
            self.tools["register_account"].execute({
                "name": "busy", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
            fake_trader = MagicMock()
            fake_trader.get_account_info.return_value = {"balance": 10000000}
            with patch("smtm.trader.trader_factory.TraderFactory.create",
                       return_value=fake_trader):
                self.operator.session_manager.create_session({
                    "name": "r1", "exchange": "UPB", "currency": "BTC",
                    "budget": 100000, "virtual": False, "strategy": "BNH",
                    "account": "busy"})
        result = self.tools["delete_account"].execute({"name": "busy"})
        self.assertFalse(result.success)
        self.assertIn("사용 중", result.error)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/account_tools_test.py -x -q` → FAIL (Tool 미등록)

- [ ] **Step 3: 구현**

`smtm/llm/tools/account_tools.py`:

```python
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
```

`system_operator.py`의 `_register_tools` 끝에:

```python
        if self.account_store is not None:
            from .tools.account_tools import (
                RegisterAccountTool, ListAccountsTool, DeleteAccountTool,
            )
            self.tool_router.register(RegisterAccountTool(self.account_store))
            self.tool_router.register(ListAccountsTool(self.account_store))
            self.tool_router.register(DeleteAccountTool(
                self.account_store, self.session_manager))
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/account_tools_test.py -q` → PASS

```bash
git add smtm/llm/tools/account_tools.py smtm/llm/system_operator.py tests/unit_tests/account_tools_test.py
git commit -m "[feat] add account management tools with env-name-only credential policy"
```

---

### Task 9: 세션 Tool 6종 + get_status session 인자

**Files:**
- Create: `smtm/llm/tools/session_tools.py`
- Modify: `smtm/llm/system_operator.py`(`_register_tools`), `smtm/llm/tools/orchestration_tools.py`(`GetStatusTool`)
- Test: `tests/unit_tests/session_tools_test.py`

**Interfaces:**
- Produces: `create_session`(profile: 프로파일 이름 참조, session: 선택적 세션 이름 — ProfileStore에서 로드 후 SessionManager 위임), `start_session(session)`, `stop_session(session)`, `remove_session(session)`, `list_sessions`, `compare_performance`. `GetStatusTool`에 optional `session` 속성 추가. `create_session` Tool은 `profile_store`가 None이면 미등록(나머지 세션 Tool은 항상 등록).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/session_tools_test.py`:

```python
import unittest
import tempfile
from unittest.mock import patch
from smtm import ProfileStore, AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class StubDataProvider:
    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-06T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


class SessionToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.profile_store = ProfileStore(dir_path=self.tmp.name + "/profiles")
        self.operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "virtual": True, "strategy": "BNH",
        }, profile_store=self.profile_store,
           account_store=AccountStore(dir_path=self.tmp.name + "/accounts"))
        self.operator.setup()
        self.tools = self.operator.tool_router.tools
        self.profile_store.save({
            "name": "rsi-v", "exchange": "UPB", "currency": "BTC",
            "budget": 200000, "virtual": True, "strategy": "RSI"})

    def tearDown(self):
        self.operator.shutdown()
        self.tmp.cleanup()

    def test_session_tools_registered(self):
        for name in ("create_session", "start_session", "stop_session",
                     "remove_session", "list_sessions", "compare_performance"):
            self.assertIn(name, self.tools)

    def test_create_start_stop_remove_flow(self):
        result = self.tools["create_session"].execute({"profile": "rsi-v"})
        self.assertTrue(result.success)
        self.assertTrue(self.tools["start_session"].execute(
            {"session": "rsi-v"}).success)
        self.assertTrue(self.tools["stop_session"].execute(
            {"session": "rsi-v"}).success)
        self.assertTrue(self.tools["remove_session"].execute(
            {"session": "rsi-v"}).success)

    def test_create_with_custom_session_name(self):
        result = self.tools["create_session"].execute(
            {"profile": "rsi-v", "session": "exp-1"})
        self.assertTrue(result.success)
        names = [s["name"] for s in
                 self.operator.session_manager.list_sessions()]
        self.assertIn("exp-1", names)

    def test_create_with_missing_profile_fails(self):
        result = self.tools["create_session"].execute({"profile": "nope"})
        self.assertFalse(result.success)

    def test_list_sessions_and_compare(self):
        self.tools["create_session"].execute({"profile": "rsi-v"})
        listing = self.tools["list_sessions"].execute({})
        self.assertEqual(len(listing.data["sessions"]), 2)  # default + rsi-v
        compare = self.tools["compare_performance"].execute({})
        self.assertEqual(len(compare.data["performance"]), 2)

    def test_get_status_supports_session_argument(self):
        status = self.tools["get_status"].execute({"session": "default"})
        self.assertTrue(status.success)
        self.assertEqual(status.data["name"], "default")
        overview = self.tools["get_status"].execute({})
        self.assertIn("sessions", overview.data)

    def test_remove_default_session_is_allowed_but_reported(self):
        result = self.tools["remove_session"].execute({"session": "default"})
        self.assertTrue(result.success)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/session_tools_test.py -x -q` → FAIL

- [ ] **Step 3: 구현**

`smtm/llm/tools/session_tools.py`:

```python
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
```

`smtm/llm/tools/orchestration_tools.py`의 `GetStatusTool` 수정:

```python
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
```

`system_operator.py`의 `_register_tools`에 추가:

```python
        from .tools.session_tools import (
            CreateSessionTool, StartSessionTool, StopSessionTool,
            RemoveSessionTool, ListSessionsTool, ComparePerformanceTool,
        )
        self.tool_router.register(StartSessionTool(self.session_manager))
        self.tool_router.register(StopSessionTool(self.session_manager))
        self.tool_router.register(RemoveSessionTool(self.session_manager))
        self.tool_router.register(ListSessionsTool(self.session_manager))
        self.tool_router.register(ComparePerformanceTool(self.session_manager))
        if self.profile_store is not None:
            self.tool_router.register(CreateSessionTool(
                self.profile_store, self.session_manager))
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/session_tools_test.py tests/unit_tests/orchestration_tools_test.py -q` → PASS

```bash
git add smtm/llm/tools/session_tools.py smtm/llm/tools/orchestration_tools.py smtm/llm/system_operator.py tests/unit_tests/session_tools_test.py
git commit -m "[feat] add session management tools for parallel trading control"
```

---

### Task 10: 읽기 Tool 4종 세션 인식 리팩터

**Files:**
- Modify: `smtm/llm/tools/market_data_tool.py`, `portfolio_tool.py`, `performance_tool.py`, `trade_history_tool.py`, `smtm/llm/system_operator.py`(`_register_tools` + select/apply의 재등록 제거)
- Test: `tests/unit_tests/market_data_tool_test.py`, `portfolio_tool_test.py`, `performance_tool_test.py`, `trade_history_tool_test.py` (개정)

**Interfaces:**
- Produces: 4종 모두 `session` optional 인자(기본 `"default"`) —
  - `MarketDataTool(session_manager)`: execute 시 세션의 `operator.data_provider.get_info()`
  - `PortfolioTool(session_manager)`: 세션 trader의 `get_account_info()`
  - `PerformanceTool(session_manager)`: `session_manager.get_performance(session)`
  - `TradeHistoryTool(system_monitor)`: `get_trade_log(session=인자)` — session 미지정 시 전체(하위 호환), input_schema에 session 추가
- SystemOperator: 세션 교체 후 `_register_tools()` 재호출 불필요해짐 (session_manager 참조는 안정) — select/apply 끝의 재등록 제거.

- [ ] **Step 1: 기존 테스트 개정 (실패 상태로)**

각 tool 테스트에서 생성자를 새 시그니처로 바꾸고 세션 라우팅 테스트 추가. 예 — `tests/unit_tests/portfolio_tool_test.py` (기존 테스트의 검증 의미는 유지하며 아래 패턴으로 개정):

```python
class PortfolioToolSessionTests(unittest.TestCase):
    def setUp(self):
        from smtm.llm.tools.portfolio_tool import PortfolioTool
        self.manager = MagicMock()
        session = MagicMock()
        session.trader.get_account_info.return_value = {"balance": 123}
        self.manager.get_session.return_value = session
        self.tool = PortfolioTool(self.manager)

    def test_default_session_used_when_omitted(self):
        result = self.tool.execute({})
        self.manager.get_session.assert_called_with("default")
        self.assertTrue(result.success)
        self.assertEqual(result.data["balance"], 123)

    def test_explicit_session_routed(self):
        self.tool.execute({"session": "s2"})
        self.manager.get_session.assert_called_with("s2")

    def test_unknown_session_returns_error(self):
        self.manager.get_session.side_effect = ValueError("세션을 찾을 수 없습니다: x")
        result = self.tool.execute({"session": "x"})
        self.assertFalse(result.success)
```

MarketDataTool/PerformanceTool도 동일 패턴 (PerformanceTool은 `manager.get_performance` 위임 검증). TradeHistoryTool은 `system_monitor.get_trade_log(session=...)` 호출 검증.

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/portfolio_tool_test.py tests/unit_tests/market_data_tool_test.py tests/unit_tests/performance_tool_test.py tests/unit_tests/trade_history_tool_test.py -q` → FAIL

- [ ] **Step 3: 구현**

각 Tool의 공통 패턴 (PortfolioTool 예 — 나머지도 동일 구조):

```python
class PortfolioTool(Tool):
    name = "get_portfolio"
    description = "세션의 포트폴리오(잔고/자산/시세)를 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"session": {"type": "string",
                                   "description": "세션 이름 (기본 default)"}},
    }

    def __init__(self, session_manager):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.session_manager = session_manager

    def execute(self, arguments: dict) -> ToolResult:
        try:
            session = self.session_manager.get_session(
                arguments.get("session") or "default")
            return ToolResult(success=True,
                              data=session.trader.get_account_info())
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        except Exception as e:
            self.logger.error(f"PortfolioTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- `MarketDataTool(session_manager)`: `session.operator.data_provider.get_info()`. 기존 description의 데이터 타입 설명은 유지하되, **input_schema는 session만 남기고 기존 `currency` 필드는 제거**한다 (DataProvider가 세션에 고정되므로 무의미). market_data_tool_test에서 currency 관련 검증이 있으면 세션 라우팅 검증으로 교체.
- `PerformanceTool(session_manager)`: `self.session_manager.get_performance(name)` 반환
- `TradeHistoryTool(system_monitor)`: 생성자 유지, execute에서 `self.system_monitor.get_trade_log(session=arguments.get("session"))` (미지정 시 None → 전체)

`system_operator.py` `_register_tools`의 읽기 4종 등록을:

```python
        self.tool_router.register(MarketDataTool(self.session_manager))
        self.tool_router.register(PortfolioTool(self.session_manager))
        self.tool_router.register(TradeHistoryTool(self.system_monitor))
        self.tool_router.register(PerformanceTool(self.session_manager))
```

그리고 Task 7에서 select_strategy/apply_profile 끝에 넣었던 `self._register_tools()` 재호출을 제거한다 (session_manager 참조는 세션 교체와 무관하게 안정).

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/ -q` → PASS (E2E는 Task 12에서)

```bash
git add smtm/llm/tools/ smtm/llm/system_operator.py tests/unit_tests/
git commit -m "[refactor] make read-only tools session-aware via SessionManager"
```

---

### Task 11: Controller / JPT / Telegram 배선

**Files:**
- Modify: `smtm/controller/controller.py`, `smtm/controller/jpt_controller.py`, `smtm/controller/telegram/telegram_controller.py`
- Test: 기존 컨트롤러 관련 테스트 있으면 개정, 없으면 import 스모크

**Interfaces:**
- Controller: `SystemOperator(..., profile_store=ProfileStore(), account_store=AccountStore())` 주입. `_terminate`에서 `operator.stop_trading()` → `operator.shutdown()`. 초기화 배너에 "멀티 세션" 안내 한 줄.
- JPT/Telegram: 동일하게 `account_store=AccountStore()` 주입, 종료 경로 `shutdown()`.
- **Telegram 부팅 자동 시작 제거**: `telegram_controller.py`의 `self.operator.start_trading()` 호출 삭제 — "start" 메시지로만 시작 (스펙 3.9).

- [ ] **Step 1: Telegram 자동 시작 제거 + 배선**

`telegram_controller.py`: `setup()` 다음 줄의 `self.operator.start_trading()` 삭제, 시작 안내 메시지를 "'start'를 입력하면 default 세션 매매가 시작됩니다"로 변경. `SystemOperator` 생성에 `account_store=AccountStore()` 추가 (import 포함). 종료 경로의 `stop_trading()`을 `shutdown()`으로.

`controller.py`: `AccountStore` import + 주입, `_terminate`의 `operator.stop_trading()` → `operator.shutdown()`, 배너에 `print("멀티 세션 지원 — 채팅으로 계좌 등록·세션 생성/시작이 가능합니다")` 추가.

`jpt_controller.py`: 동일 주입 + 종료 경로 `shutdown()`.

- [ ] **Step 2: 검증**

Run: `python -m pytest tests/unit_tests/ -q` → PASS
Run: `python -c "import smtm.__main__; from smtm.controller.telegram.telegram_controller import TelegramController; import inspect; src=inspect.getsource(TelegramController); assert 'start_trading()' not in src.split('def main')[1].split('def ')[0], 'autostart remains'; print('ok')"`
Expected: `ok` (main 경로에 자동 시작 없음)

- [ ] **Step 3: 커밋**

```bash
git add smtm/controller/
git commit -m "[feat] wire account store and session shutdown through controllers, remove telegram autostart"
```

---

### Task 12: E2E 멀티 세션 시나리오 + README 갱신

**Files:**
- Modify: `tests/e2e_tests/e2e_chat_trading_test.py` (시나리오 추가 + 기존 시나리오 유지 확인), `README.md`, `README-ko-kr.md`
- Test: `tests/e2e_tests/`

**Interfaces:**
- Consumes: 전체 스택 (FakeLlmClient/FakeDataProvider 재사용)

- [ ] **Step 1: E2E 추가**

기존 `make_operator`를 `account_store=AccountStore(tempfile dir)` 주입으로 확장(기존 테스트는 default 세션 위임으로 그대로 통과해야 함 — 깨지면 위임 버그이므로 수정 대상). 파일 끝에 추가:

```python
class MultiSessionE2ETest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.profile_store = ProfileStore(dir_path=self.tmp.name + "/p")
        self.account_store = AccountStore(dir_path=self.tmp.name + "/a")

    def tearDown(self):
        self.tmp.cleanup()

    def _operator(self, responses=None):
        llm = FakeLlmClient(responses)
        operator = SystemOperator(llm, {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "interval": 60, "virtual": True, "strategy": "BNH",
        }, profile_store=self.profile_store, account_store=self.account_store)
        operator.setup()
        # 모든 세션의 data_provider를 Fake로 교체하는 대신 factory 스텁 사용
        return operator, llm

    def test_chat_two_virtual_sessions_and_compare(self):
        """채팅: 프로파일 생성 → 세션 2개 기동 → 각자 틱 → 성과 비교"""
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="create_profile", arguments={
                    "name": "bnh-v", "strategy": "BNH", "virtual": True,
                    "budget": 300000})]),
            LlmResponse(text="프로파일 생성"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="create_session",
                         arguments={"profile": "bnh-v"})]),
            LlmResponse(text="세션 생성"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t3", name="start_session",
                         arguments={"session": "bnh-v"})]),
            LlmResponse(text="세션 시작"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t4", name="compare_performance", arguments={})]),
            LlmResponse(text="성과 비교 결과입니다"),
        ]
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()):
            operator, llm = self._operator(responses)
            self.addCleanup(operator.shutdown)
            operator.chat("BNH 가상 프로파일 만들어줘")
            operator.chat("그걸로 세션 만들어줘")
            operator.chat("세션 시작해줘")
            manager = operator.session_manager
            self.assertEqual(manager.get_session("bnh-v").state, "running")
            # default 세션과 신규 세션이 공존
            self.assertEqual(len(manager.list_sessions()), 2)
            # start가 워커에 첫 틱을 post하므로 폴링으로 첫 체결 대기
            # (interval=60 → 두 번째 틱 없음, 수동 틱 호출 금지: 이중 주문 경합)
            trader = manager.get_session("bnh-v").trader
            deadline = time.time() + 5
            while time.time() < deadline and len(trader.order_history) == 0:
                time.sleep(0.05)
            self.assertEqual(len(trader.order_history), 1)
            self.assertEqual(
                len(manager.get_session("default").trader.order_history), 0)
            reply = operator.chat("성과 비교해줘")
            self.assertIn("성과", reply)

    def test_legacy_default_flow_still_works(self):
        """기존 start_trading/stop_trading 경로가 default 세션으로 동작"""
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()):
            operator, _ = self._operator()
            self.addCleanup(operator.shutdown)
            self.assertTrue(operator.start_trading()["success"])
            self.assertEqual(
                operator.session_manager.get_session("default").state, "running")
            self.assertTrue(operator.stop_trading()["success"])

    def test_account_registration_never_leaks_key_values(self):
        """계좌 등록 대화 전 구간에 키 값이 등장하지 않는다"""
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="register_account", arguments={
                    "name": "main", "exchange": "UPB",
                    "access_key_env": "SMTM_E2E_K",
                    "secret_key_env": "SMTM_E2E_S"})]),
            LlmResponse(text="계좌가 등록되었습니다"),
        ]
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()), \
             patch.dict(os.environ, {"SMTM_E2E_K": "TOP-SECRET-KEY",
                                     "SMTM_E2E_S": "TOP-SECRET-2"}):
            operator, llm = self._operator(responses)
            self.addCleanup(operator.shutdown)
            operator.chat("main 계좌 등록해줘")
            # Tool 결과/대화 이력 어디에도 키 값 없음
            self.assertNotIn("TOP-SECRET", str(operator.conversation_history))
            self.assertNotIn("TOP-SECRET",
                             str(operator.system_monitor.tool_call_log))
```

필요 import(`os`, `time`, `tempfile`, `patch`, `AccountStore`)를 파일 상단에 추가.

- [ ] **Step 2: 전체 테스트 확인**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -q`
Expected: 전체 PASS

- [ ] **Step 3: README 갱신**

`README.md`/`README-ko-kr.md`에 멀티 세션 섹션 추가 (아키텍처 설명 근처):

```markdown
### Multi-Session Parallel Trading

Run multiple strategies across accounts and symbols in parallel — all
controlled by chatting with the agent:

- Register accounts by env-var *names* (`SMTM_KEY_1`...), never raw keys
- Create profiles (strategy × exchange × symbol × budget × account)
- `create_session` / `start_session` / `compare_performance` via chat
- Per-session budgets are validated against the real account balance,
  and an account-level guard caps daily trades across sessions
```

(한국어 README에 동일 내용 한국어로. 기존 사용법 문구 중 "단일" 전제가 명백히 틀려지는 문장이 있으면 최소 수정.)

- [ ] **Step 4: 커밋**

```bash
git add tests/e2e_tests/ README.md README-ko-kr.md
git commit -m "[test] add multi-session E2E scenarios and document parallel trading"
```

---

## 완료 기준 (Definition of Done)

1. `python -m pytest tests/unit_tests/ tests/e2e_tests/ -q` 전체 통과 (유닛 테스트 실 네트워크 0회)
2. `python -m smtm --mode 0 --strategy BNH --virtual` 부팅 스모크 정상 (default 세션 생성)
3. 스펙 7.1 In-Scope 전 항목 커버: AccountStore+계좌 Tool(T1,T8) / Trader 주입+cancel 보장(T2) / 프로파일 account(T4) / AccountGuard+Composite(T3) / SessionManager+검증(T6) / 세션 Tool+레거시 위임(T7,T9) / SystemMonitor 태깅(T5) / Telegram autostart 제거(T11)
4. 키 원문 비노출 E2E 검증 통과 (T12)
5. 레거시 플로우(start/stop/select/switch_profile, CLI 부팅) 완전 호환
