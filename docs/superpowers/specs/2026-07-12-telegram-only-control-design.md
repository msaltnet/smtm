# 텔레그램 전용 제어 — 설계

- 날짜: 2026-07-12
- 상태: 승인됨

## 1. 배경과 목적

smtm은 현재 세 개의 제어 표면을 가진다.

| 표면 | 진입점 | 상태 |
|---|---|---|
| CLI 인터랙티브 (`Controller`) | `python -m smtm --mode 0` | 제거 대상 |
| 텔레그램 챗봇 (`TelegramController`) | `python -m smtm --mode 1` | 유일한 진입점으로 남김 |
| Jupyter (`JptController`) | 노트북에서 직접 import | 유지 (진입점 밖, 개발용) |

목적은 **실행 진입점을 텔레그램 챗봇 하나로 좁히고, 그 과정에서 드러난 두 개의 실제 결함을 고치는 것**이다.

### 조사에서 드러난 기존 결함

이 작업은 단순 삭제가 아니다. 코드를 확인한 결과 두 가지가 이미 깨져 있다.

**결함 1 — 텔레그램 모드에서 CLI 플래그가 전부 무시된다.**
[`__main__.py`](../../../smtm/__main__.py)는 `--mode 1`에서 `TelegramController(token, chat_id)`를 만들고 `tcb.main()`을 인자 없이 호출한다. 그런데 `TelegramController.main(exchange="UPB", currency="BTC", budget=500000)`은 기본값을 쓰고 `virtual=False`, `strategy="BNH"`, `interval=Config.candle_interval`을 하드코딩한다. 따라서 `--budget`, `--currency`, `--exchange`, `--term`, `--strategy`, `--paper`, `--profile`, `--config`는 파싱된 뒤 버려진다.

**결함 2 — 텔레그램에서는 가상거래 세션을 만들 수 없다.**
`TelegramController`는 `SystemOperator`에 `profile_store`를 주입하지 않는다. `SystemOperator._register_tools()`는 프로파일 Tool 6종과 `create_session` Tool을 `if self.profile_store is not None:` 가드 뒤에 등록한다. 결과적으로 텔레그램 세션에는 다음 Tool이 **등록되지 않는다**:

- `list_profiles`, `describe_profile`, `create_profile`, `update_profile`, `delete_profile`, `switch_profile`
- `create_session`

`virtual` 값을 지정할 수 있는 유일한 통로가 프로파일이므로, 텔레그램 사용자는 **가상거래 세션을 만들 방법이 없고 default 세션은 `virtual: False`로 고정**된다. 즉 텔레그램은 현재 실거래 전용이다.

CLI를 제거하면 텔레그램이 유일한 진입점이 되므로, 이 두 결함은 선택이 아니라 필수 수정 사항이 된다.

## 2. 설계 결정

### D1. CLI 컨트롤러를 삭제한다 (숨기지 않는다)

`smtm/controller/controller.py`를 삭제하고 `smtm/__init__.py`의 export도 제거한다. 진입점에서만 연결을 끊고 파일을 남기는 방식은 데드 코드를 만들고, 다음 사람이 "이게 살아있는 경로인가"를 매번 판단해야 한다. git 히스토리에 남으므로 되살리기도 어렵지 않다.

`JptController`는 남긴다. `--mode`와 무관하게 노트북에서 직접 import되는 개발용 도구이며, 실행 진입점이 아니다.

### D2. 부팅 기본값을 가상거래로 바꾼다

default 세션의 `virtual`을 **`True`**로 한다. 실거래는 사용자가 채팅으로 명시적 절차(계좌 등록 → 프로파일 생성 → 세션 생성)를 거쳐야만 가능하다.

근거: `--paper` 플래그가 사라지면 부팅 시점에 가상/실거래를 고르는 수단이 없다. 그 상태에서 기본값이 실거래이면 봇을 켜는 것만으로 실주문 경로가 열린다. 트레이딩 시스템에서 안전한 기본값은 가상거래다.

이것은 **동작 변경**이다. 기존에 `--mode 1`로 실거래를 운영하던 사용자는 부팅 후 채팅으로 실거래 세션을 만들어야 한다.

### D3. 텔레그램에 `profile_store`를 주입한다

`TelegramController`가 `SystemOperator`에 `profile_store=ProfileStore()`를 넘긴다. 이것만으로 프로파일 Tool 6종과 `create_session` Tool이 등록되어 결함 2가 해소된다.

`ProfileStore`는 이미 `save()`에서 `os.makedirs(exist_ok=True)`를 호출하고 `list_profiles()`는 디렉터리가 없으면 `[]`를 반환한다. 따라서 `config/profiles/` 디렉터리가 없어도 별도 보강이 필요 없다.

### D4. CLI 플래그를 정리한다

`--mode 1`에서 어차피 무시되던 플래그들을 제거한다. 설정은 채팅(계좌 등록·프로파일·세션 생성 Tool)으로 한다 — 이미 존재하는 정식 통로다.

| 제거 | 유지 |
|---|---|
| `--mode` | `--token` |
| `--config` | `--chatid` |
| `--profile` | `--log` |
| `--budget` | `--version` |
| `--currency` | |
| `--exchange` | |
| `--term` | |
| `--strategy` | |
| `--paper` / `--virtual` | |

이에 따라 `DEFAULT_CONFIG`, `CONFIG_ALIASES`, `load_config()`, `merge_config()`가 모두 불필요해진다. `config/virtual-upbit.json`도 삭제한다.

`--config`가 사라지므로 "config JSON의 `mode` 키를 어떻게 할 것인가"라는 질문 자체가 소멸한다.

### D5. 토큰/챗ID 누락 처리

현재 `TelegramController(token=None, chat_id=None)`은 `ValueError`를 던지고 `__main__`이 안내 메시지를 출력한다. 이 동작을 유지한다. 텔레그램이 유일한 진입점이므로 토큰 없이 실행하면 아무것도 할 수 없고, 이때 명확한 에러 메시지를 내는 것이 옳다.

## 3. 변경 대상

### 3.1 `smtm/__main__.py` — 대폭 축소

- `build_parser()`: `--token`, `--chatid`, `--log`, `--version`만 남긴다. help 텍스트에서 mode 설명과 CLI 예제를 제거하고 텔레그램 실행 예제만 남긴다.
- `DEFAULT_MODE`, `DEFAULT_CONFIG`, `CONFIG_ALIASES`, `load_config()`, `merge_config()` 삭제.
- `parse_args()`: `parser.parse_args(argv)` 결과를 그대로 반환.
- `main()`: 모드 분기 없이 `TelegramController`만 생성·실행.

`Controller` import 제거.

### 3.2 `smtm/controller/controller.py` — 삭제

### 3.3 `smtm/__init__.py`

- `from .controller.controller import Controller` 삭제
- `__all__`에서 `"Controller"` 삭제

`JptController`, `TelegramController` export는 유지.

### 3.4 `smtm/controller/telegram/telegram_controller.py`

- `ProfileStore` import 추가
- `SystemOperator(llm_client, config, profile_store=ProfileStore(), account_store=AccountStore())`
- config의 `"virtual"`을 `False` → `True`
- 부팅 안내 메시지에 가상거래 기본값임을 명시하고, 실거래 전환은 채팅으로 계좌를 등록해야 함을 안내

`main()`의 `exchange`/`currency`/`budget` 파라미터는 기본값을 가진 채로 유지한다. 저장소 전체에서 `TelegramController`를 호출하는 곳은 `__main__.py` 하나뿐이고(테스트 포함 다른 참조 없음) 거기서는 인자 없이 호출하므로 기본값이 그대로 적용된다. 시그니처를 좁히는 것은 이번 변경의 목적과 무관하므로 손대지 않는다.

### 3.5 `config/virtual-upbit.json` — 삭제

### 3.6 `tests/unit_tests/main_config_test.py` — 재작성

기존 테스트는 전부 config 병합·mode·profile 플래그를 검증하므로 대상이 사라진다. 다음으로 대체한다:

- `--token`/`--chatid`가 파싱된다
- `--log`가 파싱된다
- 제거된 플래그(`--mode`, `--config`, `--budget` 등)를 넘기면 `SystemExit`

파일명을 `main_args_test.py`로 바꾼다 (더 이상 config 파일 테스트가 아니다).

### 3.7 새 테스트 — 텔레그램 Tool 등록과 가상거래 기본값

`TelegramController`가 만드는 `SystemOperator`가

- 프로파일 Tool과 `create_session` Tool을 등록하는지
- default 세션이 `virtual: True`인지

를 검증한다. 기존 e2e/통합 테스트의 Fake(`FakeLlmClient` 등)를 활용한다.

### 3.8 README 2종

- 기능 목록: "CLI 인터랙티브 모드 및 텔레그램 챗봇 제어" → "텔레그램 챗봇 제어"
- 실행 방법: `--mode 0` CLI 섹션 삭제, 텔레그램 실행만 남김
- 옵션 표: 남은 4개 플래그만
- 가상거래가 기본이며 실거래는 채팅으로 계좌 등록 후 세션을 만들어야 함을 명시
- 아키텍처 컴포넌트 목록에서 CLI `Controller` 제거

### 3.9 문서

`docs/public/architecture.md`의 Presentation 계층 표에 `Controller`(CLI)가 있다. 이 표에서 제거한다. `docs/wiki/architecture.md`도 동일.

`RELEASE_NOTES.md`는 과거 기록이므로 수정하지 않는다.

## 4. 데이터 흐름 (변경 후)

```
python -m smtm --token <t> --chatid <c>
        │
        ▼
TelegramController.main()
        │  SystemOperator(config{virtual: True}, profile_store, account_store)
        ▼
SystemOperator.setup()
        │  default 세션 생성 (가상, BNH) — 시작하지 않음
        │  Tool 등록: 시장/포트폴리오/전략/세션/프로파일/계좌 전부
        ▼
텔레그램 채팅
        ├─ "start"          → default(가상) 세션 시작
        ├─ 계좌 등록         → register_account
        ├─ 실거래 프로파일   → create_profile(virtual=false, account=...)
        └─ 실거래 세션       → create_session(profile=...) → start_session
```

## 5. 테스트 전략

| 계층 | 검증 |
|---|---|
| 단위 | 인자 파서가 4개 플래그만 받고 나머지는 거부 |
| 단위 | `smtm` 패키지에서 `Controller`가 사라짐 |
| 통합 | `TelegramController`의 `SystemOperator`에 프로파일/세션 Tool이 등록됨 |
| 통합 | default 세션이 가상거래 |
| 회귀 | 기존 e2e 스위트가 계속 통과 |

## 6. 범위 밖

- `JptController` 제거 — 노트북 전용 도구로 유지
- 텔레그램 메시지 핸들러(`message_handler.py`) 변경
- `SystemOperator`의 Tool 등록 가드(`if profile_store is not None`) 구조 변경 — 주입만으로 해결되므로 건드리지 않는다
- `RELEASE_NOTES.md` 과거 항목 수정
