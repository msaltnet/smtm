# OpenAI LLM 지원 설계

- 날짜: 2026-08-15
- 상태: 승인됨

## 1. 목적

`smtm`의 텔레그램 제어 에이전트가 Anthropic Claude뿐 아니라 OpenAI API도 사용할 수 있게 한다. 기존 Claude 사용자는 설정을 바꾸지 않아도 계속 동작해야 한다.

이번 변경은 LLM 제공자 어댑터와 부팅 설정만 다룬다. 매매 전략, 거래소 연동, SafetyGuard의 정책은 변경하지 않는다.

## 2. 결정

### D1. 두 제공자를 모두 유지한다

`SMTM_LLM_PROVIDER` 환경변수로 `claude` 또는 `openai`를 고른다. 값이 없으면 기존 동작을 보존하는 `claude`를 사용한다. 지원하지 않는 값은 부팅 전에 명확한 오류로 종료한다.

### D2. OpenAI는 별도 어댑터에서 형식을 변환한다

`SystemOperator`는 현재의 `LlmClient` 인터페이스와 대화 이력 형식을 그대로 유지한다. 새 `OpenAILlmClient`가 요청 직전에 다음을 OpenAI Chat Completions 형식으로 변환한다.

- tool schema: `input_schema` → function `parameters`
- tool choice: Anthropic의 단일 tool 강제 형식 → OpenAI function 강제 형식
- assistant tool use → OpenAI assistant `tool_calls`
- user tool result → OpenAI `tool` 메시지

OpenAI 응답은 텍스트, function call, 종료 사유, 토큰 사용량을 기존 `LlmResponse`로 정규화한다. JSON 인자가 올바르지 않으면 실행하지 않고 호출 정보를 포함한 `ValueError`를 낸다.

이 방식은 매매 도구와 안전 가드를 변경하지 않으며, Claude 회귀 위험을 최소화한다. 전체 대화 이력을 벤더 중립 형식으로 리팩터링하는 방식은 장기적으로는 더 깔끔하지만 이번 기능 범위에는 과도하다.

### D3. OpenAI 기본 모델은 비용 효율형으로 둔다

`SMTM_OPENAI_MODEL`이 없으면 `gpt-5.6-luna`를 사용한다. 텔레그램 제어와 주기적 호출에서 비용을 낮추기 위한 기본값이며, 더 높은 성능이 필요하면 운영자가 `gpt-5.6-terra` 등 계정에서 사용 가능한 함수 호출 모델로 덮어쓸 수 있다.

OpenAI 공식 문서는 GPT-5.6 Luna를 고빈도·비용 민감 작업용으로, Terra를 가격 대비 성능 선택지로 소개하며 두 모델 모두 Chat Completions와 함수 호출을 지원한다.

## 3. 환경변수와 부팅 규칙

### Claude (기존 기본값)

```env
SMTM_LLM_PROVIDER=claude
SMTM_LLM_API_KEY=...
```

### OpenAI

```env
SMTM_LLM_PROVIDER=openai
OPENAI_API_KEY=...
# 선택 사항, 기본값: gpt-5.6-luna
SMTM_OPENAI_MODEL=gpt-5.6-luna
```

선택한 제공자의 키가 없을 때만 해당 키 이름을 안내하고 부팅을 중단한다. 두 키가 모두 있어도 선택된 제공자의 키만 사용한다. 키 값은 로그·오류 메시지·테스트 출력에 포함하지 않는다.

## 4. 변경 대상

| 대상 | 변경 |
|---|---|
| `requirements.txt` | 공식 `openai` Python SDK 추가 |
| `smtm/llm/openai_llm_client.py` | OpenAI Chat Completions 어댑터 추가 |
| `smtm/llm/__init__.py`, `smtm/__init__.py` | `OpenAILlmClient` export |
| `smtm/controller/telegram/telegram_controller.py` | 환경변수로 LLM 제공자와 모델 선택 |
| `tests/unit_tests/openai_llm_client_test.py` | 요청 변환·응답 정규화·도구 호출 테스트 |
| 텔레그램 컨트롤러 테스트 | 제공자 선택·키 누락·잘못된 제공자 테스트 |
| README 및 공개 문서 | OpenAI 설정과 기본 모델 문서화 |

## 5. 데이터 흐름

```text
TelegramController
  └─ SMTM_LLM_PROVIDER=openai
       └─ OpenAILlmClient(OPENAI_API_KEY, SMTM_OPENAI_MODEL)
            ├─ 기존 messages/tools를 OpenAI Chat Completions 요청으로 변환
            └─ 응답을 LlmResponse(text, tool_calls, usage)로 정규화
                 └─ SystemOperator → ToolRouter → SafetyGuard → Trader
```

`SystemOperator`가 도구 결과를 다음 LLM 호출에 넣는 기존 루프는 유지한다. OpenAI 어댑터만 tool-call ID를 보존해 후속 `tool` 메시지가 원래 function call에 연결되도록 보장한다.

## 6. 오류 처리

- 알 수 없는 `SMTM_LLM_PROVIDER`: 지원 값 목록을 출력하고 시작하지 않음
- `OPENAI_API_KEY` 누락: 키 이름만 안내하고 시작하지 않음
- OpenAI function arguments JSON 파싱 실패: 도구를 실행하지 않고 오류 전파
- OpenAI API 오류: 기존 TelegramController 오류 경로로 사용자에게 전달하고 키는 마스킹

## 7. 검증

- 텍스트 응답, 단일·복수 도구 호출, 토큰 사용량을 `LlmResponse`로 변환하는 단위 테스트
- Anthropic 대화 이력의 tool use/tool result를 OpenAI 메시지로 변환하는 단위 테스트
- tool schema 및 강제 tool choice 변환 테스트
- provider 선택, 키 누락, 잘못된 provider의 컨트롤러 테스트
- 기존 Claude 클라이언트와 E2E 테스트 회귀 실행
- 실제 OpenAI 키 없이 SDK 호출을 전부 mock하여 테스트

## 8. 범위 밖

- Responses API 전환 또는 Agents SDK 도입
- 자동 모델 폴백·다중 제공자 동시 호출
- SafetyGuard 한도와 실거래 정책 변경
- 서버 배포와 기존 개발 컨테이너 중지는 OpenAI 지원 검증 후 별도 단계에서 수행

## 참고

- [OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI Model Guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI Model Comparison](https://developers.openai.com/api/docs/models/compare)
