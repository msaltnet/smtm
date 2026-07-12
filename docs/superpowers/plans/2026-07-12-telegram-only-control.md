# 텔레그램 전용 제어 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실행 진입점을 텔레그램 챗봇 하나로 좁히고, 그 과정에서 드러난 두 결함(텔레그램에서 CLI 플래그가 무시됨 / 가상거래 세션을 만들 수 없음)을 함께 고친다.

**Architecture:** `smtm/controller/controller.py`(CLI 인터랙티브)를 삭제하고 `__main__.py`를 텔레그램 전용 진입점으로 축소한다. `TelegramController`에 `ProfileStore`를 주입해 프로파일·세션 Tool이 등록되게 하고, default 세션의 부팅 기본값을 가상거래로 바꾼다. 설정은 CLI 플래그가 아니라 채팅(계좌 등록·프로파일·세션 생성 Tool)으로 한다.

**Tech Stack:** Python 3, argparse, unittest + pytest, Anthropic Claude SDK

**Spec:** [docs/superpowers/specs/2026-07-12-telegram-only-control-design.md](../specs/2026-07-12-telegram-only-control-design.md)

---

## File Structure

| 파일 | 변경 | 책임 |
|---|---|---|
| `smtm/controller/telegram/telegram_controller.py` | 수정 | `ProfileStore` 주입, 가상거래 기본값, 부팅 안내 |
| `smtm/__main__.py` | 대폭 축소 | 텔레그램 전용 진입점. 플래그 4개만 |
| `smtm/controller/controller.py` | **삭제** | (CLI 인터랙티브 컨트롤러) |
| `smtm/__init__.py` | 수정 | `Controller` export 제거 |
| `config/virtual-upbit.json` | **삭제** | (`--config`가 사라져 무의미) |
| `tests/unit_tests/telegram_controller_test.py` | **신규** | Tool 등록·가상거래 기본값 검증 |
| `tests/unit_tests/main_args_test.py` | **신규** | 인자 파서 검증 (`main_config_test.py` 대체) |
| `tests/unit_tests/main_config_test.py` | **삭제** | config 병합 대상이 사라짐 |
| `README.md`, `README-ko-kr.md` | 수정 | 실행 방법·옵션표·기능 목록 |
| `docs/public/architecture.md`, `docs/wiki/architecture.md` | 수정 | Presentation 계층에서 CLI Controller 제거 |

**작업 순서 근거:** Task 1(텔레그램 결함 수정)을 먼저 한다. CLI를 먼저 지우면 그 사이 가상거래 진입 수단이 없는 상태가 되기 때문이다. 결함을 고친 뒤 CLI를 제거한다.

---

### Task 1: TelegramController에 ProfileStore 주입 + 가상거래 기본값

텔레그램은 `SystemOperator`에 `profile_store`를 넘기지 않아 프로파일 Tool 6종과 `create_session` Tool이 등록되지 않는다([system_operator.py:104](../../../smtm/llm/system_operator.py#L104), [:134](../../../smtm/llm/system_operator.py#L134)의 `if self.profile_store is not None:` 가드). 그래서 `virtual`을 지정할 통로가 없고 default 세션은 실거래로 고정된다. 이 Task가 그 두 가지를 고친다.

**Files:**
- Create: `tests/unit_tests/telegram_controller_test.py`
- Modify: `smtm/controller/telegram/telegram_controller.py:31-57`

- [ ] **Step 1: 실패하는 테스트 작성**

`TelegramController.main()`은 `signal.signal()`을 호출하고 폴링 루프를 도는 실행 메서드다. 테스트에서 전체를 돌릴 수 없으므로, `main()`이 만드는 `SystemOperator`를 가로채서 검사한다. `TelegramMessageHandler`는 토큰 검증과 네트워크를 하므로 패치하고, `SessionManager`가 실제 거래소로 틱을 보내지 않도록 `DataProviderFactory.create`도 패치한다 (기존 `system_operator_test.py`의 `setUpModule` 패턴과 동일).

`tests/unit_tests/telegram_controller_test.py`를 새로 만든다:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from smtm.controller.telegram.telegram_controller import TelegramController
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubDataProvider:
    """실 네트워크 호출 없이 고정 캔들을 반환하는 테스트용 DataProvider"""

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-12T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class TelegramControllerSetupTests(unittest.TestCase):
    """main()이 조립하는 SystemOperator의 Tool 등록과 세션 기본값을 검증한다.

    main()은 signal 등록과 무한 폴링 루프를 돌기 때문에 그대로 실행할 수 없다.
    폴링을 즉시 끝내도록 message_handler를 스텁으로 바꾸고, operator만 꺼내 본다.
    """

    def setUp(self):
        self.patchers = [
            patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                  side_effect=lambda *a, **k: StubDataProvider()),
            patch("smtm.controller.telegram.telegram_controller.ClaudeLlmClient",
                  side_effect=lambda *a, **k: StubLlmClient()),
            patch("smtm.controller.telegram.telegram_controller.TelegramMessageHandler"),
            patch.dict(os.environ, {"SMTM_LLM_API_KEY": "test-key"}),
        ]
        for patcher in self.patchers:
            patcher.start()
        # 프로파일/계좌가 실제 config/ 디렉터리를 건드리지 않도록 격리
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for patcher in self.patchers:
            self.addCleanup(patcher.stop)

    def _run_main(self):
        controller = TelegramController(token="t", chat_id="c")
        # start_polling 직후 terminating=True가 되어 while 루프를 즉시 빠져나온다
        controller.message_handler.terminating = True
        with patch("signal.signal"):
            controller.main()
        return controller.operator

    def test_profile_and_session_tools_are_registered(self):
        operator = self._run_main()

        tool_names = set(operator.tool_router.tools.keys())
        self.assertIn("create_profile", tool_names)
        self.assertIn("create_session", tool_names)
        self.assertIn("switch_profile", tool_names)

    def test_default_session_is_virtual(self):
        operator = self._run_main()

        session = operator.default_session()
        self.assertTrue(session.profile["virtual"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

Run: `python -m pytest tests/unit_tests/telegram_controller_test.py -v`

Expected: 두 테스트 모두 FAIL.
- `test_profile_and_session_tools_are_registered` → `create_profile`이 등록되지 않아 `AssertionError`
- `test_default_session_is_virtual` → default 세션 프로파일의 `virtual`이 `False`라 `AssertionError`

참고로 `ToolRouter.tools`는 `Dict[str, Tool]`(이름 → Tool)이고 `TradingSession.profile`은 dict이므로 위 테스트의 접근 방식이 맞다.

- [ ] **Step 3: 구현 — ProfileStore 주입 + virtual 기본값**

[smtm/controller/telegram/telegram_controller.py](../../../smtm/controller/telegram/telegram_controller.py)에서:

import에 `ProfileStore` 추가 (`AccountStore` import 옆):

```python
from ...account_store import AccountStore
from ...profile_store import ProfileStore
```

`main()`의 config에서 `"virtual": False`를 `True`로 바꾸고, `SystemOperator` 생성에 `profile_store`를 넘긴다:

```python
        llm_client = ClaudeLlmClient(api_key=api_key)
        config = {
            "exchange": exchange,
            "currency": currency,
            "budget": budget,
            "interval": Config.candle_interval,
            "virtual": True,
            "strategy": "BNH",
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        self.operator = SystemOperator(llm_client, config,
                                       profile_store=ProfileStore(),
                                       account_store=AccountStore())
```

부팅 안내 메시지도 바꾼다 (기존 `print("'start'를 입력하면 default 세션 매매가 시작됩니다")` 자리):

```python
        print("'start'를 입력하면 default 세션 매매가 시작됩니다")
        print("default 세션은 가상거래입니다 — 실제 주문은 전송되지 않습니다")
        print("실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요")
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인**

Run: `python -m pytest tests/unit_tests/telegram_controller_test.py -v`
Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add smtm/controller/telegram/telegram_controller.py tests/unit_tests/telegram_controller_test.py
git commit -m "[fix] register profile/session tools on telegram and default to paper trading"
```

---

### Task 2: `--mode`와 CLI 컨트롤러 제거, 진입점을 텔레그램 전용으로 축소

**Files:**
- Create: `tests/unit_tests/main_args_test.py`
- Delete: `tests/unit_tests/main_config_test.py`
- Modify: `smtm/__main__.py` (전면 재작성)
- Delete: `smtm/controller/controller.py`
- Modify: `smtm/__init__.py:52,74`
- Delete: `config/virtual-upbit.json`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/main_args_test.py`를 새로 만든다:

```python
import unittest

from smtm.__main__ import parse_args


class MainArgsTests(unittest.TestCase):
    def test_token_and_chatid_are_parsed(self):
        args = parse_args(["--token", "my-token", "--chatid", "1234"])

        self.assertEqual(args.token, "my-token")
        self.assertEqual(args.chatid, "1234")

    def test_log_is_parsed(self):
        args = parse_args(["--log", "smtm.log"])

        self.assertEqual(args.log, "smtm.log")

    def test_defaults_are_none(self):
        args = parse_args([])

        self.assertIsNone(args.token)
        self.assertIsNone(args.chatid)
        self.assertIsNone(args.log)

    def test_removed_flags_are_rejected(self):
        # CLI 인터랙티브 모드가 사라지면서 함께 제거된 플래그들
        for argv in (
            ["--mode", "0"],
            ["--config", "config/whatever.json"],
            ["--budget", "500000"],
            ["--currency", "BTC"],
            ["--exchange", "UPB"],
            ["--term", "60"],
            ["--strategy", "RSI"],
            ["--profile", "my-profile"],
            ["--virtual"],
            ["--paper"],
        ):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    parse_args(argv)


class ControllerExportTests(unittest.TestCase):
    def test_cli_controller_is_gone(self):
        import smtm

        self.assertFalse(hasattr(smtm, "Controller"))
        self.assertNotIn("Controller", smtm.__all__)
        # 텔레그램과 주피터 컨트롤러는 유지된다
        self.assertTrue(hasattr(smtm, "TelegramController"))
        self.assertTrue(hasattr(smtm, "JptController"))


if __name__ == "__main__":
    unittest.main()
```

`parse_args`가 이제 `(parser, args)` 튜플이 아니라 `args` 하나만 반환한다는 점에 유의 — 병합할 config가 없으므로 parser를 돌려줄 이유가 사라진다.

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

Run: `python -m pytest tests/unit_tests/main_args_test.py -v`

Expected: FAIL.
- `test_token_and_chatid_are_parsed` → `parse_args`가 튜플을 반환하므로 `AttributeError: 'tuple' object has no attribute 'token'`
- `test_removed_flags_are_rejected` → `--mode 0` 등이 아직 유효해서 `SystemExit`이 안 남
- `test_cli_controller_is_gone` → `smtm.Controller`가 아직 존재

- [ ] **Step 3: `smtm/__main__.py` 재작성**

[smtm/__main__.py](../../../smtm/__main__.py) 전체를 아래로 교체한다. `DEFAULT_MODE`, `DEFAULT_CONFIG`, `CONFIG_ALIASES`, `load_config()`, `merge_config()`, `Controller` import가 모두 사라진다.

```python
import argparse
from argparse import RawTextHelpFormatter
import sys

from .controller.telegram import TelegramController
from .log_manager import LogManager
from .__init__ import __version__


def build_parser():
    parser = argparse.ArgumentParser(
        description="""
smtm - AI Agent 기반 암호화폐 자동매매 시스템

텔레그램 챗봇으로 제어합니다. 예산·전략·거래소 등 설정은 채팅으로 합니다.
default 세션은 가상거래로 시작하며, 실거래는 채팅으로 계좌를 등록한 뒤
세션을 만들어 시작합니다.

Example)
python -m smtm --token <telegram-bot-token> --chatid <chat-id>
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument("--token", help="telegram chat-bot token", default=None)
    parser.add_argument("--chatid", help="telegram chat id", default=None)
    parser.add_argument("--log", help="log file name", default=None)
    parser.add_argument(
        "--version", action="version", version=f"smtm version: {__version__}"
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.log is not None:
        LogManager.change_log_file(args.log)

    try:
        controller = TelegramController(token=args.token, chat_id=args.chatid)
    except ValueError:
        print("Please check your telegram chat-bot token")
        sys.exit(0)
    controller.main()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: CLI 컨트롤러 삭제와 export 제거**

```bash
git rm smtm/controller/controller.py config/virtual-upbit.json tests/unit_tests/main_config_test.py
```

[smtm/__init__.py](../../../smtm/__init__.py)에서 두 줄을 지운다:

52번 줄:
```python
from .controller.controller import Controller
```

`__all__`의 74번 줄:
```python
    "Controller",
```

`JptController`와 `TelegramController` import/export는 그대로 둔다.

- [ ] **Step 5: 테스트를 실행해 통과를 확인**

Run: `python -m pytest tests/unit_tests/main_args_test.py -v`
Expected: 4 passed

전체 스위트로 회귀를 확인한다 (통합 테스트는 실 네트워크를 쓰므로 제외):

Run: `python -m pytest tests/unit_tests tests/e2e_tests tests/strategy_tests -q`
Expected: 전부 통과. 실패한다면 `Controller`나 `parse_args`의 옛 시그니처를 참조하는 곳이 남은 것이므로 `git grep -n "Controller\b" -- smtm tests`와 `git grep -n "parse_args" -- smtm tests`로 찾아 고친다.

- [ ] **Step 6: 커밋**

```bash
git add smtm/__main__.py smtm/__init__.py tests/unit_tests/main_args_test.py
git commit -m "[feat] drop CLI interactive mode; telegram is the only entry point"
```

---

### Task 3: 문서 갱신

**Files:**
- Modify: `README.md`
- Modify: `README-ko-kr.md`
- Modify: `docs/public/architecture.md:48`
- Modify: `docs/wiki/architecture.md:7,29`

- [ ] **Step 1: README 2종 갱신**

두 README에서 다음을 고친다. (줄 번호는 현재 기준이며, Task 1·2를 거치며 밀릴 수 있으니 문자열로 찾는다.)

**기능 목록** — CLI 언급 제거:
- `README-ko-kr.md`: `- CLI 인터랙티브 모드 및 텔레그램 챗봇 제어` → `- 텔레그램 챗봇 제어`
- `README.md`: `- CLI interactive mode and Telegram chatbot control` → `- Telegram chatbot control`

**실행 방법 섹션** — `--mode 0` CLI 실행 예제와 그 설명을 통째로 삭제하고, 텔레그램 실행만 남긴다. 명령은 이제 `--mode 1` 없이:

```bash
python -m smtm --token <telegram-bot-token> --chatid <chat-id>
```

`python -m smtm --mode 0 --strategy LLM --virtual` 같은 전략/가상거래 예제도 삭제한다 — 해당 플래그가 사라졌다. 대신 다음을 안내한다: default 세션은 가상거래로 시작하고, 전략 변경과 실거래 전환은 채팅으로 한다.

**옵션 표** — 남은 4개만:

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--token` | 텔레그램 챗봇 토큰 | 없음 (필수) |
| `--chatid` | 텔레그램 chat id | 없음 (필수) |
| `--log` | 로그 파일 이름 | 없음 |
| `--version` | 버전 출력 | — |

영문판도 같은 내용으로.

**가상거래 안내 추가** — 실행 방법 섹션에 한 문단:

> default 세션은 가상거래(모의투자)로 시작하므로 실제 주문이 전송되지 않습니다. 실거래를 하려면 채팅으로 계좌를 등록하고(`register_account`), 실거래 프로파일을 만든 뒤 세션을 생성해 시작하세요.

**아키텍처 컴포넌트 목록** — `Controller`(CLI) 항목이 있으면 삭제한다.

- [ ] **Step 2: architecture 문서 갱신**

[docs/public/architecture.md:48](../../../docs/public/architecture.md#L48)의 Presentation 계층 표:

```
| Presentation | 사용자 입력·출력 | `Controller`(CLI), `TelegramController`, `JptController` |
```
→
```
| Presentation | 사용자 입력·출력 | `TelegramController`, `JptController` |
```

같은 파일의 mermaid 다이어그램(17·29·30줄 근처)에 `Controller[Controller\n사용자 입력 루프]` 노드와 `User --> Controller`, `Controller --> Operator` 엣지가 있다. 이를 `TelegramController`로 바꾼다:

```
    Controller[TelegramController\n채팅 입력 루프]
```

156·162·179줄 근처의 시퀀스 다이어그램도 `participant C as Controller` → `participant C as TelegramController`, `M->>C: new Controller(args)` → `M->>C: new TelegramController(token, chatid)`로 고친다.

267줄의 `4. Controller 생성 부분에서 ClaudeLlmClient 대신 해당 어댑터 인스턴스화.` → `4. TelegramController 생성 부분에서 ...`

[docs/wiki/architecture.md](../../../docs/wiki/architecture.md)의 7·29줄:
```
| Controller Layer | Simulator, Controller, TelegramController| User Interface |
```
→
```
| Controller Layer | TelegramController, JptController | User Interface |
```

`RELEASE_NOTES.md`와 `docs/superpowers/` 아래의 과거 스펙·플랜은 이력 문서이므로 수정하지 않는다.

- [ ] **Step 3: 문서에 죽은 참조가 남았는지 확인**

Run: `git grep -n -- "--mode" -- README.md README-ko-kr.md docs/public docs/wiki`
Expected: 출력 없음

Run: `git grep -n "mode 0\|mode 1\|virtual-upbit" -- README.md README-ko-kr.md docs/public docs/wiki`
Expected: 출력 없음

- [ ] **Step 4: 커밋**

```bash
git add README.md README-ko-kr.md docs/public/architecture.md docs/wiki/architecture.md
git commit -m "[docs] document telegram-only control and paper-trading default"
```

---

### Task 4: 최종 검증

- [ ] **Step 1: 전체 테스트**

Run: `python -m pytest tests/unit_tests tests/e2e_tests tests/strategy_tests -q`
Expected: 전부 통과, 실패 0

- [ ] **Step 2: 진입점이 실제로 동작하는지 확인**

Run: `python -m smtm --help`
Expected: `--token`, `--chatid`, `--log`, `--version`만 보이고 `--mode`/`--config`/`--budget`은 없다.

Run: `python -m smtm --version`
Expected: `smtm version: 2.0.0`

Run: `python -m smtm`
Expected: 토큰이 없으므로 `Please check your telegram chat-bot token` 출력 후 종료 (traceback 없이).

- [ ] **Step 3: 죽은 참조 최종 스캔**

Run: `git grep -n "controller.controller\|from .controller.controller\|smtm.Controller" -- smtm tests`
Expected: 출력 없음

Run: `git grep -rn "DEFAULT_CONFIG\|CONFIG_ALIASES\|merge_config\|load_config" -- smtm tests`
Expected: 출력 없음
