# smtm — User Guide

이 문서는 smtm을 **처음 설치하고 자동매매까지 돌려보려는 사용자**를 위한 실행 가이드입니다. 설치 → 환경변수 → 텔레그램 봇 실행 → 대표 시나리오 순서로 설명합니다.

smtm의 제어 채널은 **텔레그램 챗봇 하나**입니다. 예산·통화·거래소·주기·전략 같은 설정은 명령행 플래그가 아니라 **채팅으로 만드는 프로파일/세션 설정값**입니다.

- 최종 갱신일: 2026-04-20
- 기준 버전: 1.7.1

---

## 1. 시작하기

### 1.1 사전 준비물

| 항목 | 설명 |
|------|------|
| Python 3.9+ | `python --version`으로 확인 |
| Anthropic Claude API 키 | [Anthropic Console](https://console.anthropic.com) 발급, `SMTM_LLM_API_KEY`로 주입 |
| 거래소 API 키 | Upbit 또는 Bithumb (실주문용). 가상거래만 할 거라면 없어도 됩니다. |
| 텔레그램 Bot | **필수.** BotFather로 토큰 발급, `chat_id` 확인 |

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

# Upbit (거래소 코드 UPB)
UPBIT_OPEN_API_ACCESS_KEY=...
UPBIT_OPEN_API_SECRET_KEY=...
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb (거래소 코드 BTH)
BITHUMB_API_ACCESS_KEY=...
BITHUMB_API_SECRET_KEY=...
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# 텔레그램 (--token / --chatid 로 대신 넘겨도 됨)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## 2. 실행

### 2.1 텔레그램 챗봇 실행

smtm의 유일한 실행 방법입니다.

```bash
python -m smtm --token <bot_token> --chatid <chat_id>
```

`--token` / `--chatid`를 생략하면 환경변수 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`를 사용합니다. 사용 가능한 토큰이 없으면 다음을 출력하고 정상 종료합니다.

```
Please check your telegram chat-bot token
```

정상 기동하면 콘솔에 다음이 출력됩니다.

```
##### smtm telegram LLM controller is started #####
'start'를 입력하면 default 세션 매매가 시작됩니다
default 세션은 가상거래입니다 - 실제 주문은 전송되지 않습니다
실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요
```

- 지정된 `chat_id`의 메시지만 수용합니다 (다른 사람이 봇에 말 걸어도 무시).
- 수용된 모든 메시지는 LLM 에이전트에 전달됩니다.

| 텔레그램 입력 | 동작 |
|------|------|
| `start` | `default` 세션의 자동 매매 타이머 시작 (`term` 설정값 주기로 매매 루프 실행) |
| `stop` | 타이머 중지 (대화는 계속 가능) |
| 그 외 자유 입력 | LLM에 메시지 전달, Tool use 루프 실행 후 응답을 텔레그램으로 회신 |

프로세스 종료는 서버에서 `Ctrl+C`(SIGINT) 또는 SIGTERM으로 합니다.

### 2.2 기본은 가상거래 (페이퍼 트레이딩)

프로세스와 함께 뜨는 `default` 세션은 **가상거래 세션**입니다. 실시간 시세를 쓰지만 잔고는 가상이고, 주문이 거래소로 나가지 않습니다. 거래소 API 키가 없어도 바로 돌려볼 수 있습니다.

**실거래를 하려면 채팅으로** 아래 3단계를 거쳐야 합니다. 명령행 플래그로는 실거래를 켤 수 없습니다.

1. **계좌 등록** — `register_account`. API 키 '값'이 아니라 키가 담긴 **환경변수 이름**을 등록합니다.
2. **프로파일 생성** — `create_profile`. `virtual: false`와 위에서 등록한 `account`를 지정합니다.
3. **세션 생성·시작** — `create_session` → `start_session`.

### 2.3 Jupyter Notebook

노트북에서는 `JptController`로 동일한 오퍼레이터를 직접 띄울 수 있습니다. (실행 진입점이 아니라 노트북 전용 유틸리티입니다.)

```python
from smtm import JptController
controller = JptController(interval=60, budget=500000, currency="BTC", exchange="UPB")
controller.initialize()
# 이후 셀에서 controller.operator.chat("시장 상황 알려줘") 등으로 호출
```

---

## 3. 명령행 옵션 요약

명령행 옵션은 텔레그램 접속과 로그에 관한 것뿐입니다. 매매 관련 설정은 전부 채팅으로 합니다.

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--token` | 텔레그램 Bot 토큰 | 환경변수 `TELEGRAM_BOT_TOKEN` |
| `--chatid` | 텔레그램 chat id | 환경변수 `TELEGRAM_CHAT_ID` |
| `--log` | 로그 파일명 변경 | None (기본 `log/smtm.log`) |
| `--version` | 버전 출력 후 종료 | - |

### 3.1 채팅으로 설정하는 값 (프로파일/세션 설정값)

| 설정값 | 설명 | 기본(`default` 세션) |
|--------|------|--------|
| `budget` | 거래 예산 (KRW) | 500000 |
| `currency` | 거래 통화 (예: `BTC`, `ETH`) | BTC |
| `exchange` | 거래소 코드 (`UPB` / `BTH` 등) | UPB |
| `term` | 자동 매매 틱 주기 (초) | 60 |
| `strategy` | 전략 코드 (`BNH` / `RSI` / `SMA` / `LLM`) | BNH |
| `virtual` | 가상거래 여부 | true (가상거래) |
| `account` | 실거래에 사용할 등록 계좌 별칭 | 없음 |

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

모든 시나리오는 봇을 띄운 뒤 **텔레그램 채팅**으로 진행합니다.

```bash
python -m smtm --token <bot_token> --chatid <chat_id>
```

### 시나리오 1 — 처음 접속해서 시장만 살펴보기

1. 봇을 띄우고 텔레그램에서 `시장 상황 알려줘` 전송
2. LLM이 `get_market_data`를 호출한 뒤 요약해 답변
3. 아직 매매는 시작하지 않음 — `start`를 보내지 않았기 때문에 타이머 미가동

### 시나리오 2 — 가상거래로 자동 매매 시작하고 지켜보기

1. 위 상태에서 `start` 전송 → `default`(가상거래) 세션의 매매 타이머가 시작됨
2. `term` 설정값 주기(기본 60초)마다 매매 루프가 돌아감
3. 매 틱에서 시장 데이터를 확인하고, 필요하다고 판단되면 매수/매도를 실행 (가상계좌에만 반영)
4. 사용자는 아무 때나 대화에 개입 가능: "지금은 매수하지 마", "일단 관망해줘"
5. 한도를 넘는 주문은 SafetyGuard가 거부하고 LLM이 사유("1회 최대 거래금액 초과 …")를 받아 재판단

### 시나리오 3 — 잠깐 멈추고 성과 확인

1. `stop` → 타이머 중지 (봇 연결·대화는 유지)
2. `오늘 수익률 알려줘` 전송 → LLM이 `get_performance` 호출 후 수익률 응답
3. `최근 거래 5건만 보여줘` 전송 → `get_trade_history`로 내역 출력
4. 다시 돌리고 싶으면 `start`

### 시나리오 4 — 채팅으로 설정 바꿔서 새 세션 돌리기

예산·통화·거래소·주기·전략은 채팅으로 프로파일을 만들어 지정합니다.

```
RSI 전략으로 UPB에서 BTC를, 예산 300000, 주기 300초, 가상거래로 하는 rsi-btc 프로파일 만들어줘
rsi-btc로 세션 만들어서 시작해줘
세션 목록 보여줘
세션별 성과 비교해줘
```

에이전트가 `create_profile` → `create_session` → `start_session` → `list_sessions` / `compare_performance` Tool을 순서대로 호출합니다. 여러 세션을 동시에 돌릴 수 있습니다.

### 시나리오 5 — 실거래로 전환하기

가상거래가 기본이므로, 실거래는 **명시적으로** 계좌를 등록해야 합니다.

1. 거래소 키를 환경변수에 넣고 프로세스를 띄웁니다 (예: `SMTM_KEY_1`, `SMTM_SECRET_1`).
2. 텔레그램에서: `UPB 계좌를 my-upbit 이름으로 등록해줘. 액세스 키 환경변수는 SMTM_KEY_1, 시크릿은 SMTM_SECRET_1이야`
   → `register_account` 호출. **키 값 자체를 채팅에 붙여넣지 마세요.** 환경변수 '이름'만 등록됩니다.
3. `my-upbit 계좌로 실거래하는 real-btc 프로파일 만들어줘. UPB, BTC, 예산 500000, 가상거래 아님`
   → `create_profile`(`virtual: false`, `account: my-upbit`)
4. `real-btc로 세션 만들고 시작해줘` → `create_session` + `start_session`

세션별 예산은 실제 계좌 잔고와 대조 검증되고, 같은 계좌를 공유하는 세션에는 계좌 단위 일일 거래 한도 가드가 함께 적용됩니다.

### 시나리오 6 — 안전장치 기본값이 너무 타이트해서 조정

프로파일의 `safety` 설정값으로 세션별 한도를 지정할 수 있습니다.

```
real-btc 프로파일의 안전장치를 1회 최대 200000원, 하루 10회, 손실 한도 -10%로 바꿔줘
```

코드 레벨에서 기본값을 바꾸려면 `SystemOperator` 생성 시 `config["safety"]` dict로 주입합니다.

```python
config = {
    "budget": 1_000_000,
    "safety": {
        "max_trade_amount": 200_000,
        "max_daily_trades": 10,
        "max_loss_ratio": -0.10,
    },
    # ...
}
operator = SystemOperator(llm_client, config)
```

상세 필드는 [`architecture.md`](architecture.md#safetyguard) 또는 `smtm/llm/safety_guard.py`의 `SafetyConfig`를 참고하세요.

---

## 6. 자주 쓰는 운영 팁

- **백그라운드 실행**: SSH 종료 후에도 살아남도록 `nohup python -m smtm --token <bot_token> --chatid <chat_id> &` 또는 `tmux`/`screen` 사용.
- **로그 확인**: 기본 경로 `log/smtm.log` (2MB × 10 롤링). `tail -F log/smtm.log`로 실시간 관찰.
- **비용 모니터링**: `SystemMonitor.get_llm_usage()`로 누적 입/출력 토큰을 확인할 수 있습니다. 매매 주기(`term` 설정값)가 짧을수록, 그리고 동시 실행 세션이 많을수록 API 호출 비용이 증가합니다.
- **세션 수 관리**: 세션마다 거래소를 독립적으로 폴링하므로, 거래소 API 호출 한도를 고려해 세션 수를 적게 유지하세요.
- **드라이런**: 실거래 이전에 `default` 가상거래 세션으로 전체 흐름을 확인하거나, `tests/e2e_tests/`에서 Fake 구현으로 검증할 수 있습니다 (자세한 내용은 README의 Testing 섹션).

---

## 7. 문제가 생기면

- 설정·실행 문제는 [`faq.md`](faq.md)의 "문제 해결 체크리스트" 섹션
- 내부 흐름이 궁금하면 [`architecture.md`](architecture.md)
- 버전별 알려진 이슈·변경점은 [`release-notes.md`](release-notes.md)
