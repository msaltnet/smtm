# LLM Operator 설계 문서

smtm 자동 매매 시스템을 LLM 기반 자율 에이전트 아키텍처로 전환하기 위한 설계 문서.

## 목차

1. [배경 및 동기](#1-배경-및-동기)
2. [설계 결정 사항](#2-설계-결정-사항)
3. [기존 시스템 vs 새 시스템](#3-기존-시스템-vs-새-시스템)
4. [전체 아키텍처](#4-전체-아키텍처)
5. [신규 컴포넌트 상세](#5-신규-컴포넌트-상세)
6. [기존 컴포넌트 변환](#6-기존-컴포넌트-변환)
7. [데이터 흐름](#7-데이터-흐름)
8. [안전장치](#8-안전장치)
9. [설정 및 구성](#9-설정-및-구성)

---

## 1. 배경 및 동기

### 현재 시스템의 한계

smtm은 `DataProvider → Strategy → Trader → Analyzer` 순차 파이프라인 기반의 자동 매매 시스템이다.
현재 전략(Strategy)은 SMA, RSI 등 규칙 기반 알고리즘으로, 다음과 같은 한계가 있다:

- **고정된 규칙**: 임계값과 지표가 코드에 하드코딩되어 시장 변화에 유연하게 대응 불가
- **비정형 데이터 활용 불가**: 뉴스, 시장 심리, 온체인 데이터 등을 판단에 반영할 수 없음
- **단방향 인터랙션**: 사용자가 명령어로 제어하지만, 시스템이 왜 그런 판단을 했는지 설명 불가
- **순차 파이프라인 고정**: 데이터 수집 → 판단 → 실행 순서가 고정되어 상황에 따른 유동적 판단 불가

### 목표

LLM을 시스템의 핵심 오케스트레이터로 도입하여:

- 정형/비정형 데이터를 종합한 자율적 매매 판단
- 자연어 기반 사용자 인터랙션 (채팅으로 제어, 조회, 설명)
- 기존 전략을 LLM이 참고하는 지식으로 활용
- 상황에 따라 유동적으로 데이터 수집, 분석, 실행 순서 결정

---

## 2. 설계 결정 사항

설계 과정에서 확정된 주요 결정:

| 항목 | 결정 | 이유 |
|------|------|------|
| LLM 호출 방식 | 내부 LLM Client 직접 호출 | 기존 구조에 자연스럽게 통합 |
| LLM 추상화 | LlmClient ABC로 벤더 추상화 | Claude, OpenAI, 로컬 LLM 등 교체 가능 |
| 거래소 지원 | 기존 TraderFactory 구조 활용, 거래소 무관 | 설정으로 거래소 선택 분리 |
| 안전장치 | 보수적 (거래금액/횟수/손실한도 3중 제한) | LLM 할루시네이션에 의한 금전적 손실 방지 |
| 시뮬레이션 | 미지원 | LLM 비결정적 특성상 백테스팅 재현 불가 |
| 기존 전략 활용 | 병행 운용 (기존 Operator와 LlmOperator 동시 실행) | 성과 비교 가능 |
| 컨텍스트 범위 | 사용자 설정 가능 | 비용/성능 균형을 사용자가 조절 |
| Operator 구조 | Operator + Strategy 통합 → LlmOperator | LLM이 전략과 오케스트레이션 모두 담당 |
| 인터페이스 | 단일 chat 인터페이스 | 사용자 요청, 주기적 판단, 조회 모두 chat으로 통합 |
| Analyzer 분리 | 분석(Tool) + 로깅(SystemMonitor) | 로깅은 LLM 바깥에서 독립 동작 필수 |

---

## 3. 기존 시스템 vs 새 시스템

### 3-1. 아키텍처 전환 요약

```
기존: 고정 순차 파이프라인
┌────────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Controller │──→│   Operator   │──→│DataProvdr│──→│ Strategy │──→│  Trader  │
│            │   │  (순차실행)   │   │          │   │(규칙기반) │   │          │
└────────────┘   └──────────────┘   └──────────┘   └──────────┘   └──────────┘
                        │                                               │
                        └────────────── Analyzer ◄──────────────────────┘

신규: LLM 자율 에이전트
┌────────────┐   ┌──────────────────────────────────────────────────────┐
│ Controller │──→│                  LlmOperator                        │
│ (chat 중계) │   │  ┌───────────┐                                      │
│            │   │  │ LlmClient │──→ Tool 자율 호출 (순서 유동적)        │
└────────────┘   │  └───────────┘       │                               │
                 │      ▲               ├── Data Tools (DataProvider)   │
                 │      │               ├── Execution Tools (Trader)    │
                 │  Strategy            ├── Analysis Tools (Analyzer)   │
                 │  Knowledge           └── SafetyGuard (강제)          │
                 │  (RAG/Skill)                                         │
                 │                      SystemMonitor (독립 로깅)        │
                 └──────────────────────────────────────────────────────┘
```

### 3-2. 컴포넌트별 역할 변화

| 컴포넌트 | 기존 역할 | 새 역할 |
|----------|----------|---------|
| **Controller** | 명령어 파싱, 상태 관리, 콜백 처리 | chat 입출력 중계 + 타이머 위임 |
| **Operator** | DataProvider→Strategy→Trader 순차 실행 | *기존 그대로 유지 (병행 운용)* |
| **LlmOperator** | *(신규)* | LLM 기반 자율 오케스트레이션 |
| **DataProvider** | Operator가 호출, Strategy에 전달 | Tool로 래핑, LLM이 자율 호출 |
| **Strategy** | 규칙 기반 매매 알고리즘 (코드) | 전략 지식 문서 (텍스트, RAG/Skill) |
| **Trader** | Operator가 Strategy 결과를 전달받아 실행 | Tool로 래핑, LLM이 자율 호출 |
| **Analyzer** | 데이터 기록 + 분석 + 리포트 + 그래프 | **분리**: 분석/리포트는 Tool, 기록/로깅은 SystemMonitor |

---

## 4. 전체 아키텍처

### 4-1. 시스템 전체 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Controller Layer                             │
│                                                                     │
│   ┌───────────┐    ┌──────────────────┐    ┌──────────────────┐    │
│   │Controller │    │TelegramController│    │  JptController   │    │
│   │  (CLI)    │    │   (Chatbot)      │    │  (Jupyter)       │    │
│   └─────┬─────┘    └───────┬──────────┘    └────────┬─────────┘    │
│         │                  │                        │              │
│         ▼                  ▼                        ▼              │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │              chat(message) → response                    │     │
│   └──────────────────────────┬───────────────────────────────┘     │
│                              │                                     │
│   ┌──────────────────────────▼───────────────────────────────┐     │
│   │                    LlmOperator                            │     │
│   │   (타이머, LLM 호출, Tool 실행, 대화 관리)                  │     │
│   └──────────────────────────┬───────────────────────────────┘     │
│                              │                                     │
│           ┌──────────────────┼───────────────────┐                 │
│           ▼                  ▼                   ▼                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│   │  LlmClient   │  │  ToolRouter  │  │   SystemMonitor      │    │
│   │ (LLM 추상화) │  │ (Tool 실행)  │  │  (독립 로깅)          │    │
│   └──────────────┘  └──────┬───────┘  └──────────────────────┘    │
│                            │                                       │
│         ┌──────────────────┼──────────────────┐                    │
│         ▼                  ▼                  ▼                    │
│   ┌───────────┐     ┌───────────┐     ┌──────────────┐            │
│   │Data Tools │     │Exec Tools │     │ SafetyGuard  │            │
│   └─────┬─────┘     └─────┬─────┘     │ (규칙 강제)  │            │
│         │                 │           └──────────────┘            │
│         ▼                 ▼                                        │
│   ┌───────────┐     ┌───────────┐                                  │
│   │DataProvdr │     │  Trader   │                                  │
│   │(Upbit/    │     │ (Upbit/   │                                  │
│   │ Binance)  │     │  Binance) │                                  │
│   └───────────┘     └───────────┘                                  │
│                                                                     │
│   Strategy Knowledge (RAG/Skill)                                    │
│   ┌──────────────────────────────────┐                              │
│   │ sma_crossover.md │ rsi.md │ ... │                              │
│   └──────────────────────────────────┘                              │
│                                                                     │
│   기존 Operator (병행 운용, 선택적)                                   │
│   ┌──────────────────────────────────┐                              │
│   │ Operator + Strategy + Trader     │                              │
│   └──────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 4-2. 병행 운용 구조

기존 Operator와 LlmOperator를 동시에 실행하여 성과를 비교할 수 있다.

```
Controller
    │
    ├──→ LlmOperator  (LLM 기반, 실거래 또는 데모)
    │        └── Trader (Upbit)
    │
    └──→ Operator      (규칙 기반, 데모 모드로 비교)
             ├── Strategy (SMA)
             └── Trader (Demo)
```

두 시스템은 독립적으로 동작하며, 각각의 SystemMonitor/Analyzer가 성과를 기록한다.

---

## 5. 신규 컴포넌트 상세

### 5-1. LlmOperator

Operator와 Strategy가 통합된 LLM 기반 자율 오퍼레이터.
기존 Operator의 순차 파이프라인 대신, LLM이 자율적으로 Tool을 선택하여 호출한다.

**역할:**
- 주기적 타이머 관리 (매 사이클마다 LLM에게 판단 요청)
- 사용자와의 채팅 인터페이스 제공
- LLM 대화 컨텍스트(conversation history) 관리
- Tool 호출 결과를 LLM에게 반환하는 루프 처리
- 시스템 상태 관리 (ready, running, stopped, error)

**인터페이스:**

```python
class LlmOperator:
    """LLM 기반 자율 트레이딩 오퍼레이터
    
    기존 Operator가 DataProvider→Strategy→Trader를 순차 호출했다면,
    LlmOperator는 LLM이 자율적으로 Tool을 선택하여 호출한다.
    """

    def __init__(self, llm_client, config):
        self.llm_client: LlmClient            # LLM 추상화 클라이언트
        self.tool_router: ToolRouter           # Tool 라우팅 및 실행
        self.system_monitor: SystemMonitor     # 독립 로깅
        self.safety_guard: SafetyGuard         # 안전장치
        self.conversation_history: list        # LLM 대화 기록
        self.strategy_knowledge: str           # 전략 지식 (System Prompt에 주입)
        self.state: str                        # ready, running, stopped, error
        self.interval: int                     # 주기적 호출 간격 (초)
        self.timer: Timer                      # 주기적 호출 타이머
        self.context_config: ContextConfig     # 컨텍스트 범위 설정

    def chat(self, message: str) -> str:
        """단일 인터페이스 — 사용자 요청 및 주기적 판단 모두 처리
        
        사용자 요청 예시:
          "BTC 자동매매 시작해줘, 예산 50만원, Upbit 거래소"
          "지금 수익률 어때?"
          "왜 방금 매수했어?"
          "좀 더 보수적으로 운영해줘"
          "거래 중지해"
        
        주기적 호출 (타이머):
          시장 데이터가 포함된 판단 요청 프롬프트
        
        Args:
            message: 사용자 메시지 또는 시스템 프롬프트
            
        Returns:
            LLM 응답 텍스트 (사용자에게 전달)
        """

    def _on_timer(self):
        """주기적 판단 요청 — 타이머가 호출
        
        1. DataProvider에서 현재 시장 데이터 수집
        2. SystemMonitor에 시장 데이터 기록
        3. 시장 데이터 + 포트폴리오 상태를 포함한 프롬프트 구성
        4. chat()을 통해 LLM에게 판단 요청
        """

    def _execute_llm_loop(self, messages) -> str:
        """LLM Tool Use 루프
        
        LLM 응답에 tool_calls가 포함되면:
          1. SafetyGuard 검증
          2. ToolRouter로 실행
          3. SystemMonitor에 기록
          4. 결과를 LLM에 반환
          5. LLM이 추가 tool_calls 없을 때까지 반복
        """

    def _build_system_prompt(self) -> str:
        """System Prompt 구성
        
        포함 내용:
          - 역할 정의 (자율 트레이딩 에이전트)
          - 선택된 전략 지식 (Strategy Knowledge)
          - 안전장치 규칙 안내
          - 사용 가능한 Tool 목록 설명
          - 현재 설정 정보 (거래소, 통화, 예산)
        """

    def _build_periodic_prompt(self, market_data) -> str:
        """주기적 판단 요청 프롬프트 구성
        
        포함 내용:
          - 현재 시장 데이터 (OHLCV)
          - 컨텍스트 설정에 따른 과거 데이터
          - 현재 포트폴리오 상태 요약
        """

class ContextConfig:
    """LLM에 전달할 컨텍스트 범위 설정"""
    candle_count: int = 20              # 전달할 과거 캔들 수
    include_portfolio: bool = True      # 포트폴리오 상태 포함 여부
    include_trade_history: bool = True  # 최근 거래 내역 포함 여부
    trade_history_count: int = 10       # 포함할 최근 거래 수
    max_conversation_turns: int = 50    # 대화 기록 최대 턴 수 (초과 시 오래된 것부터 제거)
```

**동시성 처리:**

타이머의 `_on_timer()`와 사용자의 `chat()` 호출이 동시에 발생할 수 있다.
기존 Operator와 동일하게 Worker 스레드 + 큐 방식으로 직렬화하여 처리한다.
모든 LLM 호출은 Worker 큐에 task로 등록되어 순차 실행된다.

**대화 기록 관리:**

conversation_history는 `ContextConfig.max_conversation_turns`에 따라 관리된다.
최대 턴 수를 초과하면 오래된 대화부터 제거한다.
단, System Prompt와 가장 최근 사이클의 Tool 호출 기록은 항상 유지한다.

**상태 전이:**

```
            chat("시작해")         chat("중지해")
  ready ─────────────────→ running ───────────────→ stopped
    ▲                         │                        │
    │                         │ (에러 발생)             │
    │                         ▼                        │
    │                       error                      │
    │                         │                        │
    └─────────────────────────┴────────────────────────┘
                       chat("재시작해")
```

기존 Operator와의 핵심 차이:
- `initialize()`, `start()`, `stop()`, `get_score()` 등 개별 메서드 대신 `chat()` 하나로 통합
- 시작/중지/조회 등의 명령을 LLM이 자연어로 해석하여 내부적으로 처리
- 타이머는 내부에서 관리하며, 주기적으로 `_on_timer()`를 호출

---

### 5-2. LlmClient

LLM 벤더를 추상화하는 클라이언트 인터페이스.
Claude, OpenAI, 로컬 LLM 등을 교체 가능하게 한다.

**역할:**
- LLM API 호출 추상화
- Tool Use 스펙 변환 (벤더별 포맷 차이 내부 처리)
- 응답 파싱 및 정규화

**인터페이스:**

```python
class LlmClient(ABC):
    """LLM 벤더 추상화 클라이언트"""

    @abstractmethod
    def create_message(
        self,
        system_prompt: str,
        messages: list,
        tools: list
    ) -> LlmResponse:
        """LLM에 메시지를 전송하고 응답을 받는다
        
        Args:
            system_prompt: 시스템 프롬프트
            messages: 대화 기록 [{role, content}]
            tools: 사용 가능한 Tool 스키마 목록
            
        Returns:
            LlmResponse: 정규화된 LLM 응답
        """

class LlmResponse:
    """LLM 응답 정규화 객체"""
    text: str                       # LLM 텍스트 응답
    tool_calls: List[ToolCall]      # Tool 호출 목록 (없으면 빈 리스트)
    stop_reason: str                # "end_turn" | "tool_use"
    usage: dict                     # 토큰 사용량 {input, output}

class ToolCall:
    """Tool 호출 정보"""
    id: str              # Tool 호출 고유 ID
    name: str            # Tool 이름 e.g. "execute_trade"
    arguments: dict      # Tool 인자 e.g. {"action": "buy", "currency": "BTC"}
```

**구현체:**

```python
class ClaudeLlmClient(LlmClient):
    """Anthropic Claude API 클라이언트"""
    # anthropic SDK 사용
    # tool_use 네이티브 지원

class OpenAILlmClient(LlmClient):
    """OpenAI API 클라이언트"""
    # openai SDK 사용
    # function_calling → ToolCall 변환

class OllamaLlmClient(LlmClient):
    """Ollama 로컬 LLM 클라이언트"""
    # 로컬 실행, 인터넷 불필요
    # Tool Use 지원 모델 필요
```

---

### 5-3. ToolRouter

Tool 등록, 스키마 관리, 실행을 담당하는 라우터.

**역할:**
- Tool 인스턴스 등록 및 관리
- LLM에 전달할 Tool 스키마 생성
- ToolCall을 받아 해당 Tool 실행
- SafetyGuard 연동 (실행 전 검증)

**인터페이스:**

```python
class ToolRouter:
    """Tool 등록, 라우팅, 실행"""

    def __init__(self, safety_guard: SafetyGuard):
        self.tools: Dict[str, Tool] = {}
        self.safety_guard = safety_guard

    def register(self, tool: Tool):
        """Tool 등록"""

    def get_tool_schemas(self) -> list:
        """LLM에 전달할 Tool 스키마 목록 반환
        
        각 Tool의 name, description, input_schema를 
        LlmClient가 사용하는 포맷으로 반환
        """

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Tool 실행
        
        1. SafetyGuard 검증 (execute_trade 등 거래 Tool)
        2. 해당 Tool의 execute() 호출
        3. ToolResult 반환
        """

class Tool(ABC):
    """Tool 기본 추상 클래스"""
    name: str                  # Tool 이름
    description: str           # Tool 설명 (LLM이 읽음)
    input_schema: dict         # JSON Schema

    @abstractmethod
    def execute(self, arguments: dict) -> ToolResult:
        """Tool 실행"""

class ToolResult:
    """Tool 실행 결과"""
    success: bool
    data: Any                  # Tool 실행 결과 데이터
    error: str | None          # 에러 메시지 (실패 시)
```

---

### 5-4. SystemMonitor

LLM 바깥에서 독립적으로 동작하는 시스템 모니터.
LLM이 제어할 수 없으며, 모든 시스템 활동을 무조건 기록한다.

**역할:**
- 모든 거래 요청/결과 자동 기록
- 시장 데이터 기록
- LLM 호출 로그 (프롬프트, 응답, 토큰 사용량)
- Tool 호출 로그
- SafetyGuard 이벤트 로그
- 주기적 자산 스냅샷
- 기록된 데이터를 Analysis Tool에 제공

**기존 Analyzer와의 관계:**

```
기존 Analyzer의 역할 분리:

┌─────────────────────────────────────────┐
│            기존 Analyzer                 │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │  데이터 기록   │  │  분석/리포트/그래프│ │
│  │  (로깅)       │  │  (분석)           │ │
│  └──────┬───────┘  └────────┬─────────┘ │
└─────────┼──────────────────┼────────────┘
          │                  │
          ▼                  ▼
┌──────────────────┐  ┌──────────────────┐
│  SystemMonitor   │  │ PerformanceTool  │
│  (독립 로깅)     │  │ (분석 Tool)       │
│  LLM 제어 불가   │  │ LLM이 호출       │
└──────────────────┘  └──────────────────┘
```

**인터페이스:**

```python
class SystemMonitor:
    """독립 시스템 모니터 — LLM 바깥에서 모든 활동을 기록"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path   # 로그 저장 경로

    # === 자동 기록 (LLM이 제어 불가) ===
    
    def log_market_data(self, data: list):
        """매 사이클 시장 데이터 기록"""

    def log_trade_request(self, request: dict):
        """모든 거래 요청 기록"""

    def log_trade_result(self, result: dict):
        """모든 거래 결과 기록"""

    def log_tool_call(self, tool_call: ToolCall, result: ToolResult):
        """모든 Tool 호출과 결과 기록"""

    def log_llm_interaction(self, request: dict, response: LlmResponse):
        """LLM 요청/응답 기록 (토큰 사용량 포함)"""

    def log_safety_event(self, event: dict):
        """SafetyGuard 차단/경고 이벤트 기록"""

    # === 자산 스냅샷 ===
    
    def take_snapshot(self, portfolio: dict):
        """현재 자산 상태 스냅샷 기록
        
        포함: 현금 잔고, 보유 자산, 현재 시세, 평가 금액
        """

    # === 데이터 조회 (PerformanceTool이 사용) ===
    
    def get_trade_log(self, start_time=None, end_time=None) -> list:
        """거래 기록 조회"""

    def get_snapshots(self, start_time=None, end_time=None) -> list:
        """자산 스냅샷 조회"""

    def get_llm_usage(self) -> dict:
        """LLM API 사용량 통계"""
```

---

### 5-5. SafetyGuard

규칙 기반 안전장치. Tool 실행 전에 검증하며, LLM이 우회할 수 없다.

**역할:**
- 거래 Tool (`execute_trade`) 호출 시 사전 검증
- 1회 최대 거래금액 제한
- 일일 거래횟수 제한
- 누적 손실 한도 초과 시 거래 자동 차단
- 모든 차단/경고 이벤트를 SystemMonitor에 기록

**인터페이스:**

```python
class SafetyGuard:
    """규칙 기반 안전장치 — Tool 실행 전 검증, LLM 우회 불가"""

    def __init__(self, config: SafetyConfig):
        self.max_trade_amount: float     # 1회 최대 거래금액
        self.max_daily_trades: int       # 일일 최대 거래횟수
        self.max_loss_ratio: float       # 최대 허용 손실률 (e.g. -0.20 = -20%)
        self.initial_budget: float       # 초기 예산
        
        self.daily_trade_count: int      # 오늘 거래 횟수
        self.daily_reset_time: datetime  # 일일 카운터 리셋 시간

    def check(self, tool_call: ToolCall, portfolio: dict) -> SafetyResult:
        """Tool 호출 사전 검증
        
        execute_trade Tool만 검증, 나머지 Tool은 무조건 통과.
        
        검증 항목:
        1. 1회 거래금액 ≤ max_trade_amount
        2. 일일 거래횟수 < max_daily_trades
        3. 현재 손실률 < max_loss_ratio
        
        Returns:
            SafetyResult: allowed=True/False, reason (차단 시 사유)
        """

    def record_trade(self, result: dict):
        """거래 완료 후 카운터 업데이트"""

    def is_trading_allowed(self) -> bool:
        """현재 거래 가능 상태인지 확인"""

    def get_status(self) -> dict:
        """현재 안전장치 상태 반환
        
        Returns:
            {
                "daily_trades": 5,
                "daily_limit": 10,
                "current_loss_ratio": -0.05,
                "max_loss_ratio": -0.20,
                "trading_allowed": True
            }
        """

class SafetyResult:
    allowed: bool          # 허용 여부
    reason: str | None     # 차단 사유 (차단 시)
```

**SafetyGuard가 동작하는 위치:**

```
LLM → "execute_trade BTC 매수" 
         │
         ▼
    ┌─────────────┐
    │ SafetyGuard │──→ 차단 시: LLM에게 차단 사유 반환
    │   check()   │           "일일 거래횟수 초과 (10/10)"
    └──────┬──────┘
           │ 통과
           ▼
    ┌─────────────┐
    │  TradeTool  │──→ Trader API 호출
    │  execute()  │
    └──────┬──────┘
           │ 결과
           ▼
    ┌─────────────┐
    │ SafetyGuard │──→ 거래 카운터 업데이트
    │record_trade │
    └──────┬──────┘
           │
           ▼
    ┌───────────────┐
    │ SystemMonitor │──→ 거래 기록 저장
    │  log_trade()  │
    └───────────────┘
```

---

### 5-6. Strategy Knowledge

기존 Strategy 코드를 LLM이 참고하는 지식 문서로 변환한 것.
LlmOperator의 System Prompt에 주입되거나, RAG로 검색된다.

**역할:**
- 매매 전략의 원리, 조건, 파라미터를 텍스트로 제공
- LLM이 시장 상황에 맞는 전략을 선택/조합하여 판단
- 사용자가 커스텀 전략 문서를 추가 가능

**파일 구조:**

```
strategies/
├── sma_crossover.md          # SMA 크로스오버 전략
├── rsi_strategy.md           # RSI 과매수/과매도 전략
├── bollinger_bands.md        # 볼린저밴드 전략
├── buy_and_hold.md           # 매수 후 보유 전략
└── custom/                   # 사용자 정의 전략
    └── my_strategy.md
```

**전략 문서 형식:**

```markdown
# SMA 크로스오버 전략

## 개요
단기/중기/장기 이동평균선의 교차를 기반으로 매매 신호를 생성하는 전략.

## 매수 조건
- 단기 SMA(10)가 중기 SMA(40)를 상향 돌파 (골든크로스)
- 종가가 장기 SMA(60) 위에 위치

## 매도 조건
- 단기 SMA(10)가 중기 SMA(40)를 하향 돌파 (데드크로스)
- 또는 손절 기준 도달 시

## 파라미터
- SHORT_PERIOD: 10 (단기 이동평균 기간)
- MID_PERIOD: 40 (중기 이동평균 기간)  
- LONG_PERIOD: 60 (장기 이동평균 기간)

## 적합한 시장
- 추세가 명확한 시장에서 효과적
- 횡보장에서는 잦은 거짓 신호 발생 주의

## 주의사항
- 이동평균은 후행 지표이므로 급변 시 대응 지연
- 분할 매수/매도로 리스크 분산 권장
```

**사용 방식:**
- `LlmOperator` 초기화 시 설정된 전략 문서를 로드
- System Prompt에 직접 포함하거나, 여러 전략 시 RAG로 검색
- LLM은 전략 지식을 참고하되, 시장 상황에 따라 자율적으로 판단

---

## 6. 기존 컴포넌트 변환

### 6-1. Data Tools — DataProvider 래핑

기존 DataProvider를 Tool로 래핑하여 LLM이 자율적으로 호출할 수 있게 한다.

| Tool 이름 | 래핑 대상 | 설명 |
|-----------|----------|------|
| `get_market_data` | DataProvider.get_info() | 현재 OHLCV 캔들 데이터 조회 |
| `get_orderbook` | *(신규 API 호출)* | 호가창 데이터 조회 |
| `search_news` | *(신규 외부 API)* | 암호화폐 관련 뉴스 검색 |
| `get_fear_greed` | *(신규 외부 API)* | 시장 공포탐욕 지수 조회 |
| `get_onchain_data` | *(신규 외부 API)* | 온체인 메트릭 조회 |

**MarketDataTool 상세:**

```python
class MarketDataTool(Tool):
    """시장 데이터 조회 Tool — 기존 DataProvider 래핑"""

    name = "get_market_data"
    description = "현재 시장의 OHLCV 캔들 데이터를 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "조회할 암호화폐"
            },
            "count": {
                "type": "integer",
                "description": "조회할 캔들 수 (기본 1)",
                "default": 1
            }
        },
        "required": ["currency"]
    }

    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider

    def execute(self, arguments: dict) -> ToolResult:
        """DataProvider.get_info()를 호출하여 시장 데이터 반환"""
```

`get_orderbook`, `search_news`, `get_fear_greed`, `get_onchain_data`는 신규 외부 API를 호출하는 Tool이며, 첫 버전에서는 `get_market_data`만 구현하고 나머지는 이후 확장한다.

---

### 6-2. Execution Tools — Trader, Analyzer 래핑

| Tool 이름 | 래핑 대상 | 설명 |
|-----------|----------|------|
| `execute_trade` | Trader.send_request() | 매수/매도 주문 실행 |
| `cancel_order` | Trader.cancel_request() | 주문 취소 |
| `get_portfolio` | Trader.get_account_info() | 현재 포트폴리오 조회 |
| `get_trade_history` | SystemMonitor.get_trade_log() | 거래 내역 조회 |
| `get_performance` | Analyzer 분석 기능 | 수익률/분석 리포트 |

**TradeTool 상세:**

```python
class TradeTool(Tool):
    """거래 실행 Tool — 기존 Trader 래핑"""

    name = "execute_trade"
    description = "거래소에 매수 또는 매도 주문을 실행합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "매수(buy) 또는 매도(sell)"
            },
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "거래할 암호화폐"
            },
            "price": {
                "type": "number",
                "description": "주문 가격"
            },
            "amount": {
                "type": "number",
                "description": "주문 수량"
            }
        },
        "required": ["action", "currency", "price", "amount"]
    }

    def __init__(self, trader: Trader):
        self.trader = trader

    def execute(self, arguments: dict) -> ToolResult:
        """Trader.send_request()를 호출하여 주문 실행
        
        내부적으로 기존 request 포맷으로 변환:
        {
            "id": 자동 생성,
            "type": arguments["action"],
            "price": arguments["price"],
            "amount": arguments["amount"],
            "date_time": 현재 시간
        }
        
        SafetyGuard는 ToolRouter 레벨에서 이미 검증 완료.
        """
```

**PerformanceTool 상세:**

```python
class PerformanceTool(Tool):
    """수익률 분석 Tool — Analyzer 분석 기능 + SystemMonitor 데이터"""

    name = "get_performance"
    description = "현재까지의 수익률, 거래 통계, 성과 분석을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": ["all", "today", "week", "month"],
                "description": "분석 기간",
                "default": "all"
            },
            "include_graph": {
                "type": "boolean",
                "description": "그래프 생성 여부",
                "default": False
            }
        }
    }

    def __init__(self, system_monitor: SystemMonitor, analyzer_components):
        self.system_monitor = system_monitor
        self.data_analyzer = analyzer_components["data_analyzer"]
        self.graph_generator = analyzer_components["graph_generator"]
        self.report_generator = analyzer_components["report_generator"]

    def execute(self, arguments: dict) -> ToolResult:
        """SystemMonitor 데이터를 기반으로 분석 리포트 생성"""
```

---

## 7. 데이터 흐름

### 7-1. 주기적 트레이딩 사이클

```
Timer 만료
    │
    ▼
LlmOperator._on_timer()
    │
    ├─ 1. DataProvider.get_info() → 시장 데이터 수집
    │
    ├─ 2. SystemMonitor.log_market_data() → 시장 데이터 기록
    │
    ├─ 3. 주기적 판단 프롬프트 구성
    │     (시장 데이터 + 컨텍스트 설정에 따른 과거 데이터 + 포트폴리오 요약)
    │
    ├─ 4. LlmClient.create_message() → LLM 호출
    │
    ├─ 5. LLM 응답 처리
    │     ├─ text만 → 판단 결과 로깅, 거래 없음
    │     └─ tool_calls 포함 → Tool Use 루프 진입
    │
    └─ 6. Tool Use 루프 (LLM이 tool_calls를 보내지 않을 때까지 반복)
          │
          ├─ SafetyGuard.check() → 검증
          ├─ ToolRouter.execute() → Tool 실행
          ├─ SystemMonitor.log_tool_call() → 기록
          └─ 결과를 LLM에 반환 → LLM이 추가 판단
```

### 7-2. 사용자 채팅 요청

```
사용자 메시지
    │
    ▼
Controller → LlmOperator.chat(message)
    │
    ├─ 1. conversation_history에 사용자 메시지 추가
    │
    ├─ 2. LlmClient.create_message() → LLM 호출
    │
    ├─ 3. LLM 응답 처리
    │     ├─ "수익률 보여줘" → get_performance Tool 호출
    │     ├─ "시작해" → 내부 상태 변경 + 타이머 시작
    │     ├─ "왜 매수했어?" → conversation_history 참고하여 설명
    │     └─ "중지해" → 타이머 중지 + 포지션 정리
    │
    ├─ 4. SystemMonitor.log_llm_interaction() → 기록
    │
    └─ 5. LLM 텍스트 응답 → Controller → 사용자에게 전달
```

### 7-3. Controller 변경 사항

기존 Controller는 명령어를 파싱하고 Operator의 개별 메서드를 호출했다.
LlmOperator 사용 시 Controller는 입출력 중계 역할만 수행한다.

```python
# 기존 Controller 흐름
key = input()
if key == "run":
    operator.start()
elif key == "stop":
    operator.stop()
elif key == "query":
    operator.get_score(callback)

# 새 Controller 흐름
message = input()
response = llm_operator.chat(message)
print(response)
```

TelegramController는 이미 채팅 기반이므로 전환이 자연스럽다:

```python
# 기존: 버튼 기반 명령 → 개별 메서드 호출
# 신규: 사용자 메시지 → llm_operator.chat() → 응답 전송
```

---

## 8. 안전장치

### 8-1. 3중 안전장치 구조

```
┌─ 1차: SafetyGuard (Tool 레벨) ──────────────────┐
│  • 1회 최대 거래금액 검증                          │
│  • 일일 거래횟수 제한                              │
│  • 누적 손실 한도 초과 시 거래 차단                 │
│  → LLM이 우회 불가, Tool 실행 전 강제 검증          │
└──────────────────────────────────────────────────┘

┌─ 2차: SystemMonitor (감사 로깅) ────────────────┐
│  • 모든 거래 요청/결과 무조건 기록                  │
│  • LLM 호출 로그 전체 기록                         │
│  • SafetyGuard 차단 이벤트 기록                    │
│  → 사후 추적 및 감사 가능                          │
└──────────────────────────────────────────────────┘

┌─ 3차: LLM System Prompt (가이드라인) ──────────┐
│  • "리스크 관리를 최우선으로 고려하라"               │
│  • "확신이 없으면 거래하지 마라"                    │
│  • "분할 매수/매도를 권장한다"                      │
│  → 가이드라인일 뿐, 강제력 없음 (1차/2차가 보완)    │
└──────────────────────────────────────────────────┘
```

### 8-2. SafetyGuard 설정 예시

```python
safety_config = SafetyConfig(
    max_trade_amount=100_000,      # 1회 최대 10만원
    max_daily_trades=20,           # 일일 최대 20회
    max_loss_ratio=-0.20,          # 최대 손실률 -20%
)
```

### 8-3. 차단 시 동작

SafetyGuard가 거래를 차단하면, 차단 사유가 LLM에게 Tool 결과로 전달된다.
LLM은 이 정보를 바탕으로 사용자에게 상황을 설명하거나, 대안적 판단을 내릴 수 있다.

```
LLM: execute_trade(buy, BTC, 200000, 0.5)
                    │
SafetyGuard: 차단 — "1회 최대 거래금액 초과 (200,000 > 100,000)"
                    │
LLM: "현재 설정된 1회 최대 거래금액(10만원)을 초과하여 매수할 수 없습니다.
      금액을 줄여서 분할 매수를 진행할까요?"
```

---

## 9. 설정 및 구성

### 9-1. LlmOperator 설정

```python
class LlmOperatorConfig:
    # LLM 설정
    llm_provider: str = "claude"            # "claude" | "openai" | "ollama"
    llm_model: str = "claude-sonnet-4-20250514"  # 모델 ID
    llm_api_key: str                        # API 키 (환경변수)
    
    # 거래 설정
    exchange: str = "UPB"                   # 거래소 코드
    currency: str = "BTC"                   # 거래 통화
    budget: float = 500_000                 # 초기 예산
    interval: int = 60                      # 주기적 호출 간격 (초)
    
    # 컨텍스트 설정
    context_candle_count: int = 20          # LLM에 전달할 과거 캔들 수
    context_include_portfolio: bool = True  # 포트폴리오 상태 포함 여부
    context_include_history: bool = True    # 최근 거래 내역 포함 여부
    
    # 전략 지식
    strategy_files: list = ["sma_crossover.md", "rsi_strategy.md"]
    
    # 안전장치
    safety: SafetyConfig
    
    # 로깅
    monitor_storage_path: str = "output/monitor/"
```

### 9-2. 환경변수

```bash
# LLM API 키
SMTM_LLM_API_KEY=sk-...

# 거래소 API 키 (기존과 동일)
UPBIT_OPEN_API_ACCESS_KEY=...
UPBIT_OPEN_API_SECRET_KEY=...
UPBIT_OPEN_API_SERVER_URL=...
```
