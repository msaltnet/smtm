# 지원 거래소와 매매 가이드

smtm은 이제 **Upbit·Bithumb·Binance** 세 거래소에서 실거래가 가능하며, 어떤 설정이든 **가상거래(페이퍼 트레이딩)**로 먼저 검증할 수 있습니다. 이 문서는 각 거래소의 사용법과 주의사항을 정리합니다.

> 모든 제어는 텔레그램 챗봇의 AI Agent와의 대화로 이뤄집니다. 예산·통화·거래소·전략·주기는 **프로파일/세션 설정값**입니다(명령행 플래그 아님).

## 한눈에 보기

| 코드 | 거래소 | 결제 통화 | 지원 코인 | 실거래 | 비고 |
|------|--------|-----------|-----------|:------:|------|
| `UPB` | Upbit | KRW | BTC, ETH, DOGE, XRP | ✅ | 기본값 |
| `BTH` | Bithumb | KRW | BTC, ETH | ✅ | |
| `BNC` | Binance | **USDT** | BTC, ETH, DOGE, XRP | ✅ | **신규** — 예산·금액이 USDT 기준 |
| (가상) | Simulation | 프로파일 예산 통화 | 선택한 코인 | 가상 | `virtual: true`면 어느 코드든 인메모리 시뮬레이터로 실행 |

> 뉴스·소셜·온체인 등 **복합 데이터 소스 코드**(`UPN`/`UMN`/`USC`/`UFC`/`UBD` 등)는 시장 데이터 확장용입니다. 실주문 실행 Trader가 연결된 코드는 현재 `UPB`/`BTH`/`BNC` 세 가지이며, 그 외 코드는 **가상거래 모드**로 사용하세요. 전체 데이터 소스 목록은 [README](../README-ko-kr.md#지원-거래소-및-데이터-제공자)를 참고하세요.

## 지원하는 주문 유형

| 주문 유형 | Upbit / Bithumb / Binance (실거래) | 가상거래(Simulation) |
|-----------|:---:|:---:|
| 지정가 (limit) | ✅ | ✅ |
| 시장가 (market) | ✅ | ✅ |
| 손절 / 익절 (stop-loss / take-profit) | ⏳ 예정 | ✅ (로컬 에뮬레이션) |
| OCO / 트레일링 | ⏳ 예정 | ⏳ 예정 |

- **시장가/지정가**는 세 거래소 모두에서 동작합니다. (요청에 `ord_type` 필드가 없으면 기존과 동일하게 지정가로 처리 — 하위호환)
- **손절/익절**은 현재 가상거래에서 매 틱 시세로 트리거를 검사해 발동하도록 에뮬레이션됩니다. 실거래소의 네이티브 조건부 주문(Binance stop/OCO 등)과 세션 단위 자동 손절/익절 정책은 후속 작업에서 제공될 예정입니다.

## 환경변수 설정

프로젝트 루트 `.env`(또는 환경변수)에 사용할 거래소의 키를 설정합니다.

```bash
# 필수: LLM API 키
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit (거래소 코드 UPB)
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb (거래소 코드 BTH)
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# Binance (거래소 코드 BNC) — 현물(spot)
BINANCE_API_ACCESS_KEY=your_binance_access_key
BINANCE_API_SECRET_KEY=your_binance_secret_key
BINANCE_API_SERVER_URL=https://api.binance.com
```

> 실거래 계좌는 키 '값'이 아니라 키가 담긴 **환경변수 이름**으로 등록합니다(`register_account`). 키 원문은 저장되지 않습니다.

## 매매 세션 만드는 법 (채팅)

기본으로 뜨는 `default` 세션은 **가상거래**입니다. 실거래를 하려면 채팅으로 다음을 진행합니다.

1. `register_account` — 거래소에 맞는 계좌를 환경변수 이름으로 등록
2. `create_profile` — `exchange`/`currency`/`budget`/`strategy`/`term`과 `virtual: false`, `account` 지정
3. `create_session` + `start_session` — 그 프로파일로 세션 생성·시작

### 예시 — Upbit (KRW)

```
upbit-btc 프로파일 만들어줘: 거래소 UPB, 통화 BTC, 예산 500000, 전략 RSI, 주기 60초, 실거래(virtual false), 계좌 my-upbit
upbit-btc로 세션 만들고 시작해줘
```

### 예시 — Binance (USDT)

```
binance-eth 프로파일 만들어줘: 거래소 BNC, 통화 ETH, 예산 300, 전략 SMA, 주기 60초, 실거래(virtual false), 계좌 my-binance
binance-eth로 세션 만들고 시작해줘
```

> Binance는 **USDT 페어**(BTCUSDT 등)로 거래하므로 `budget`과 모든 금액이 **USDT 기준**입니다. 위 예시의 `300`은 300 USDT입니다.

### 예시 — 가상거래로 먼저 검증

```
sim-btc 프로파일 만들어줘: 거래소 BNC, 통화 BTC, 예산 1000, 전략 RSI, 주기 60초, 가상거래(virtual true)
sim-btc로 세션 만들고 시작해줘
포트폴리오 보여줘
```

## 주의사항

- **Binance는 USDT 기준**: 예산·수익·거래금액이 모두 USDT입니다. KRW 거래소(Upbit/Bithumb)와 숫자를 혼동하지 마세요.
- **⚠️ USDT 세션의 안전장치 설정**: `SafetyGuard`의 금액 기반 기본값(`max_trade_amount=100000`, `initial_budget`)은 **KRW 전제**입니다. Binance(USDT) 세션은 프로파일의 `safety` 설정에서 **반드시 USDT 기준 값으로 지정**하세요. (거래소별 통화 인지형 기본값은 후속 과제)
- **시장가 매수 의미 차이**: 시장가 매수 시 Upbit/Binance는 "총액 지출"(price×amount) 기준으로 동작합니다. 시장가 매도는 세 거래소 모두 "수량" 기준입니다.
- **API 호출 한도**: 세션마다 거래소를 독립적으로 폴링하므로 소수의 세션 운영을 전제로 합니다.
- **수수료**: 가상거래 수수료는 0이며, 실거래 수수료 비율은 거래소별로 다릅니다(로컬 수익 계산용 값).

## 관련 문서

- 전체 데이터 소스·거래소 표: [README (한국어)](../README-ko-kr.md)
- 설계/구현 배경: `docs/superpowers/specs/2026-07-14-order-types-and-binance-trader-design.md`
