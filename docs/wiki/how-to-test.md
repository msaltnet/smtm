# 테스트 방법

테스트 실행을 위해 개발 의존성을 먼저 설치하세요.

```
pip install -r requirements-dev.txt
```

테스트는 pytest로 실행하며, 세 가지 카테고리로 나뉩니다.

```
# 전체 테스트 실행
python -m pytest tests/

# 카테고리별 실행
python -m pytest tests/unit_tests/          # 단위 테스트
python -m pytest tests/e2e_tests/           # E2E 테스트
python -m pytest tests/integration_tests/   # 통합 테스트 (API 키 필요)
```

## 테스트 구조

| 디렉토리 | 설명 | 외부 API |
|----------|------|----------|
| `tests/unit_tests/` | 개별 컴포넌트 테스트 | 전부 mock |
| `tests/e2e_tests/` | 전체 파이프라인 테스트 (채팅 → 도구 → 거래 → 결과) | LLM, 거래소, 시장 데이터만 Fake. 내부 컴포넌트는 전부 실제 코드 |
| `tests/integration_tests/` | 실제 거래소 API 테스트 | API 키 필요 |

## E2E 테스트

E2E 테스트는 외부 API 호출 없이 전체 흐름을 검증합니다. 시스템 경계만 Fake로 대체됩니다.

- **FakeLlmClient** — 미리 정의된 LLM 응답(도구 호출, 텍스트)을 순서대로 반환
- **SimulationTrader** — 실제 잔고/자산 상태를 관리하는 프로덕션 가상거래 Trader
- **FakeDataProvider** — 고정 시장 캔들 데이터 반환

내부 컴포넌트(`SystemOperator`, `TradingOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, 모든 Strategy와 Tool)는 실제 코드로 동작합니다.

## 통합 테스트

통합 테스트는 실제 거래소 API를 사용해서 진행됩니다. 일부 수동 테스트는 주피터 노트북으로도 실행할 수 있습니다. `notebook` 폴더를 확인해 보세요.


# How to test

Install the development dependencies first.

```
pip install -r requirements-dev.txt
```

Tests run with pytest and are split into three categories.

```
# Run all tests
python -m pytest tests/

# Run by category
python -m pytest tests/unit_tests/          # Unit tests
python -m pytest tests/e2e_tests/           # E2E tests
python -m pytest tests/integration_tests/   # Integration tests (requires API keys)
```

## Test structure

| Directory | Description | External APIs |
|-----------|-------------|---------------|
| `tests/unit_tests/` | Individual component tests | All mocked |
| `tests/e2e_tests/` | Full pipeline tests (chat → tool → trade → result) | LLM, exchange, market data are Fake; all internal components run real code |
| `tests/integration_tests/` | Real exchange API tests | Requires API keys |

## E2E tests

E2E tests verify the complete flow without calling any external APIs. Only the system boundary is replaced with Fake implementations.

- **FakeLlmClient** — Returns pre-scripted LLM responses (tool calls and text)
- **SimulationTrader** — Production virtual-trading trader with real balance/asset state management
- **FakeDataProvider** — Returns static market candle data

All internal components (`SystemOperator`, `TradingOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, all Strategies and Tools) run with real code.

## Integration tests

Integration tests run against the real exchange APIs. Some manual tests can also be run via Jupyter notebooks — see the `notebook` directory.
