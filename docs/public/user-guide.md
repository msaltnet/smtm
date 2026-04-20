# smtm — User Guide

이 문서는 smtm을 **처음 설치하고 자동매매까지 돌려보려는 사용자**를 위한 실행 가이드입니다. 설치 → 환경변수 → CLI / 텔레그램 실행 → 대표 시나리오 4종 순서로 설명합니다.

- 최종 갱신일: 2026-04-20
- 기준 버전: 1.7.1

---

## 1. 시작하기

### 1.1 사전 준비물

| 항목 | 설명 |
|------|------|
| Python 3.9+ | `python --version`으로 확인 |
| Anthropic Claude API 키 | [Anthropic Console](https://console.anthropic.com) 발급, `SMTM_LLM_API_KEY`로 주입 |
| 거래소 API 키 | Upbit 또는 Bithumb (실주문용). 미발급 상태에서는 Tool 호출이 실패합니다. |
| (선택) 텔레그램 Bot | BotFather로 토큰 발급, `chat_id` 확인 |

### 1.2 설치

```bash
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

### 1.3 환경변수

프로젝트 루트의 `.env` 파일 또는 쉘 환경에 다음을 설정합니다.

```bash
# 필수 (현재 구현된 LLM 벤더는 Claude 하나)
SMTM_LLM_API_KEY=sk-ant-xxxxx

# Upbit (--exchange UPB)
UPBIT_OPEN_API_ACCESS_KEY=...
UPBIT_OPEN_API_SECRET_KEY=...
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb (--exchange BTH)
BITHUMB_API_ACCESS_KEY=...
BITHUMB_API_SECRET_KEY=...
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# 텔레그램 (--mode 1)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## 2. 실행 모드

### 2.1 CLI 인터랙티브 모드 (`--mode 0`)

터미널에서 LLM과 직접 채팅하며 매매를 제어합니다.

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB
```

실행하면 다음과 같은 프롬프트가 반복됩니다.

```
##### smtm LLM trading system is initialized #####
exchange: UPB, currency: BTC, budget: 500000
'start'를 입력하면 자동 매매가 시작됩니다
==============================
메시지를 입력하세요 (q: 종료):
```

| 입력 | 동작 |
|------|------|
| `start` | 자동 매매 타이머 시작 (`--term` 초 주기로 LLM 호출) |
| `stop` | 타이머 중지 (대화는 계속 가능) |
| `q` / `quit` / `exit` / `terminate` | 프로세스 종료 |
| 그 외 자유 입력 | LLM에 메시지 전달, Tool use 루프 실행 후 응답 출력 |

### 2.2 텔레그램 챗봇 모드 (`--mode 1`)

원격에서 텔레그램 메신저로 매매를 제어합니다.

```bash
python -m smtm --mode 1 --token <bot_token> --chatid <chat_id>
```

- 지정된 `chat_id`의 메시지만 수용합니다 (다른 사람이 봇에 말 걸어도 무시).
- 텍스트 메시지는 CLI와 동일한 대화 세션에 합류합니다.

### 2.3 Jupyter Notebook

노트북에서 `JptController`로 동일한 오퍼레이터를 띄울 수 있습니다.

```python
from smtm import JptController
controller = JptController(interval=60, budget=500000, currency="BTC", exchange="UPB")
controller.initialize()
# 이후 셀에서 controller.operator.chat("시장 상황 알려줘") 등으로 호출
```

---

## 3. 명령행 옵션 요약

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mode` | `0`: CLI, `1`: 텔레그램. 미지정 시 도움말 출력 | 도움말 |
| `--budget` | 거래 예산 (KRW) | 500000 |
| `--currency` | 거래 통화 (예: `BTC`, `ETH`) | BTC |
| `--exchange` | 거래소 코드 (`UPB` / `BTH`) | UPB |
| `--term` | 자동 매매 틱 주기 (초) | 60 |
| `--token` | 텔레그램 Bot 토큰 (mode 1 전용) | None |
| `--chatid` | 텔레그램 chat id (mode 1 전용) | None |
| `--log` | 로그 파일명 변경 | None (기본 `log/smtm.log`) |
| `--version` | 버전 출력 후 종료 | — |

---

## 4. 대화 방법 가이드

LLM에게는 **상황과 의도를 같이** 알려주면 더 잘 판단합니다. 단순한 명령뿐 아니라 자유형 질문도 가능합니다.

- 시장 관련: "BTC 시장 지금 어때?", "최근 캔들 요약해줘", "상승 추세면 소량 매수해"
- 포트폴리오: "내 포지션 보여줘", "지금까지 수익률 얼마야?"
- 이력: "최근 10건 거래 내역 줘"
- 제어: "조금만 관망하자", "리스크 낮춰서 가자"

LLM은 자체적으로 Tool을 선택해 호출합니다. 사용자가 Tool 이름을 외울 필요는 없습니다.

---

## 5. 시나리오

### 시나리오 1 — 처음 접속해서 시장만 살펴보기

1. `python -m smtm --mode 0 --budget 500000` 실행
2. `시장 상황 알려줘` 입력
3. LLM이 `get_market_data`를 호출한 뒤 요약해 답변
4. 아직 매매는 시작하지 않음 — `start`를 입력하지 않았기 때문에 타이머 미가동

### 시나리오 2 — 자동 매매 시작하고 지켜보기

1. 위 상태에서 `start` 입력 → "자동 매매가 시작되었습니다" 출력
2. `--term` 주기(기본 60초)마다 LLM이 호출됨
3. 매 틱에서 LLM이 시장 데이터를 확인하고, 필요하다고 판단되면 `execute_trade`를 호출
4. 사용자는 아무 때나 대화에 개입 가능: "지금은 매수하지 마", "일단 관망해줘"
5. 한도를 넘는 주문은 SafetyGuard가 거부하고 LLM이 사유("1회 최대 거래금액 초과 …")를 받아 재판단

### 시나리오 3 — 잠깐 멈추고 성과 확인

1. `stop` → 타이머 중지 (연결·대화는 유지)
2. `오늘 수익률 알려줘` 입력 → LLM이 `get_performance` 호출 후 수익률 응답
3. `최근 거래 5건만 보여줘` 입력 → `get_trade_history`로 내역 출력
4. 다시 돌리고 싶으면 `start`

### 시나리오 4 — 텔레그램으로 외출 중 개입

1. 로컬 서버/VPS에서 `--mode 1`로 실행 중
2. 출근 이동 중 텔레그램에서 "BTC 급락 중이야? 매도해" 전송
3. Bot이 메시지를 받아 LLM에 전달, LLM은 시장 상태를 확인한 뒤 매도 판단 시 주문 실행
4. 거래 결과가 텔레그램 메시지로 되돌아옴

### 시나리오 5 — 안전장치 기본값이 너무 타이트해서 조정

현재 `SafetyGuard`는 코드 레벨 `config["safety"]`로 주입됩니다. CLI 옵션으로는 노출돼 있지 않으며, 소스 수정이 필요합니다.

```python
# 예: Controller 초기화 부분에서
config = {
    "budget": 1_000_000,
    "safety": {
        "max_trade_amount": 200_000,
        "max_daily_trades": 10,
        "max_loss_ratio": -0.10,
    },
    # ...
}
operator = LlmOperator(llm_client, config)
```

상세 필드는 [`architecture.md`](architecture.md#safetyguard) 또는 `smtm/llm/safety_guard.py`의 `SafetyConfig`를 참고하세요.

---

## 6. 자주 쓰는 운영 팁

- **백그라운드 실행**: SSH 종료 후에도 살아남도록 `nohup python -m smtm --mode 0 ... &` 또는 `tmux`/`screen` 사용.
- **로그 확인**: 기본 경로 `log/smtm.log` (2MB × 10 롤링). `tail -F log/smtm.log`로 실시간 관찰.
- **비용 모니터링**: `SystemMonitor.get_llm_usage()`로 누적 입/출력 토큰을 확인할 수 있습니다. 시장 판단 주기(`--term`)가 짧을수록 API 호출 비용이 증가합니다.
- **드라이런**: 실주문 이전에 `tests/e2e_tests/`에서 `FakeTrader`로 전체 흐름을 검증할 수 있습니다 (자세한 내용은 README의 Testing 섹션).

---

## 7. 문제가 생기면

- 설정·실행 문제는 [`faq.md`](faq.md)의 "문제 해결 체크리스트" 섹션
- 내부 흐름이 궁금하면 [`architecture.md`](architecture.md)
- 버전별 알려진 이슈·변경점은 [`release-notes.md`](release-notes.md)
