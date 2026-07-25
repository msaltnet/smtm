# OKX 거래소 지원 설계 (DataProvider + Trader)

- 작성일: 2026-07-25
- 상태: **사용자 리뷰 대기**
- 관련 파일: `smtm/data/okx_data_provider.py`(신규), `smtm/trader/okx_trader.py`(신규),
  `smtm/data/data_provider_factory.py`, `smtm/trader/trader_factory.py`,
  `smtm/account_store.py`, `smtm/llm/tools/account_tools.py`, `smtm/__init__.py`
- 선행 스펙: [2026-07-14 주문 유형 + BinanceTrader](2026-07-14-order-types-and-binance-trader-design.md)

---

## 1. 배경

smtm은 거래소별로 `DataProvider`(시장 데이터)와 `Trader`(주문 실행)를 한 쌍으로 두고,
동일한 **거래소 코드**로 둘을 함께 지정한다. 현재 실주문 Trader가 존재하는 거래소는
Upbit(`UPB`) · Bithumb(`BTH`) · Binance(`BNC`) 세 곳이다.

Binance 지원 작업에서 `BaseExchangeTrader`(공통 워커/타이머/잔고 갱신/HTTP)와
`BaseDataProvider`(공통 HTTP)가 이미 추출되어 있어, 새 거래소 추가 비용은
**거래소 고유의 인증·엔드포인트·응답 파싱**으로 국한된다.

### OKX v5가 Binance와 다른 지점

구조(현물 REST, 캔들 + 주문/조회/취소)는 유사하지만 다음이 다르다. 설계 결정의 근거이므로 명시한다.

| 항목 | Binance (기존 구현) | OKX v5 |
|---|---|---|
| 심볼 | `BTCUSDT` | `BTC-USDT` (`instId`) |
| 인증 | HMAC-SHA256 **hex**, 서명된 query string | `base64(HMAC-SHA256(ISO타임스탬프 + METHOD + requestPath + body))` |
| 자격증명 | access + secret (2개) | access + secret + **passphrase (3개)** |
| 주문 전송 | signed query string, `POST /api/v3/order` | **JSON 바디**, `POST /api/v5/trade/order` (`tdMode=cash`) |
| 주문 취소 | `DELETE /api/v3/order` | `POST /api/v5/trade/cancel-order` |
| 응답 | 결과 객체 직접 반환 | `{"code":"0","msg":"","data":[...]}` **봉투** |
| 오류 표현 | HTTP 4xx/5xx | **HTTP 200 + `code!=0`**, 상세는 `data[0].sCode`/`sMsg` |
| 캔들 정렬 | 오래된 순 | **최신 순(내림차순)** |
| 캔들 주기 | `1m/3m/5m/15m/30m/...` | `1m/3m/5m/15m/30m/...` (**둘 다 10m 없음**) |
| 가상 환경 | 별도 testnet 도메인 | 동일 도메인 + `x-simulated-trading: 1` 헤더 |

시장가 매수의 "총액 지정"은 Binance `quoteOrderQty` ↔ OKX `tgtCcy=quote_ccy`로 1:1 대응된다.

---

## 2. 목표 / 비목표

### 목표

1. **`OkxDataProvider`** — OKX 현물 캔들 조회. public 엔드포인트로 인증 불필요.
2. **`OkxTrader`** — OKX 현물(spot) 지정가/시장가 주문, 계좌·시세 조회, 주문 상태 폴링, 취소.
3. **passphrase 배선** — `AccountStore`에 계좌별 passphrase 환경변수 이름을 등록할 수 있게 확장.
   기존 계좌 파일(3필드)의 하위호환을 깨지 않는다.
4. **데모 거래 스위치** — 환경변수 하나로 OKX 데모 환경에 붙어 실주문 경로를 무비용 검증.
5. 거래소 코드 **`OKX`** 하나로 데이터·주문 모두 사용 가능.

### 비목표 (이번 범위 밖)

- OKX **선물/스왑/마진** — `tdMode=cross|isolated`, 레버리지·청산 개념이 현물 가정과 충돌. 별도 과제.
- **`instruments` 기반 정밀 라운딩** — `lotSz`/`tickSz`/`minSz` 준수. Binance와 동일한 기존 미해결 과제
  (§6 참조). 이번엔 Binance와 같은 수준(`_format_number`)까지만 맞춘다.
- **`BaseExchangeTrader`/`BaseDataProvider` 수정** — 기존 3개 Trader 회귀 위험을 만들지 않는다.
  (`Trader` 추상클래스에 클래스 상수 `USES_PASSPHRASE = False` 하나를 추가하는 것은 예외다.
  기존 `SUPPORTED_ORD_TYPES`와 같은 additive 확장이며 동작을 바꾸지 않는다. §4 참조.)
- **`BinanceTrader`의 종료 상태 결함 수정** — §6에 후속 과제로 기록.
- **거래소별 통화 인지형 `SafetyConfig` 기본값** — Binance 때부터의 기존 과제(§6).

---

## 3. 구조 (A안: 독립 파일 2개)

거래소 3종(Upbit/Bithumb/Binance) Trader가 모두 인증 로직을 **자기 클래스 안에** 두는 기존 패턴을
따른다. OKX 하나만 별도 클라이언트 모듈로 분리하면 코드베이스에 두 가지 패턴이 공존하게 되고,
DataProvider는 public 엔드포인트라 실제 공유분이 봉투 해제 몇 줄뿐이므로 이득이 비용보다 작다.

### 신규 파일

| 파일 | 클래스 | `CODE` | `NAME` |
|---|---|---|---|
| `smtm/data/okx_data_provider.py` | `OkxDataProvider(BaseDataProvider)` | `"OKX"` | `"OKX DP"` |
| `smtm/trader/okx_trader.py` | `OkxTrader(BaseExchangeTrader)` | `"OKX"` | `"OKX"` |

`CODE`를 DataProvider와 Trader가 공유하는 것은 `BNC`와 동일한 기존 규약이다.

### 변경 파일

- `smtm/data/data_provider_factory.py` — `DataProvider_LIST`에 `OkxDataProvider` 추가
- `smtm/trader/trader_factory.py` — `TRADER_LIST`에 `OkxTrader` 추가 + passphrase 전달(§4)
- `smtm/__init__.py` — `OkxDataProvider`, `OkxTrader` export
- `smtm/trader/__init__.py` — `OkxTrader` export (기존 `BinanceTrader` 스타일 유지)
- `smtm/trader/trader.py` — `Trader`에 클래스 상수 `USES_PASSPHRASE = False` 추가(§4).
  기존 `SUPPORTED_ORD_TYPES` 기본값과 같은 자리·같은 패턴
- `smtm/account_store.py` — `passphrase_env` 옵셔널 필드(§4)
- `smtm/llm/tools/account_tools.py` — `register_account` 스키마에 `passphrase_env`(옵셔널)

### 지원 통화

Binance와 동일하게 맞춘다(4종 모두 OKX USDT 현물 상장).

```python
AVAILABLE_CURRENCY = {
    "BTC": ("BTC-USDT", "BTC"),
    "ETH": ("ETH-USDT", "ETH"),
    "DOGE": ("DOGE-USDT", "DOGE"),
    "XRP": ("XRP-USDT", "XRP"),
}
```

`OkxDataProvider`는 Binance DP와 동일하게 `{"BTC": "BTC-USDT", ...}` 단일 값 형태를 쓴다.

---

## 4. 자격증명 · 환경변수 · passphrase 배선

### 환경변수

| 이름 | 필수 | 기본값 | 용도 |
|---|---|---|---|
| `OKX_API_ACCESS_KEY` | ✅ | — | API Key |
| `OKX_API_SECRET_KEY` | ✅ | — | Secret Key (서명용) |
| `OKX_API_PASSPHRASE` | ✅ | — | API 생성 시 지정한 passphrase |
| `OKX_API_SERVER_URL` | — | `https://www.okx.com` | 엔드포인트 |
| `OKX_API_DEMO` | — | (미설정) | `1`/`true`/`yes`면 데모 거래 헤더 부가 |

`BaseExchangeTrader.__init__`은 `env_key_names=(access, secret, server_url)` 3-튜플만 받으므로,
passphrase는 `OkxTrader.__init__`에서 `super().__init__()` 호출 후 직접 읽는다.
`SERVER_URL` 기본값 주입도 `BinanceTrader`와 같은 방식(`if not self.SERVER_URL:`)을 쓴다.

```python
def __init__(self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True,
             access_key_env=None, secret_key_env=None, passphrase_env=None):
    ...
    super().__init__(..., env_key_names=(
        access_key_env or "OKX_API_ACCESS_KEY",
        secret_key_env or "OKX_API_SECRET_KEY",
        "OKX_API_SERVER_URL",
    ))
    if not self.SERVER_URL:
        self.SERVER_URL = "https://www.okx.com"
    self.PASSPHRASE = os.environ.get(passphrase_env or "OKX_API_PASSPHRASE", "")
    if not self.PASSPHRASE:
        self.logger.warning("OkxTrader passphrase is not set")
    self.is_demo = os.environ.get("OKX_API_DEMO", "").lower() in ("1", "true", "yes")
```

`commission_ratio` 기본값은 OKX 현물 일반 등급 taker 수수료에 맞춰 `0.001`(Binance와 동일).

### `_validate_credentials()` 오버라이드

기반 클래스는 access/secret/server_url 3개만 검사하므로 passphrase 검사를 덧붙인다.
서명이 필요한 모든 경로(`_send_order`, `_query_order`, `_cancel_order`)가 이 함수를 통과하므로
passphrase 누락 시 주문이 전송되지 않는다.

```python
def _validate_credentials(self):
    if not super()._validate_credentials():
        return False
    if not self.PASSPHRASE:
        self.logger.error("OKX passphrase is not configured")
        return False
    return True
```

### `AccountStore` 확장

- `ALLOWED_FIELDS`에 `"passphrase_env"` **추가**
- `REQUIRED_FIELDS`는 **변경하지 않음** — 기존 Upbit/Bithumb/Binance 계좌 파일(3필드)이
  `validate()`를 계속 통과해야 한다. OKX 계좌에서 passphrase를 빠뜨리면 `AccountStore`가 아니라
  `OkxTrader._validate_credentials()`가 주문 시점에 막는다.
- `ENV_NAME_PATTERN` 검증 루프에 `passphrase_env` 포함 (값이 있을 때만 — 기존 루프도 동일 구조)
- `missing_env_vars()` — `passphrase_env`가 **등록되어 있을 때만** 미설정 여부를 검사.
  등록되지 않은 계좌를 "누락"으로 보고하면 기존 계좌가 전부 `env_ready=false`가 된다.
- `list_accounts()` 요약에 `passphrase_env` 포함
- `save()`의 중복 계좌 검사는 access/secret 쌍 기준을 **유지** — 같은 access/secret을 쓰면
  passphrase가 다르더라도 사실상 같은 계좌다.

교차 필드 검증(예: "`exchange`가 `OKX`가 아니면 `passphrase_env` 거부")은 하지 않는다.
`AccountStore`는 거래소 코드의 의미를 모르는 순수 레지스트리로 유지한다.

### `TraderFactory` 전달

`passphrase_env`를 무조건 넘기면 이를 받지 않는 Upbit/Bithumb/Binance Trader에서 `TypeError`가 난다.
`Trader` 기반 클래스에 `USES_PASSPHRASE = False`를 두고 `OkxTrader`만 `True`로 선언한다.

```python
if account.get("passphrase_env") and getattr(trader, "USES_PASSPHRASE", False):
    kwargs["passphrase_env"] = account["passphrase_env"]
```

`getattr` 기본값을 함께 쓰는 이유는 `Trader` 서브클래스가 플래그를 선언하지 않아도 안전하게
동작하도록 하기 위함이다.

---

## 5. 컴포넌트 상세

### 5.1 `OkxDataProvider`

`GET /api/v5/market/candles?instId=BTC-USDT&bar=1m&limit=1` (public, 무인증)

**interval 매핑** — `60→"1m"`, `180→"3m"`, `300→"5m"`, 그 외는 `UserWarning`.
`600`은 OKX `bar` 목록에 없으므로 **거부한다**. `15m`으로 대체 매핑하면 요청한 것과 다른
주기의 데이터를 조용히 반환하게 되므로 하지 않는다.

> **기록**: `BinanceDataProvider`는 `600 → "10m"`으로 매핑하지만 Binance 역시 `10m` interval이
> 없어 실제로는 실패한다. 기존 결함이며 이번 범위 밖이다(§6).

**응답 봉투** — `code != "0"`이면 `msg`를 로깅하고 `UserWarning`을 발생시킨다.
`BaseDataProvider._get_data_from_server`가 실패를 `UserWarning`으로 올리는 기존 규약과 일치시킨다.

**캔들 배열 인덱스** (OKX는 배열, Binance와 인덱스가 다름)

```
[0] ts (unix ms, 캔들 시작)   → date_time (KST ISO)
[1] o  → opening_price
[2] h  → high_price
[3] l  → low_price
[4] c  → closing_price
[5] vol      (base ccy 수량)  → acc_volume
[6] volCcy   (quote ccy 금액) → acc_price
[7] volCcyQuote  (현물에서는 [6]과 동일) — 미사용
[8] confirm  ("0" 미완성 / "1" 완성) — 미사용
```

`limit=1`은 **진행 중인 최신 캔들**을 반환한다. 최신순 정렬이지만 1건만 받으므로
`data[0]`이 곧 최신이고, `BinanceDataProvider`의 동작(진행 중 캔들 반환)과 동일하다.
정렬 차이를 별도로 보정할 필요가 없다.

반환 스키마는 기존 DataProvider 계약(`type="primary_candle"`, `market`, `date_time`,
`opening_price`, `high_price`, `low_price`, `closing_price`, `acc_price`, `acc_volume`)을 그대로
따르고, KST 변환은 `DateConverter.to_iso_string`을 쓴다.

### 5.2 `OkxTrader` — 서명

```python
# OKX 타임스탬프는 밀리초 3자리 UTC ISO8601 (예: 2026-07-25T09:08:57.715Z)
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
prehash   = timestamp + method.upper() + request_path + body   # body는 GET이면 ""
sign      = base64.b64encode(
    hmac.new(self.SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).digest()
).decode()
```

- `request_path`는 **쿼리스트링을 포함한** 경로다. 예: `/api/v5/trade/order?instId=BTC-USDT&ordId=123`
  → 서명 문자열과 실제 요청 URL의 쿼리가 **정확히 일치**해야 한다. 따라서 서명이 필요한 GET은
  `urlencode`로 쿼리를 한 번 만들어 `request_path`에 붙이고, **같은 문자열이 붙은 전체 URL**을
  `_request_get(url, headers=...)`에 `params` 없이 넘긴다. `requests`의 `params=`에 dict를 넘기면
  인코딩 결과가 서명과 달라질 수 있다.
- 서명이 불필요한 public GET(캔들·시세)은 기존처럼 `params=` dict를 써도 무방하다.
- 헤더:
  ```
  OK-ACCESS-KEY, OK-ACCESS-SIGN, OK-ACCESS-TIMESTAMP, OK-ACCESS-PASSPHRASE
  Content-Type: application/json
  x-simulated-trading: 1   # is_demo 일 때만
  ```
- POST는 JSON **문자열**을 만들어 서명하고, 같은 문자열을 `_request_post(data=...)`로 보낸다.
  dict를 따로 직렬화하면 서명과 바디가 달라질 수 있으므로 **한 번 만든 문자열을 재사용**한다.

### 5.3 `OkxTrader` — 봉투 해제 `_unwrap`

OKX는 업무 오류를 HTTP 200으로 반환하므로 기반 클래스의 `_request_get`/`_request_post`(HTTP 오류만
`None`)만으로는 실패를 감지할 수 없다. 실패가 최상위 `code`와 `data[0].sCode` 두 층에 나뉘고,
최상위 `code="1"`일 때 구체적 사유는 `data[0].sMsg`에만 담긴다.

```
_unwrap(response):
    response is None                       → None
    str(code) != "0"                       → data[0].sMsg 우선(없으면 msg) 로깅 → None
    data 가 비어있음                        → None
    data[0]이 dict이고 sCode가 있고 != "0"  → sMsg 로깅 → None
    그 외                                   → data[0]
```

서명 GET/POST의 모든 호출부가 `_unwrap`을 통과하도록 한다.

### 5.4 `OkxTrader` — 시세 · 계좌

- `get_trade_tick()` — `GET /api/v5/market/ticker?instId=...` (public) → `_unwrap` → `data[0]`
- `get_account_info()` — `BinanceTrader`와 동일. 로컬 `balance`/`asset` + 실시간 시세(`last` 필드).
  잔고를 거래소에서 재조회하지 않고 로컬 상태를 신뢰하는 기존 설계를 그대로 따른다.

### 5.5 `OkxTrader` — 주문 전송

`POST /api/v5/trade/order`, `tdMode="cash"`(현물 비마진)

| 유형 | 바디 |
|---|---|
| 지정가 | `ordType="limit"`, `px=가격`, `sz=수량` |
| 시장가 매수 | `ordType="market"`, `tgtCcy="quote_ccy"`, `sz=price*amount` (**USDT 총액**) |
| 시장가 매도 | `ordType="market"`, `tgtCcy="base_ccy"`, `sz=amount` (**코인 수량**) |

`tgtCcy`는 현물 시장가에서 기본값이 방향에 따라 달라지므로 **양쪽 모두 명시**한다.

성공 응답 `data[0]`에서 `ordId`를 꺼내 `order_map`에 저장한다. `ordId`가 없으면 실패로 처리한다.

`_execute_order`의 나머지 흐름은 `BinanceTrader`와 동일하게 유지한다:

- `type == "cancel"` → `cancel_request` 위임
- `order_spec.get_ord_type(request)`가 `SUPPORTED_ORD_TYPES = {"limit", "market"}`에 없으면
  `order_spec.make_rejected_result`로 거부
- 지정가에서 `price == 0`이면 **기존 no-op(hold) 신호**이므로 경고 후 무시
- 매수 시 `price * amount > balance`면 거부, 매도 시 `amount > asset[1]`이면 거부

`_format_number`는 `BinanceTrader`와 동일하게 지수표기 없는 고정소수점 문자열을 만든다
(최대 8자리 소수, 불필요한 0 제거). OKX도 `sz`/`px`를 문자열로 받으며 `1e-05` 같은 표기를 거부한다.

### 5.6 `OkxTrader` — 주문 상태 폴링

`GET /api/v5/trade/order?instId=...&ordId=...` (서명) → `_unwrap` → `state` 분기

| `state` | 처리 |
|---|---|
| `live`, `partially_filled` | `order_map`에 유지, 타이머 재시작 |
| `filled` | `avgPx`(체결 평단), `accFillSz`(체결 수량)로 `state="done"` 콜백 후 제거 |
| `canceled`, `mmp_canceled` | **종료 상태 — `order_map`에서 제거**하고 `accFillSz`(미체결이면 0)로 `done` 콜백 |
| 조회 실패(`None`) | `order_map`에 유지 (일시적 오류일 수 있음) |

`canceled`를 종료로 처리하는 이유: 남겨두면 주문이 이미 오더북에서 사라졌는데도 타이머가 영구
폴링한다. `_call_callback`은 `price * amount == 0`일 때 자산·잔고를 변경하지 않으므로
미체결 취소를 `amount=0`으로 콜백해도 회계가 오염되지 않는다.

체결 단가는 `avgPx`를 우선 사용하고, 비어 있으면 `0`으로 둔다. Binance처럼
`체결총액/체결수량`을 직접 계산할 필요가 없다 — OKX가 `avgPx`를 직접 제공한다.

### 5.7 `OkxTrader` — 주문 취소

`POST /api/v5/trade/cancel-order`, 바디 `{"instId": ..., "ordId": ...}` (**DELETE가 아님**)

**Binance와 다른 핵심 차이**: OKX의 취소 응답은 `{ordId, clOrdId, sCode, sMsg}`뿐이고
**체결 정보(`accFillSz`/`avgPx`)를 담지 않는다.** Binance의 `DELETE /api/v3/order`는 체결 정보를
주므로 그 응답을 그대로 결과로 썼지만, OKX는 **취소 성공/실패와 무관하게 항상 `_query_order`로
최종 상태를 재조회**해야 한다.

`cancel_request(request_id)` 흐름: `order_map`에서 제거 → 취소 요청 → `_query_order`로 최종 상태
확정 → `done` 콜백(`avgPx`/`accFillSz` 기준). 재조회까지 실패하면 콜백 없이 에러 로깅만 한다.

취소 실패는 **이미 체결됐을 가능성**을 포함한다. OKX는 이미 체결/취소된 주문에 `sCode=51400` 계열
오류를 주므로 `_unwrap`이 `None`을 반환하지만, 어차피 항상 재조회하므로 성공·실패 경로가 같다.

`cancel_all_requests()`는 기반 클래스 구현을 그대로 사용한다.

---

## 6. 알려진 한계 · 후속 과제

이번 범위에서 **고치지 않지만** 반드시 기록해 둘 항목들.

1. **`lotSz`/`tickSz`/`minSz` 정밀 라운딩 부재** — `GET /api/v5/public/instruments` 조회와 심볼별
   필터 캐시가 필요하다. 현재는 `_format_number`(고정소수점 8자리)까지만 적용하므로 소액 주문이나
   특정 심볼에서 거래소가 주문을 거부할 수 있다. **Binance와 동일한 미해결 과제**이며 두 거래소를
   함께 해결하는 것이 옳다.
2. **⚠️ USDT 세션의 안전장치 기본값** — `SafetyConfig`의 `max_trade_amount=100000`,
   `initial_budget=500000`은 **KRW 전제**다. OKX(USDT) 세션은 프로파일 `safety` 설정에서
   반드시 USDT 기준 값으로 지정해야 한다. 지정하지 않으면 사실상 한도가 없는 것과 같다.
   거래소별 통화 인지형 기본값은 Binance 때부터의 후속 과제다. → 문서에 경고만 추가한다.
3. **`BinanceTrader`의 종료 상태 결함** — `_update_order_result`가 `FILLED`만 종료로 보므로
   `CANCELED`/`EXPIRED`/`REJECTED` 주문이 `order_map`에 남아 타이머가 영구 폴링한다.
   §5.6에서 OKX는 올바르게 처리하지만 Binance 수정은 별도 과제로 둔다.
4. **`BinanceDataProvider`의 `600 → "10m"` 매핑** — Binance에 존재하지 않는 interval이라
   실제로는 실패한다. OKX는 `600`을 명시적으로 거부(§5.1)하지만 Binance 수정은 별도 과제다.
5. **데모 거래는 별도 API 키가 필요** — OKX 데모 환경은 실계정 키를 받지 않는다.
   `OKX_API_DEMO=1`로 켜면서 실계정 키를 그대로 쓰면 인증 오류가 난다. 문서에 명시한다.

### 6.1 구현 후 최종 리뷰에서 나온 이월 항목 (2026-07-25)

전체 브랜치 리뷰에서 발견됐으나 이번 세션에서 고치지 않기로 **결정한** 항목들.
1·2번은 실금액 경로이므로 다음 작업 세션의 우선 후보다.

1. **`cancel_request`의 재조회 실패 시 미아 주문** *(사용자 판단으로 이월)* —
   `cancel_request`는 취소 POST 후 `_query_order`가 `None`이면 이미 `order_map`에서 지운 주문을
   **복원하지 않고 콜백도 쏘지 않는다**(§5.7이 명시적으로 지시한 동작). 재조회가 일시적으로
   실패하면(네트워크 반짝, 429 — `cancel_all_requests`가 주문마다 취소+조회를 연속 발사하므로
   rate limit에 걸리기 쉬운 구간) 주문이 거래소에는 살아 있는데 로컬 추적에서 사라진다. 이후
   폴링도 콜백도 없고, 나중에 체결되면 로컬 잔고·자산이 거래소와 **영구 괴리**되어 이후 주문
   사이징과 `SafetyGuard` 한도가 틀린 숫자 위에서 계산된다.
   바로 옆 `_update_order_result`는 같은 `response is None` 조건에서 주문을 **유지**하므로 동일
   코드베이스가 같은 "상태 불명"을 반대로 처리하고 있다.
   수정 방향: `response is None` 분기를 비종료 분기와 동일하게 `order_map` 복원 + 타이머 재시작으로.
   폴링이 재조회해 `canceled`를 확인하면 0체결 `done`(회계 무영향)으로 안전히 정리된다.
   **함께 뒤집어야 할 것**: 본 문서 §5.7의 서술, §7의 해당 테스트 항목,
   `tests/unit_tests/okx_trader_test.py`의 `test_cancel_request_without_query_result_does_not_callback`
   (현재 `assertNotIn("ok", trader.order_map)`으로 이 동작을 못 박고 있다).

2. **`order_map` 스레드 경합 (Trader 4종 공통 기존 결함)** — `_update_order_result`는 트레이더
   워커 스레드의 타이머 콜백이고, `TradingOperator.stop()`(`smtm/trading_operator.py:58`)은
   **제어 스레드**에서 `cancel_all_requests()` → `cancel_request()`를 호출한다. 스윕이 반복마다
   네트워크 왕복을 하는 동안 취소가 `del`/재삽입하면 `RuntimeError: dictionary changed size
   during iteration`이 발생하고, 재대입에 도달하지 못한 예외가 워커로 전파된다.
   `Worker.looper`(`smtm/worker.py:77-80`)는 예외 시 `self.thread = None` 후 재던지며 **되살리는
   코드가 없어** 해당 트레이더가 영구 정지한다(매매가 조용히 멈춤).
   이번 브랜치는 순회를 `list(...)`로 감싸 크래시만 국소 차단했다. **"잃어버린 업데이트"(복원
   유실 또는 종료된 주문의 부활) 경합은 남아 있다.** 근본 해결은 `order_map`에 `threading.Lock`을
   두거나 취소도 워커 큐를 경유시키는 것이며, `binance_trader.py:132`·`bithumb_trader.py:215`·
   `upbit_trader.py:239,251`이 같은 순회 형태를 공유하므로 4종을 함께 고쳐야 한다.
   `cancel_all_requests`의 `copy.deepcopy(self.order_map)`도 같은 이유로 던질 수 있고,
   `SessionManager.stop_session`은 `operator.stop()`을 try로 감싸지 않아 그대로 전파된다.

3. **⚠️ 시장가 매수 `accFillSz` 단위 미검증 — OKX 시장가를 켜기 전 필수 확인** —
   시장가 매수는 `tgtCcy=quote_ccy`로 **USDT 총액**을 보내는데, 체결 회계는 `accFillSz`를
   **코인 수량**으로 간주한다(`_fill_amount`). OKX 현물의 `accFillSz`는 base ccy 표기이고
   `avgPx`와 짝이 맞는 것으로 이해하지만, 만약 시장가 매수에서 quote 표기로 온다면
   `_call_callback`이 자산 수량에 5000(USDT)을 더하고 평단을 50000으로 잡는 **파괴적 회계 오염**이
   된다. 지정가 경로에는 이 모호성이 없다.
   현재 어떤 전략도 `ord_type`을 만들지 않아 시장가 경로는 도달 불가이며 이것이 유일한 안전판이다.
   **데모에서 시장가 매수 1건의 `accFillSz`를 눈으로 확인하기 전까지 OKX 시장가를 켜지 말 것.**

4. **주문 조회 실패와 "그런 주문 없음"이 구분되지 않음** — `_unwrap`은 일시적 네트워크 실패와
   거래소의 "주문 없음"(top-level `code=51603`, `data=[]`)을 모두 `None`으로 뭉갠다. 후자에서
   폴링 루프는 주문을 영구 보존해 5초마다 서명 요청을 영원히 보내고 전략은 `done`을 못 받는다.
   시도 횟수 상한이 필요하다. `requirements.md`의 `[후속] R-EXEC-06`(재시도 정책)이 이 영역이다.

5. **passphrase 미등록 OKX 계좌가 `env_ready`를 통과** — `passphrase_env`를 등록하지 않은 OKX
   계좌는 `missing_env_vars()`가 아무것도 보고하지 않아 세션 생성 검증을 통과한다.
   `create_session`이 부르는 `get_account_info()`는 public 티커만 쓰므로 역시 통과한다. 그런데
   전역 `OKX_API_PASSPHRASE`가 없으면 이후 **모든 주문이 100% 거부**되고, 사용자는 실매매가 도는
   줄 안다. fail-closed이므로 자금 손실은 없다. 값싼 개선: `missing_env_vars`/세션 생성이
   `USES_PASSPHRASE`를 참조하게 하거나, 실거래 세션 생성 시 서명 엔드포인트를 1회 프로브.

6. **`OKX_API_SERVER_URL` 말미 슬래시 미정규화** — `https://www.okx.com/`로 설정하면 전송 경로는
   `//api/v5/...`, 서명 경로는 `/api/v5/...`가 되어 전부 실패한다(fail-closed이지만 원인 파악이
   어렵다). Binance도 동일한 형태다.

7. **OKX는 `candle_interval` 60/180/300초만 지원** — `Config.candle_interval = 600`이면 OKX 세션
   조립이 실패한다. 600 거부는 의도된 올바른 결정이지만(조용한 15m 대체보다 낫다), Binance는
   600을 받으므로 거래소를 `BNC`→`OKX`로 바꾼 사용자는 원인 없는 "세션 조립 실패"만 본다.
   사용자용 문서에 한 줄 안내가 필요하다.

8. **서명 경로가 실제 OKX 서버를 통과한 적 없음** — 개발 샌드박스에 외부 호스트로의 신뢰 CA
   경로가 없어 모든 네트워크 통합 테스트가 실패한다(기존 `binance_data_provider_ITG_test.py`도
   동일하게 실패). 검증은 로컬 재구성 HMAC 벡터 + `requests` 경로 동일성까지다.
   **릴리스 전 `OKX_API_DEMO=1` + 데모 전용 키로 주문 1건 왕복을 반드시 수행할 것.**
   `python -m pytest tests/integration_tests/okx_data_provider_ITG_test.py -v`도 네트워크가 있는
   환경에서 재실행이 필요하다.

---

## 7. 테스트 계획

### 신규 단위 테스트

**`tests/unit_tests/okx_data_provider_test.py`**
- 정상 봉투 → 캔들 dict 변환. 특히 `acc_volume=data[5]`, `acc_price=data[6]` 인덱스 검증
- `code != "0"` 응답 → `UserWarning`
- `data`가 빈 배열 → `UserWarning`
- 미지원 통화 → `UserWarning`
- interval `60/180/300` → 각각 `1m/3m/5m`
- **interval `600` → `UserWarning`** (OKX에 10m 없음)
- 요청 파라미터에 `instId="BTC-USDT"`, `limit=1`, `bar` 포함

**`tests/unit_tests/okx_trader_test.py`** — `binance_trader_test.py` 구조를 미러링하고 OKX 고유 항목 추가
- 서명: `prehash = timestamp + METHOD + requestPath + body` 조립 검증.
  서명에 쓴 `requestPath`의 쿼리와 실제 요청 URL의 쿼리가 **일치**하는지 확인
- 헤더 4종(`OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE`) + `Content-Type: application/json` 존재
- `OKX_API_DEMO` 설정/미설정에 따른 `x-simulated-trading` 헤더 유무
- 지정가 주문 바디: `tdMode="cash"`, `ordType="limit"`, `px`, `sz`
- **시장가 매수**: `ordType="market"`, `tgtCcy="quote_ccy"`, `sz == price * amount`
- **시장가 매도**: `ordType="market"`, `tgtCcy="base_ccy"`, `sz == amount`
- POST 서명에 쓴 JSON 문자열과 실제 전송 바디가 동일한 객체인지
- `_unwrap` 2층 오류: ① `code="1"` + `data[0].sMsg`, ② `code="0"` + `data[0].sCode!="0"` 모두 `None`
- passphrase 미설정 → 주문 전송되지 않음(`_validate_credentials` 차단)
- 주문 폴링: `filled` → `avgPx`/`accFillSz`로 `done` 콜백, `order_map` 비워짐
- 주문 폴링: **`canceled` → `order_map` 비워짐**(영구 폴링 방지), `amount=0` `done` 콜백
- 주문 폴링: `live`/`partially_filled` → `order_map` 유지
- 취소: `POST /api/v5/trade/cancel-order` 사용(DELETE 아님), **취소 성공 시에도 재조회**해
  `accFillSz`/`avgPx`를 확정(취소 응답에 체결 정보가 없음), 재조회 실패 시 콜백 없음
- 잔고 초과 매수 거부, 보유량 초과 매도 거부
- 미지원 `ord_type` → `make_rejected_result`
- 지정가 `price == 0` → no-op
- `_format_number`가 지수표기를 만들지 않음

**`tests/integration_tests/okx_data_provider_ITG_test.py`**
- 실제 public 캔들 1건 조회 → 스키마 키 존재 및 숫자 파싱 확인

### 기존 테스트 확장

- `tests/unit_tests/data_provider_factory_test.py` — `create("OKX")` → `OkxDataProvider`,
  `get_name("OKX")`
- `tests/unit_tests/trader_factory_account_test.py` —
  ① `create("OKX")` → `OkxTrader`,
  ② `account`에 `passphrase_env`가 있으면 `OkxTrader`에 전달,
  ③ **비-OKX Trader(`BNC` 등)에는 `passphrase_env`가 전달되지 않음**(`TypeError` 회귀 방지)
- `tests/unit_tests/account_store_test.py` —
  ① `passphrase_env` 포함 계좌 `validate` 통과,
  ② 환경변수 이름이 아닌 키 '값'을 넣으면 거부,
  ③ `passphrase_env` 미설정 시 `missing_env_vars`에 포함,
  ④ **`passphrase_env`가 없는 기존 3필드 계좌는 `env_ready` 판정에 영향 없음**(하위호환)

---

## 8. 문서 갱신

### OKX 내용 추가

- `README.md` / `README-ko-kr.md` — 환경변수 블록(`# OKX exchange (exchange code OKX)`)과
  지원 거래소 표에 `OKX` 행 추가
- `docs/exchanges-and-trading-ko.md` — 거래소 표, 환경변수, 프로파일 생성 예시,
  **USDT 안전장치 경고**(§6-2), **데모 모드 사용법 및 별도 키 필요 안내**(§6-5)

### Binance 작업 때부터 낡은 서술 정정

아래는 `BNC` Trader 구현 이후 이미 사실과 다르다. OKX 추가와 함께 바로잡는다.

| 위치 | 현재 (잘못됨) |
|---|---|
| `docs/public/faq.md:19` | "실주문 가능 거래소는 Upbit·Bithumb 두 곳, Binance는 데이터 조회만" |
| `docs/public/faq.md:104-105` | "`BNC`는 Trader 구현이 없어 주문 불가" |
| `docs/public/data-providers.md:46` | "Trader가 존재하는 거래소는 Upbit·Bithumb 두 곳. `BNC`는 데이터 전용" |
| `docs/public/architecture.md:53` | "`Trader` 2종" |
| `docs/wiki/SMTM_프로젝트_소개.md:211` | "`BNC` \| Binance \| — \| 데이터 전용" |
| `docs/public/requirements.md:62,138` | 지원 코드 목록에 `OKX` 없음 / "`BNC`처럼 Trader가 없는 코드" |

---

## 9. 구현 순서

1. `OkxDataProvider` + 단위 테스트 + `DataProviderFactory` 등록 (인증 없어 독립적으로 완결)
2. `AccountStore`/`account_tools` passphrase 확장 + `Trader.USES_PASSPHRASE` +
   `TraderFactory` 전달 + 테스트 (Trader 없이도 검증 가능)
3. `OkxTrader` 골격 — 서명, 헤더, 데모 스위치, `_unwrap`, `_validate_credentials`, 시세/계좌 조회,
   **주문 조회 + 취소**, `TraderFactory` 등록 + export.
   `cancel_request`는 `BaseExchangeTrader`에 남은 추상 메서드(`{cancel_request, get_account_info}`)이므로
   이 단계에서 구현해야 클래스를 인스턴스화할 수 있다 — 뒤로 미룰 수 없다.
4. `OkxTrader` 주문 전송 — 지정가/시장가, `tgtCcy`, 가드
5. `OkxTrader` 체결 폴링 — `filled`/`canceled`/`mmp_canceled` 종료 상태 처리
6. 문서 갱신(§8)
