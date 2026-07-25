# OKX 거래소 지원 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OKX 현물(spot) 거래소를 거래소 코드 `OKX` 하나로 시장 데이터 조회와 실주문 실행 모두 가능하게 한다.

**Architecture:** 기존 `BaseDataProvider`/`BaseExchangeTrader`를 상속하는 독립 파일 2개(`OkxDataProvider`, `OkxTrader`)를 추가한다. 기반 클래스는 수정하지 않는다. OKX는 access/secret 외에 **passphrase**를 요구하므로 `AccountStore`에 옵셔널 `passphrase_env` 필드를 추가하고, `Trader.USES_PASSPHRASE` 플래그로 이를 받을 수 있는 Trader에만 전달한다.

**Tech Stack:** Python 3, `requests`, `hmac`/`hashlib`/`base64`(OKX 서명), `unittest` + `pytest`(러너), `unittest.mock`

**설계 스펙:** [docs/superpowers/specs/2026-07-25-okx-exchange-support-design.md](../specs/2026-07-25-okx-exchange-support-design.md)

## Global Constraints

- 거래소 코드는 `"OKX"` — `OkxDataProvider.CODE`와 `OkxTrader.CODE`가 **같은 값**을 쓴다(`BNC`와 동일한 기존 규약).
- `OkxDataProvider.NAME = "OKX DP"`, `OkxTrader.NAME = "OKX"`.
- 기본 엔드포인트: `https://www.okx.com`. 환경변수 `OKX_API_SERVER_URL`이 비어 있을 때만 주입한다.
- 환경변수 이름: `OKX_API_ACCESS_KEY`, `OKX_API_SECRET_KEY`, `OKX_API_PASSPHRASE`, `OKX_API_SERVER_URL`, `OKX_API_DEMO`.
- **`smtm/data/base_data_provider.py`와 `smtm/trader/base_exchange_trader.py`는 수정하지 않는다.** (`smtm/trader/trader.py`에 클래스 상수 1개 추가는 예외 — Task 2)
- 지원 통화 4종 고정: `BTC`, `ETH`, `DOGE`, `XRP`. OKX `instId`는 `BTC-USDT` 형식(하이픈).
- 지원 캔들 주기 3종 고정: `60→"1m"`, `180→"3m"`, `300→"5m"`. **`600`은 `UserWarning`으로 거부** — OKX `bar`에 10m이 없다.
- OKX 응답은 `{"code":"0","msg":"","data":[...]}` 봉투다. **업무 오류도 HTTP 200으로 온다.**
- 주문 수량/가격은 항상 문자열이며 **지수표기(`1e-05`)를 쓰면 거래소가 거부한다.**
- 기존 계좌 파일(`name`/`exchange`/`access_key_env`/`secret_key_env` 4필드)은 계속 유효해야 한다. `passphrase_env`는 `REQUIRED_FIELDS`에 넣지 않는다.
- 테스트 러너: `python -m pytest`. 단위 테스트는 `tests/unit_tests/`, 네트워크를 타는 통합 테스트는 `tests/integration_tests/`(파일명 `*_ITG_test.py`).
- 커밋 메시지는 이 저장소 관례인 `[type] message` 형식을 쓴다(`[feat]`, `[test]`, `[docs]`, `[fix]`). **`Co-Authored-By` 트레일러를 붙이지 않는다.**

---

## File Structure

| 파일 | 책임 |
|---|---|
| `smtm/data/okx_data_provider.py` (신규) | OKX 캔들 조회 + 봉투 해제 + 공통 캔들 스키마 변환. 인증 없음 |
| `smtm/trader/okx_trader.py` (신규) | OKX 서명/헤더/봉투 해제 + 현물 주문 전송·폴링·취소 + 계좌·시세 조회 |
| `smtm/trader/trader.py` (수정) | `USES_PASSPHRASE = False` 기본값 선언 |
| `smtm/account_store.py` (수정) | `passphrase_env` 옵셔널 필드 저장·검증·미설정 보고 |
| `smtm/llm/tools/account_tools.py` (수정) | `register_account` 입력 스키마에 `passphrase_env` 노출 |
| `smtm/trader/trader_factory.py` (수정) | `OkxTrader` 등록 + `USES_PASSPHRASE` Trader에만 passphrase 전달 |
| `smtm/data/data_provider_factory.py` (수정) | `OkxDataProvider` 등록 |
| `smtm/__init__.py`, `smtm/trader/__init__.py` (수정) | export |
| `tests/unit_tests/okx_data_provider_test.py` (신규) | 캔들 파싱·봉투 오류·통화/주기 검증 |
| `tests/unit_tests/okx_trader_test.py` (신규) | 서명·헤더·데모·주문·폴링·취소 |
| `tests/integration_tests/okx_data_provider_ITG_test.py` (신규) | 실제 public 캔들 조회 |
| `tests/unit_tests/account_store_test.py` (수정) | passphrase 필드 + 하위호환 |
| `tests/unit_tests/trader_factory_account_test.py` (수정) | passphrase 전달 규칙 |
| `tests/unit_tests/data_provider_factory_test.py` (수정) | `"OKX"` 매핑 |
| 문서 9종 (수정) | OKX 안내 추가 + Binance 때부터 낡은 서술 정정 |

---

## Task 1: OkxDataProvider

**Files:**
- Create: `smtm/data/okx_data_provider.py`
- Create: `tests/unit_tests/okx_data_provider_test.py`
- Create: `tests/integration_tests/okx_data_provider_ITG_test.py`
- Modify: `smtm/data/data_provider_factory.py`
- Modify: `smtm/__init__.py`
- Modify: `tests/unit_tests/data_provider_factory_test.py`

**Interfaces:**
- Consumes: `BaseDataProvider(logger_name)` — `self.logger`, `self._api_url`, `self._query_params`,
  `self._get_data_from_server()`(실패 시 `UserWarning`). `DateConverter.to_iso_string(datetime)`.
- Produces:
  - `OkxDataProvider(currency="BTC", interval=60)` — `CODE="OKX"`, `NAME="OKX DP"`
  - `OkxDataProvider.get_info() -> list[dict]` — `type="primary_candle"` 캔들 1건 리스트
  - `OkxDataProvider.AVAILABLE_CURRENCY: dict[str, str]` — `{"BTC": "BTC-USDT", ...}`
  - `OkxDataProvider.AVAILABLE_INTERVAL: dict[int, str]` — `{60: "1m", 180: "3m", 300: "5m"}`
  - `OkxDataProvider._get_kst_time_from_unix_time_ms(int) -> str` (staticmethod)

- [ ] **Step 1: Write the failing test**

`tests/unit_tests/okx_data_provider_test.py`:

```python
import unittest
from unittest.mock import patch
from smtm import OkxDataProvider


class OkxDataProviderTests(unittest.TestCase):
    def test_get_kst_time_from_unix_time_ms_should_return_correct_string(self):
        self.assertEqual(
            OkxDataProvider._get_kst_time_from_unix_time_ms(1622563200000),
            "2021-06-02T01:00:00",
        )
        self.assertEqual(
            OkxDataProvider._get_kst_time_from_unix_time_ms(1499040000000),
            "2017-07-03T09:00:00",
        )

    def test_unsupported_currency_raises(self):
        with self.assertRaises(UserWarning):
            OkxDataProvider("USD", 60)

    def test_unsupported_interval_raises(self):
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 900)

    def test_interval_600_raises_because_okx_has_no_10m_bar(self):
        # OKX bar 목록에 10m이 없다 — 15m으로 조용히 바꾸지 않고 거부한다
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 600)

    @patch("requests.get")
    def test_get_info_should_call_get_with_correct_params(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [[
                "1499040000000", "0.01634790", "0.80000000", "0.01575800",
                "0.01577100", "148976.11427815", "2434.19055334",
                "2434.19055334", "1",
            ]],
        }
        OkxDataProvider("BTC", 60).get_info()
        self.assertEqual(
            mock_get.call_args_list[0][0][0],
            "https://www.okx.com/api/v5/market/candles",
        )
        self.assertEqual(
            mock_get.call_args_list[0][1]["params"],
            {"instId": "BTC-USDT", "bar": "1m", "limit": 1},
        )

        OkxDataProvider("ETH", 180).get_info()
        self.assertEqual(
            mock_get.call_args_list[1][1]["params"],
            {"instId": "ETH-USDT", "bar": "3m", "limit": 1},
        )

        OkxDataProvider("XRP", 300).get_info()
        self.assertEqual(
            mock_get.call_args_list[2][1]["params"],
            {"instId": "XRP-USDT", "bar": "5m", "limit": 1},
        )

    @patch("requests.get")
    def test_get_info_should_return_correct_data(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": "0",
            "msg": "",
            "data": [[
                "1499040000000",     # ts
                "0.01634790",        # o
                "0.80000000",        # h
                "0.01575800",        # l
                "0.01577100",        # c
                "148976.11427815",   # vol   (base ccy)
                "2434.19055334",     # volCcy (quote ccy)
                "2434.19055334",     # volCcyQuote
                "1",                 # confirm
            ]],
        }
        expected = {
            "type": "primary_candle",
            "market": "BTC",
            "date_time": "2017-07-03T09:00:00",
            "opening_price": 0.0163479,
            "high_price": 0.8,
            "low_price": 0.015758,
            "closing_price": 0.015771,
            "acc_price": 2434.19055334,
            "acc_volume": 148976.11427815,
        }
        data = OkxDataProvider("BTC", 60).get_info()
        self.assertEqual(data[0], expected)

    @patch("requests.get")
    def test_error_envelope_raises_user_warning(self, mock_get):
        # OKX는 업무 오류도 HTTP 200으로 반환한다
        mock_get.return_value.json.return_value = {
            "code": "51001", "msg": "Instrument ID does not exist", "data": [],
        }
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 60).get_info()

    @patch("requests.get")
    def test_empty_data_raises_user_warning(self, mock_get):
        mock_get.return_value.json.return_value = {"code": "0", "msg": "", "data": []}
        with self.assertRaises(UserWarning):
            OkxDataProvider("BTC", 60).get_info()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_tests/okx_data_provider_test.py -v`
Expected: FAIL — `ImportError: cannot import name 'OkxDataProvider' from 'smtm'`

- [ ] **Step 3: Write the implementation**

Create `smtm/data/okx_data_provider.py`:

```python
from datetime import datetime, timezone, timedelta
from ..date_converter import DateConverter
from .base_data_provider import BaseDataProvider


class OkxDataProvider(BaseDataProvider):
    """
    OKX 거래소의 실시간 거래 데이터를 제공하는 클래스
    A class that provides real-time trading data from the OKX exchange.

    OKX의 public api를 사용. 별도의 가입, 인증, token 없이 사용 가능
    Uses OKX's public API. No signup, authentication, or tokens required.

    https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks
    """

    URL = "https://www.okx.com/api/v5/market/candles"
    AVAILABLE_CURRENCY = {
        "BTC": "BTC-USDT",
        "ETH": "ETH-USDT",
        "DOGE": "DOGE-USDT",
        "XRP": "XRP-USDT",
    }
    #: OKX bar 값. 10m은 OKX에 존재하지 않으므로 600은 지원하지 않는다.
    AVAILABLE_INTERVAL = {60: "1m", 180: "3m", 300: "5m"}
    NAME = "OKX DP"
    CODE = "OKX"
    KST = timezone(timedelta(hours=9))

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")
        if interval not in self.AVAILABLE_INTERVAL:
            raise UserWarning(f"not supported interval: {interval}")

        super().__init__(logger_name="OkxDataProvider")
        self.market = currency
        self.interval = self.AVAILABLE_INTERVAL[interval]
        self._api_url = self.URL
        self._query_params = {
            "instId": self.AVAILABLE_CURRENCY[currency],
            "bar": self.interval,
            "limit": 1,
        }

    def get_info(self):
        """실시간 거래 정보 전달한다

        Returns: 거래 정보 딕셔너리
        {
            "market": 거래 시장 종류 BTC
            "date_time": 정보의 기준 시간
            "opening_price": 시작 거래 가격
            "high_price": 최고 거래 가격
            "low_price": 최저 거래 가격
            "closing_price": 마지막 거래 가격
            "acc_price": 단위 시간내 누적 거래 금액
            "acc_volume": 단위 시간내 누적 거래 양
        }
        """
        data = self._get_data_from_server()
        return [self._create_candle_info(self._unwrap_candles(data)[0])]

    def _unwrap_candles(self, data):
        """OKX 응답 봉투를 해제해 캔들 배열 리스트를 반환한다.

        OKX는 업무 오류도 HTTP 200으로 반환하므로 code를 직접 확인해야 한다.
        실패는 BaseDataProvider._get_data_from_server와 같은 UserWarning으로 올린다.
        """
        if not isinstance(data, dict) or str(data.get("code")) != "0":
            msg = data.get("msg") if isinstance(data, dict) else data
            self.logger.error(f"OKX error response: {msg}")
            raise UserWarning("Fail get data from sever")
        rows = data.get("data") or []
        if not rows:
            self.logger.error("OKX returned empty candle data")
            raise UserWarning("Fail get data from sever")
        return rows

    def _create_candle_info(self, data):
        """
        sample response:
        {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1597026383085",   // ts, 캔들 시작 시간 (unix ms)
                    "3.721",           // o, 시가
                    "3.743",           // h, 고가
                    "3.677",           // l, 저가
                    "3.708",           // c, 종가
                    "8422410",         // vol, 거래량 (base ccy)
                    "22698348.04",     // volCcy, 거래대금 (quote ccy)
                    "22698348.04",     // volCcyQuote, 현물에서는 volCcy와 동일
                    "1"                // confirm, 0=미완성 1=완성
                ]
            ]
        }
        캔들은 최신순(내림차순)으로 오지만 limit=1이므로 data[0]이 곧 최신 캔들이다.
        """
        try:
            return {
                "type": "primary_candle",
                "market": self.market,
                "date_time": self._get_kst_time_from_unix_time_ms(int(data[0])),
                "opening_price": float(data[1]),
                "high_price": float(data[2]),
                "low_price": float(data[3]),
                "closing_price": float(data[4]),
                "acc_price": float(data[6]),
                "acc_volume": float(data[5]),
            }
        except (IndexError, ValueError) as err:
            self.logger.warning(f"invalid data for candle info: {err}")
            return None

    @staticmethod
    def _get_kst_time_from_unix_time_ms(unix_time_ms):
        return DateConverter.to_iso_string(
            datetime.fromtimestamp(unix_time_ms / 1000, tz=OkxDataProvider.KST)
        )
```

- [ ] **Step 4: Register in factory and export**

`smtm/data/data_provider_factory.py` — 첫 import 줄 아래에 추가하고 리스트에 넣는다:

```python
from .binance_data_provider import BinanceDataProvider
from .okx_data_provider import OkxDataProvider
from .upbit_data_provider import UpbitDataProvider
```

```python
    DataProvider_LIST = [
        BinanceDataProvider,
        OkxDataProvider,
        UpbitDataProvider,
        BithumbDataProvider,
        UpbitBinanceDataProvider,
        UpbitNewsDataProvider,
        UpbitMultiNewsDataProvider,
        UpbitSocialDataProvider,
        UpbitFullContextDataProvider,
    ]
```

`smtm/__init__.py` — `from .data.binance_data_provider import BinanceDataProvider` 줄 바로 아래에 추가:

```python
from .data.okx_data_provider import OkxDataProvider
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit_tests/okx_data_provider_test.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Add the factory test**

`tests/unit_tests/data_provider_factory_test.py` — 상단 import 블록에 `OkxDataProvider`를 더한다:

```python
from smtm import (
    DataProviderFactory,
    BinanceDataProvider,
    OkxDataProvider,
    UpbitDataProvider,
    BithumbDataProvider,
    UpbitBinanceDataProvider,
)
```

그리고 `DataProviderFactoryTests` 클래스 안에 두 테스트를 추가:

```python
    def test_create_should_return_okx_data_provider_for_okx(self):
        self.assertTrue(
            isinstance(DataProviderFactory.create("OKX"), OkxDataProvider)
        )

    def test_get_name_should_return_okx_name(self):
        self.assertEqual(DataProviderFactory.get_name("OKX"), OkxDataProvider.NAME)
```

- [ ] **Step 7: Run the factory test**

Run: `python -m pytest tests/unit_tests/data_provider_factory_test.py -v`
Expected: PASS

- [ ] **Step 8: Add the integration test**

`tests/integration_tests/okx_data_provider_ITG_test.py`:

```python
import unittest
from smtm import OkxDataProvider


class OkxDataProviderIntegrationTests(unittest.TestCase):
    def _assert_candle_schema(self, info, market=None):
        self.assertEqual(info["type"], "primary_candle")
        if market is not None:
            self.assertEqual(info["market"], market)
        for key in ("market", "date_time", "opening_price", "high_price",
                    "low_price", "closing_price", "acc_price", "acc_volume"):
            self.assertIn(key, info)
        for key in ("opening_price", "high_price", "low_price",
                    "closing_price", "acc_price", "acc_volume"):
            self.assertIsInstance(info[key], float)

    def test_ITG_get_info_return_correct_data(self):
        self._assert_candle_schema(OkxDataProvider().get_info()[0])

    def test_ITG_get_info_return_correct_data_when_currency_is_BTC(self):
        self._assert_candle_schema(OkxDataProvider("BTC").get_info()[0], "BTC")

    def test_ITG_get_info_return_correct_data_when_currency_is_ETH(self):
        self._assert_candle_schema(OkxDataProvider("ETH").get_info()[0], "ETH")

    def test_ITG_get_info_return_correct_data_when_currency_is_DOGE(self):
        self._assert_candle_schema(OkxDataProvider("DOGE").get_info()[0], "DOGE")

    def test_ITG_get_info_return_correct_data_when_currency_is_XRP(self):
        self._assert_candle_schema(OkxDataProvider("XRP").get_info()[0], "XRP")
```

- [ ] **Step 9: Run the integration test (needs network)**

Run: `python -m pytest tests/integration_tests/okx_data_provider_ITG_test.py -v`
Expected: PASS (5 tests). 실패하면 응답을 직접 확인한다:
`python -c "import requests,json; print(json.dumps(requests.get('https://www.okx.com/api/v5/market/candles', params={'instId':'BTC-USDT','bar':'1m','limit':1}).json(), indent=2))"`

- [ ] **Step 10: Commit**

```bash
git add smtm/data/okx_data_provider.py smtm/data/data_provider_factory.py smtm/__init__.py \
        tests/unit_tests/okx_data_provider_test.py \
        tests/unit_tests/data_provider_factory_test.py \
        tests/integration_tests/okx_data_provider_ITG_test.py
git commit -m "[feat] add OkxDataProvider with OKX candle envelope handling"
```

---

## Task 2: passphrase 배선 (AccountStore · Trader 플래그 · TraderFactory)

OKX는 access/secret 외에 passphrase를 요구한다. `OkxTrader`가 아직 없어도 이 배선은 독립적으로 검증 가능하다.

**Files:**
- Modify: `smtm/account_store.py:14-15` (필드 집합), `:35-39` (검증 루프), `:41-48` (`missing_env_vars`), `:93-99` (요약)
- Modify: `smtm/llm/tools/account_tools.py:2-10` (`ACCOUNT_PROPERTIES`)
- Modify: `smtm/trader/trader.py:12-13` 아래 (`USES_PASSPHRASE`)
- Modify: `smtm/trader/trader_factory.py:36-39` (kwargs 조립)
- Test: `tests/unit_tests/account_store_test.py`, `tests/unit_tests/trader_factory_account_test.py`

**Interfaces:**
- Consumes: Task 1의 산출물 없음 (독립).
- Produces:
  - `AccountStore.ALLOWED_FIELDS`에 `"passphrase_env"` 포함, `REQUIRED_FIELDS`는 4필드 유지
  - `AccountStore.missing_env_vars(account) -> list[str]` — `passphrase_env`는 **등록됐을 때만** 검사
  - `AccountStore.list_accounts()` 요약 dict에 `"passphrase_env"` 키 포함
  - `Trader.USES_PASSPHRASE: bool = False` — 서브클래스가 `True`로 덮어쓴다
  - `TraderFactory.create(..., account=...)`는 `account["passphrase_env"]`가 있고
    Trader가 `USES_PASSPHRASE=True`일 때만 `passphrase_env` kwarg를 넘긴다

- [ ] **Step 1: Write the failing tests**

`tests/unit_tests/account_store_test.py` — 파일 맨 아래 `AccountStoreTests` 클래스 안에 추가:

```python
    def test_validate_accepts_optional_passphrase_env(self):
        self.store.validate({**ACCOUNT, "exchange": "OKX",
                             "passphrase_env": "SMTM_TEST_PASSPHRASE_1"})

    def test_validate_rejects_key_value_shaped_passphrase_env(self):
        with self.assertRaises(ValueError):
            self.store.validate({**ACCOUNT, "passphrase_env": "my+raw/passphrase=="})

    def test_missing_env_vars_includes_unset_passphrase_env(self):
        account = {**ACCOUNT, "passphrase_env": "SMTM_TEST_PASSPHRASE_1"}
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            os.environ.pop("SMTM_TEST_PASSPHRASE_1", None)
            missing = self.store.missing_env_vars(account)
        self.assertEqual(missing, ["SMTM_TEST_PASSPHRASE_1"])

    def test_missing_env_vars_empty_when_passphrase_env_is_set(self):
        account = {**ACCOUNT, "passphrase_env": "SMTM_TEST_PASSPHRASE_1"}
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b",
                                     "SMTM_TEST_PASSPHRASE_1": "c"}):
            self.assertEqual(self.store.missing_env_vars(account), [])

    def test_account_without_passphrase_env_stays_env_ready(self):
        # 하위호환: passphrase_env를 등록하지 않은 기존 계좌는 누락으로 보고되지 않는다
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            self.assertEqual(self.store.missing_env_vars(ACCOUNT), [])

    def test_save_and_load_roundtrip_with_passphrase_env(self):
        account = {**ACCOUNT, "exchange": "OKX",
                   "passphrase_env": "SMTM_TEST_PASSPHRASE_1"}
        self.store.save(account)
        self.assertEqual(self.store.load("main"), account)

    def test_list_accounts_includes_passphrase_env(self):
        account = {**ACCOUNT, "exchange": "OKX",
                   "passphrase_env": "SMTM_TEST_PASSPHRASE_1"}
        self.store.save(account)
        summary = self.store.list_accounts()[0]
        self.assertEqual(summary["passphrase_env"], "SMTM_TEST_PASSPHRASE_1")
```

`tests/unit_tests/trader_factory_account_test.py` — 파일 맨 아래 클래스 안에 추가
(상단 import에 `from smtm.trader.trader import Trader`, `from smtm.trader.binance_trader import BinanceTrader` 추가):

```python
    def test_trader_defaults_to_no_passphrase(self):
        self.assertFalse(Trader.USES_PASSPHRASE)
        self.assertFalse(BinanceTrader.USES_PASSPHRASE)

    def test_passphrase_env_not_passed_to_trader_that_does_not_use_it(self):
        # passphrase_env가 섞인 계좌로 BNC를 만들어도 TypeError 없이 생성돼야 한다
        with patch.dict(os.environ, {
            "SMTM_KEY_8": "a", "SMTM_SECRET_8": "b",
            "BINANCE_API_SERVER_URL": "https://api.binance.com",
        }):
            trader = TraderFactory.create(
                "BNC", budget=1000, currency="BTC",
                account={"access_key_env": "SMTM_KEY_8",
                         "secret_key_env": "SMTM_SECRET_8",
                         "passphrase_env": "SMTM_PASS_8"})
        self.assertIsInstance(trader, BinanceTrader)
        trader.worker.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit_tests/account_store_test.py tests/unit_tests/trader_factory_account_test.py -v`
Expected: FAIL — `ValueError: 알 수 없는 계좌 필드: passphrase_env`, `AttributeError: type object 'Trader' has no attribute 'USES_PASSPHRASE'`

- [ ] **Step 3: Extend AccountStore**

`smtm/account_store.py` — `ALLOWED_FIELDS`/`REQUIRED_FIELDS`를 다음으로 교체
(`REQUIRED_FIELDS`는 **변경하지 않는다** — 기존 4필드 계좌 파일의 하위호환):

```python
    ALLOWED_FIELDS = {"name", "exchange", "access_key_env", "secret_key_env",
                      "passphrase_env"}
    REQUIRED_FIELDS = ("name", "exchange", "access_key_env", "secret_key_env")
    #: 환경변수 '이름' 형식을 검증할 필드 (passphrase_env는 OKX 등에서만 선택적으로 쓰임)
    ENV_NAME_FIELDS = ("access_key_env", "secret_key_env", "passphrase_env")
```

`validate()`의 검증 루프를 교체:

```python
        for key in self.ENV_NAME_FIELDS:
            value = account.get(key, "")
            if value and not self.ENV_NAME_PATTERN.match(str(value)):
                raise ValueError(
                    f"{key}은(는) 환경변수 '이름'이어야 합니다 (키 값을 넣지 마세요)")
```

`missing_env_vars()`를 교체:

```python
    def missing_env_vars(self, account: dict) -> list:
        """설정되지 않은 키 환경변수 '이름' 목록 (값을 저장하거나 반환하지 않는다)"""
        missing = []
        for key in ("access_key_env", "secret_key_env"):
            env_name = account.get(key)
            if not env_name or not os.environ.get(env_name, ""):
                missing.append(env_name or key)
        # passphrase_env는 등록된 계좌에서만 검사한다. 필수로 취급하면
        # passphrase가 없는 기존 거래소 계좌가 모두 env_ready=False가 된다.
        passphrase_env = account.get("passphrase_env")
        if passphrase_env and not os.environ.get(passphrase_env, ""):
            missing.append(passphrase_env)
        return missing
```

`list_accounts()`의 요약 dict에 한 줄 추가 (`"secret_key_env"` 다음):

```python
                    "passphrase_env": account.get("passphrase_env"),
```

- [ ] **Step 4: Expose the field to the LLM tool**

`smtm/llm/tools/account_tools.py` — `ACCOUNT_PROPERTIES`에 항목 추가
(`required` 목록은 **변경하지 않는다**):

```python
    "passphrase_env": {"type": "string",
                       "description": "passphrase가 담긴 환경변수 이름."
                                      " OKX처럼 passphrase를 요구하는 거래소에만 필요"},
```

- [ ] **Step 5: Add the Trader flag**

`smtm/trader/trader.py` — `SUPPORTED_ORD_TYPES` 선언 바로 아래에 추가:

```python
    #: 이 Trader가 access/secret 외에 passphrase를 요구하는지 여부.
    #: True인 Trader에만 TraderFactory가 passphrase_env를 전달한다.
    USES_PASSPHRASE = False
```

- [ ] **Step 6: Wire TraderFactory**

`smtm/trader/trader_factory.py` — `if account:` 블록을 교체:

```python
                if account:
                    kwargs["access_key_env"] = account.get("access_key_env")
                    kwargs["secret_key_env"] = account.get("secret_key_env")
                    # passphrase를 받지 않는 Trader에 넘기면 TypeError가 나므로
                    # USES_PASSPHRASE를 선언한 Trader에만 전달한다.
                    if (account.get("passphrase_env")
                            and getattr(trader, "USES_PASSPHRASE", False)):
                        kwargs["passphrase_env"] = account["passphrase_env"]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/unit_tests/account_store_test.py tests/unit_tests/trader_factory_account_test.py tests/unit_tests/account_tools_test.py -v`
Expected: PASS (기존 테스트 포함 전부)

- [ ] **Step 8: Commit**

```bash
git add smtm/account_store.py smtm/llm/tools/account_tools.py \
        smtm/trader/trader.py smtm/trader/trader_factory.py \
        tests/unit_tests/account_store_test.py \
        tests/unit_tests/trader_factory_account_test.py
git commit -m "[feat] AccountStore supports optional passphrase_env for 3-credential exchanges"
```

---

## Task 3: OkxTrader 골격 — 서명 · 헤더 · 봉투 해제 · 시세 · 계좌 · 주문조회 · 취소

> **왜 취소가 여기 포함되는가:** `BaseExchangeTrader.__abstractmethods__`는
> `{"cancel_request", "get_account_info"}`다. `cancel_request`를 정의하지 않으면
> `OkxTrader`를 **인스턴스화조차 할 수 없다**(`TypeError: Can't instantiate abstract class`).
> 따라서 이 Task에서 `cancel_request`와 그 의존 메서드까지 완성한다.
> 확인: `python -c "from smtm.trader.base_exchange_trader import BaseExchangeTrader; print(BaseExchangeTrader.__abstractmethods__)"`

**Files:**
- Create: `smtm/trader/okx_trader.py`
- Create: `tests/unit_tests/okx_trader_test.py`
- Modify: `smtm/trader/trader_factory.py` (`TRADER_LIST`)
- Modify: `smtm/trader/__init__.py`, `smtm/__init__.py`

**Interfaces:**
- Consumes: `BaseExchangeTrader(budget, currency, commission_ratio, opt_mode, logger_name, worker_name, env_key_names)` — `self.ACCESS_KEY`/`SECRET_KEY`/`SERVER_URL`/`balance`/`asset`/`order_map`/`logger`, `self._request_get(url, headers=None, params=None)`, `self._request_post(url, headers=None, params=None, data=None)`, `self._validate_credentials()`, `self.ISO_DATEFORMAT`. Task 2의 `Trader.USES_PASSPHRASE`.
- Produces:
  - `OkxTrader(budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True, access_key_env=None, secret_key_env=None, passphrase_env=None)`
  - 클래스 속성: `CODE="OKX"`, `NAME="OKX"`, `USES_PASSPHRASE=True`,
    `SUPPORTED_ORD_TYPES=frozenset({"limit","market"})`,
    `TERMINAL_STATES=frozenset({"filled","canceled","mmp_canceled"})`,
    `AVAILABLE_CURRENCY: dict[str, tuple[str, str]]`
  - 인스턴스 속성: `market`(예 `"BTC-USDT"`), `market_currency`(예 `"BTC"`), `PASSPHRASE`, `is_demo`
  - `_timestamp() -> str` (staticmethod)
  - `_create_signature(timestamp, method, request_path, body="") -> str`
  - `_auth_headers(method, request_path, body="") -> dict`
  - `_unwrap(response) -> dict | None`
  - `_signed_get(path, params) -> dict | None`
  - `_signed_post(path, payload) -> dict | None`
  - `_format_number(value) -> str` (staticmethod)
  - `get_trade_tick() -> dict | None`, `get_account_info() -> dict`
  - `_query_order(order_id) -> dict | None`, `_cancel_order(order_id) -> dict | None`
  - `_fill_price(response) -> float`, `_fill_amount(response) -> float` (staticmethod)
  - `cancel_request(request_id)` — 추상 메서드 구현. `order_map`에서 제거 후 상태 확정

- [ ] **Step 1: Write the failing tests**

`tests/unit_tests/okx_trader_test.py`:

```python
import base64
import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch, MagicMock
from smtm.trader.okx_trader import OkxTrader
from smtm.trader.trader_factory import TraderFactory

TEST_OKX_ENV = {
    "OKX_API_ACCESS_KEY": "test_access_key",
    "OKX_API_SECRET_KEY": "test_secret_key",
    "OKX_API_PASSPHRASE": "test_passphrase",
    "OKX_API_SERVER_URL": "http://test_server",
}


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderScaffoldTest(unittest.TestCase):
    def test_currency_maps_to_inst_id_and_coin(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        self.assertEqual(trader.market, "BTC-USDT")
        self.assertEqual(trader.market_currency, "BTC")

    def test_unsupported_currency_raises(self):
        with self.assertRaises(UserWarning):
            OkxTrader(currency="SOL")

    def test_supported_ord_types(self):
        self.assertEqual(
            OkxTrader(currency="BTC").SUPPORTED_ORD_TYPES,
            frozenset({"limit", "market"}),
        )

    def test_declares_passphrase_usage(self):
        self.assertTrue(OkxTrader.USES_PASSPHRASE)

    def test_passphrase_read_from_env(self):
        self.assertEqual(OkxTrader(currency="BTC").PASSPHRASE, "test_passphrase")

    def test_custom_passphrase_env_name(self):
        with patch.dict(os.environ, {"MY_OKX_PASS": "custom-pass"}):
            trader = OkxTrader(currency="BTC", passphrase_env="MY_OKX_PASS")
        self.assertEqual(trader.PASSPHRASE, "custom-pass")

    def test_timestamp_is_utc_iso8601_with_milliseconds(self):
        stamp = OkxTrader._timestamp()
        self.assertTrue(stamp.endswith("Z"))
        self.assertEqual(len(stamp), 24)  # 2026-07-25T09:08:57.715Z
        self.assertEqual(stamp[10], "T")
        self.assertEqual(stamp[19], ".")

    def test_signature_is_base64_hmac_sha256_of_prehash(self):
        trader = OkxTrader(currency="BTC")
        prehash = "2026-07-25T09:08:57.715ZGET/api/v5/trade/order?instId=BTC-USDT"
        expected = base64.b64encode(
            hmac.new(b"test_secret_key", prehash.encode(), hashlib.sha256).digest()
        ).decode()
        self.assertEqual(
            trader._create_signature(
                "2026-07-25T09:08:57.715Z", "GET",
                "/api/v5/trade/order?instId=BTC-USDT"),
            expected,
        )

    def test_signature_includes_body_for_post(self):
        trader = OkxTrader(currency="BTC")
        body = '{"instId": "BTC-USDT"}'
        prehash = "2026-07-25T09:08:57.715ZPOST/api/v5/trade/order" + body
        expected = base64.b64encode(
            hmac.new(b"test_secret_key", prehash.encode(), hashlib.sha256).digest()
        ).decode()
        self.assertEqual(
            trader._create_signature(
                "2026-07-25T09:08:57.715Z", "POST", "/api/v5/trade/order", body),
            expected,
        )

    def test_auth_headers_contain_all_four_okx_headers(self):
        trader = OkxTrader(currency="BTC")
        headers = trader._auth_headers("GET", "/api/v5/account/balance")
        self.assertEqual(headers["OK-ACCESS-KEY"], "test_access_key")
        self.assertEqual(headers["OK-ACCESS-PASSPHRASE"], "test_passphrase")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("OK-ACCESS-SIGN", headers)
        self.assertIn("OK-ACCESS-TIMESTAMP", headers)
        # 서명은 헤더에 실린 그 타임스탬프로 만들어져야 한다
        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            trader._create_signature(
                headers["OK-ACCESS-TIMESTAMP"], "GET", "/api/v5/account/balance"),
        )

    def test_no_demo_header_by_default(self):
        trader = OkxTrader(currency="BTC")
        self.assertFalse(trader.is_demo)
        self.assertNotIn("x-simulated-trading", trader._auth_headers("GET", "/x"))

    def test_demo_header_added_when_env_enabled(self):
        with patch.dict(os.environ, {"OKX_API_DEMO": "1"}):
            trader = OkxTrader(currency="BTC")
        self.assertTrue(trader.is_demo)
        self.assertEqual(
            trader._auth_headers("GET", "/x")["x-simulated-trading"], "1")

    def test_default_server_url_when_env_blank(self):
        with patch.dict(os.environ, {"OKX_API_SERVER_URL": ""}):
            trader = OkxTrader(currency="BTC")
        self.assertEqual(trader.SERVER_URL, "https://www.okx.com")

    def test_format_number_avoids_scientific_notation(self):
        self.assertEqual(OkxTrader._format_number(0.00005), "0.00005")
        self.assertEqual(OkxTrader._format_number(5000.0), "5000")
        self.assertEqual(OkxTrader._format_number(0), "0")


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderUnwrapTest(unittest.TestCase):
    def _trader(self):
        return OkxTrader(currency="BTC")

    def test_unwrap_returns_first_data_item_on_success(self):
        result = self._trader()._unwrap(
            {"code": "0", "msg": "", "data": [{"ordId": "42"}]})
        self.assertEqual(result, {"ordId": "42"})

    def test_unwrap_returns_none_for_none_response(self):
        self.assertIsNone(self._trader()._unwrap(None))

    def test_unwrap_returns_none_on_top_level_error_code(self):
        # 최상위 code!=0 — 구체적 사유는 data[0].sMsg에만 담긴다
        self.assertIsNone(self._trader()._unwrap({
            "code": "1", "msg": "",
            "data": [{"sCode": "51008", "sMsg": "Insufficient balance"}],
        }))

    def test_unwrap_returns_none_on_item_level_error_code(self):
        self.assertIsNone(self._trader()._unwrap({
            "code": "0", "msg": "",
            "data": [{"ordId": "", "sCode": "51000", "sMsg": "Parameter error"}],
        }))

    def test_unwrap_accepts_item_with_scode_zero(self):
        result = self._trader()._unwrap({
            "code": "0", "msg": "",
            "data": [{"ordId": "7", "sCode": "0", "sMsg": ""}],
        })
        self.assertEqual(result["ordId"], "7")

    def test_unwrap_returns_none_on_empty_data(self):
        self.assertIsNone(self._trader()._unwrap({"code": "0", "msg": "", "data": []}))


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderSignedRequestTest(unittest.TestCase):
    def test_signed_get_signs_the_exact_url_query_it_sends(self):
        trader = OkxTrader(currency="BTC")
        trader._request_get = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"state": "live"}]})
        trader._signed_get("/api/v5/trade/order",
                           {"instId": "BTC-USDT", "ordId": "42"})
        args, kwargs = trader._request_get.call_args
        url = args[0]
        # params= 로 넘기지 않고 URL에 직접 인코딩해야 서명과 일치한다
        self.assertIsNone(kwargs.get("params"))
        self.assertEqual(
            url, "http://test_server/api/v5/trade/order?instId=BTC-USDT&ordId=42")
        request_path = url[len("http://test_server"):]
        self.assertEqual(
            kwargs["headers"]["OK-ACCESS-SIGN"],
            trader._create_signature(
                kwargs["headers"]["OK-ACCESS-TIMESTAMP"], "GET", request_path),
        )

    def test_signed_post_signs_the_exact_body_it_sends(self):
        trader = OkxTrader(currency="BTC")
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "9"}]})
        trader._signed_post("/api/v5/trade/order", {"instId": "BTC-USDT"})
        args, kwargs = trader._request_post.call_args
        body = kwargs["data"]
        self.assertEqual(json.loads(body), {"instId": "BTC-USDT"})
        self.assertEqual(
            kwargs["headers"]["OK-ACCESS-SIGN"],
            trader._create_signature(
                kwargs["headers"]["OK-ACCESS-TIMESTAMP"], "POST",
                "/api/v5/trade/order", body),
        )

    def test_signed_request_blocked_without_passphrase(self):
        with patch.dict(os.environ, {"OKX_API_PASSPHRASE": ""}):
            trader = OkxTrader(currency="BTC")
        trader._request_post = MagicMock()
        trader._request_get = MagicMock()
        self.assertIsNone(trader._signed_post("/api/v5/trade/order", {"a": 1}))
        self.assertIsNone(trader._signed_get("/api/v5/trade/order", {"a": 1}))
        trader._request_post.assert_not_called()
        trader._request_get.assert_not_called()


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderAccountTest(unittest.TestCase):
    def test_get_trade_tick_calls_public_ticker_endpoint(self):
        trader = OkxTrader(currency="BTC")
        trader._request_get = MagicMock(return_value={
            "code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "50000.0"}],
        })
        result = trader.get_trade_tick()
        args, kwargs = trader._request_get.call_args
        self.assertIn("/api/v5/market/ticker", args[0])
        self.assertEqual(kwargs["params"], {"instId": "BTC-USDT"})
        self.assertEqual(result["last"], "50000.0")

    def test_get_account_info_returns_local_balance_and_live_quote(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        trader.balance = 1000
        trader.asset = (50000, 0.02)
        trader.get_trade_tick = MagicMock(return_value={"last": "51000.0"})
        info = trader.get_account_info()
        self.assertEqual(info["balance"], 1000)
        self.assertEqual(info["asset"], {"BTC": (50000, 0.02)})
        self.assertEqual(info["quote"], {"BTC": 51000.0})
        self.assertIn("date_time", info)

    def test_get_account_info_survives_quote_failure(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        trader.get_trade_tick = MagicMock(return_value=None)
        info = trader.get_account_info()
        self.assertEqual(info["quote"], {})


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderFactoryTest(unittest.TestCase):
    def test_factory_creates_okx_trader_for_okx(self):
        trader = TraderFactory.create("OKX", budget=1000, currency="BTC")
        self.assertIsInstance(trader, OkxTrader)
        trader.worker.stop()

    def test_factory_get_name_for_okx(self):
        self.assertEqual(TraderFactory.get_name("OKX"), "OKX")

    def test_factory_passes_passphrase_env_to_okx_trader(self):
        with patch.dict(os.environ, {
            "SMTM_KEY_7": "a", "SMTM_SECRET_7": "b", "SMTM_PASS_7": "custom-pass",
        }):
            trader = TraderFactory.create(
                "OKX", budget=1000, currency="BTC",
                account={"access_key_env": "SMTM_KEY_7",
                         "secret_key_env": "SMTM_SECRET_7",
                         "passphrase_env": "SMTM_PASS_7"})
        self.assertEqual(trader.ACCESS_KEY, "a")
        self.assertEqual(trader.SECRET_KEY, "b")
        self.assertEqual(trader.PASSPHRASE, "custom-pass")
        trader.worker.stop()


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderCancelTest(unittest.TestCase):
    def _trader_with_open_order(self):
        trader = OkxTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (0, 0)
        trader._start_timer = MagicMock()
        trader._stop_timer = MagicMock()
        cb = MagicMock()
        trader.order_map["ok"] = {
            "order_id": "444",
            "callback": cb,
            "result": {"state": "requested", "request": {"id": "ok"},
                       "type": "buy", "price": 50000, "amount": 0.1, "msg": "success"},
        }
        return trader, cb

    def test_query_order_uses_signed_get_with_inst_id_and_ord_id(self):
        trader, _ = self._trader_with_open_order()
        trader._signed_get = MagicMock(return_value={"state": "live"})
        trader._query_order("444")
        trader._signed_get.assert_called_once_with(
            "/api/v5/trade/order", {"instId": "BTC-USDT", "ordId": "444"})

    def test_cancel_order_uses_post_cancel_endpoint(self):
        trader, _ = self._trader_with_open_order()
        trader._signed_post = MagicMock(return_value={"ordId": "444", "sCode": "0"})
        trader._cancel_order("444")
        trader._signed_post.assert_called_once_with(
            "/api/v5/trade/cancel-order", {"instId": "BTC-USDT", "ordId": "444"})

    def test_fill_price_and_amount_handle_empty_strings(self):
        # 미체결 주문은 avgPx/accFillSz가 빈 문자열로 온다
        self.assertEqual(OkxTrader._fill_price({"avgPx": ""}), 0)
        self.assertEqual(OkxTrader._fill_amount({"accFillSz": ""}), 0)
        self.assertEqual(OkxTrader._fill_price({"avgPx": "50000.0"}), 50000.0)
        self.assertEqual(OkxTrader._fill_amount({"accFillSz": "0.1"}), 0.1)

    def test_cancel_request_requeries_because_cancel_response_lacks_fill_info(self):
        # OKX cancel-order 응답에는 accFillSz/avgPx가 없다 → 항상 재조회해야 한다
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value={"ordId": "444", "sCode": "0"})
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "canceled", "avgPx": "", "accFillSz": "0",
        })
        trader.cancel_request("ok")
        trader._cancel_order.assert_called_once_with("444")
        trader._query_order.assert_called_once_with("444")
        self.assertNotIn("ok", trader.order_map)
        self.assertEqual(cb.call_args[0][0]["state"], "done")

    def test_cancel_request_reports_fill_when_already_filled(self):
        # 취소 실패(이미 체결)여도 재조회로 체결 결과를 확정한다
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "filled", "avgPx": "50000.0", "accFillSz": "0.1",
        })
        trader.cancel_request("ok")
        done = cb.call_args[0][0]
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["price"], 50000.0)
        self.assertEqual(done["amount"], 0.1)
        self.assertNotIn("ok", trader.order_map)

    def test_cancel_request_without_query_result_does_not_callback(self):
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value=None)
        trader.cancel_request("ok")
        cb.assert_not_called()
        self.assertNotIn("ok", trader.order_map)

    def test_cancel_unknown_id_is_noop(self):
        trader, _ = self._trader_with_open_order()
        trader._cancel_order = MagicMock()
        trader.cancel_request("does-not-exist")
        trader._cancel_order.assert_not_called()

    def test_cancel_all_requests_cancels_every_open_order(self):
        trader, _ = self._trader_with_open_order()
        trader.order_map["ok2"] = dict(trader.order_map["ok"], order_id="555")
        cancelled = []
        trader.cancel_request = lambda request_id: cancelled.append(request_id)
        trader.cancel_all_requests()
        self.assertEqual(sorted(cancelled), ["ok", "ok2"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'smtm.trader.okx_trader'`

- [ ] **Step 3: Write the scaffold implementation**

Create `smtm/trader/okx_trader.py`:

```python
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from .base_exchange_trader import BaseExchangeTrader
from . import order_spec


class OkxTrader(BaseExchangeTrader):
    """
    OKX 현물(spot) 거래소를 통한 거래 요청 및 계좌 조회를 처리하는 Trader

    OkxTrader processes spot trading requests and account inquiries via OKX.

    id: 요청 정보 id
    type: 거래 유형 buy, sell, cancel
    price: 거래 가격 (USDT)
    amount: 거래 수량 (코인)

    OKX는 access/secret 외에 passphrase를 요구하며, 업무 오류도 HTTP 200에
    {"code": "0|기타", "data": [...]} 봉투로 실어 보낸다. _unwrap이 이를 처리한다.

    https://www.okx.com/docs-v5/en/
    """

    AVAILABLE_CURRENCY = {
        "BTC": ("BTC-USDT", "BTC"),
        "ETH": ("ETH-USDT", "ETH"),
        "DOGE": ("DOGE-USDT", "DOGE"),
        "XRP": ("XRP-USDT", "XRP"),
    }
    NAME = "OKX"
    CODE = "OKX"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})
    USES_PASSPHRASE = True
    #: 더 이상 오더북에 남지 않는 상태. 폴링 대상에서 제거해야 한다.
    TERMINAL_STATES = frozenset({"filled", "canceled", "mmp_canceled"})

    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True,
        access_key_env=None, secret_key_env=None, passphrase_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="OkxTrader",
            worker_name="OkxTrader-Worker",
            env_key_names=(
                access_key_env or "OKX_API_ACCESS_KEY",
                secret_key_env or "OKX_API_SECRET_KEY",
                "OKX_API_SERVER_URL",
            ),
        )
        if not self.SERVER_URL:
            self.SERVER_URL = "https://www.okx.com"
        self.PASSPHRASE = os.environ.get(passphrase_env or "OKX_API_PASSPHRASE", "")
        if not self.PASSPHRASE:
            self.logger.warning("OkxTrader passphrase is not set")
        self.is_demo = os.environ.get("OKX_API_DEMO", "").lower() in ("1", "true", "yes")
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    @staticmethod
    def _timestamp():
        """OKX 서명용 UTC ISO8601 타임스탬프 (밀리초 3자리). 예: 2026-07-25T09:08:57.715Z"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _create_signature(self, timestamp, method, request_path, body=""):
        """base64(HMAC-SHA256(timestamp + METHOD + requestPath + body))

        request_path는 쿼리스트링을 포함한 경로여야 하며, 실제 요청 URL과
        정확히 같아야 서명이 통과한다.
        """
        prehash = f"{timestamp}{method.upper()}{request_path}{body}"
        return base64.b64encode(
            hmac.new(self.SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()

    def _auth_headers(self, method, request_path, body=""):
        timestamp = self._timestamp()
        headers = {
            "OK-ACCESS-KEY": self.ACCESS_KEY,
            "OK-ACCESS-SIGN": self._create_signature(
                timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.PASSPHRASE,
            "Content-Type": "application/json",
        }
        if self.is_demo:
            headers["x-simulated-trading"] = "1"
        return headers

    def _validate_credentials(self):
        """기반 클래스는 access/secret/server_url만 검사하므로 passphrase를 덧붙인다"""
        if not super()._validate_credentials():
            return False
        if not self.PASSPHRASE:
            self.logger.error("OKX passphrase is not configured")
            return False
        return True

    def _unwrap(self, response):
        """OKX 응답 봉투를 해제해 data[0]을 반환. 실패면 None.

        업무 오류가 HTTP 200으로 오고, 실패가 최상위 code와 data[0].sCode 두 층에
        나뉜다. 최상위 code!=0일 때 구체적 사유는 data[0].sMsg에만 담긴다.
        """
        if response is None:
            return None
        data = response.get("data") or []
        first = data[0] if data and isinstance(data[0], dict) else None
        if str(response.get("code")) != "0":
            detail = first.get("sMsg") if first else None
            self.logger.error(
                f"OKX error {response.get('code')}: {detail or response.get('msg')}")
            return None
        if not data:
            self.logger.error("OKX response has empty data")
            return None
        if first is not None and first.get("sCode") not in (None, "", "0"):
            self.logger.error(
                f"OKX order error {first.get('sCode')}: {first.get('sMsg')}")
            return None
        return data[0]

    def _signed_get(self, path, params):
        """서명 GET. 서명 문자열의 requestPath와 실제 URL 쿼리가 반드시 일치해야 하므로
        쿼리를 한 번만 만들어 양쪽에 같이 쓴다 (requests의 params=를 쓰지 않는다)."""
        if not self._validate_credentials():
            return None
        request_path = f"{path}?{urlencode(params)}"
        return self._unwrap(self._request_get(
            self.SERVER_URL + request_path,
            headers=self._auth_headers("GET", request_path),
        ))

    def _signed_post(self, path, payload):
        """서명 POST. 서명한 JSON 문자열과 전송 바디가 반드시 같아야 하므로
        직렬화 결과를 한 번만 만들어 재사용한다."""
        if not self._validate_credentials():
            return None
        body = json.dumps(payload)
        return self._unwrap(self._request_post(
            self.SERVER_URL + path,
            headers=self._auth_headers("POST", path, body),
            data=body,
        ))

    @staticmethod
    def _format_number(value):
        """지수표기 없이 고정소수점 문자열로 포맷 (OKX 파라미터 대비).
        최대 8자리 소수, 불필요한 0/소수점 제거. instId별 lotSz/tickSz
        정밀 라운딩은 /api/v5/public/instruments 조회가 필요하므로 후속 과제."""
        formatted = f"{float(value):.8f}".rstrip("0").rstrip(".")
        return formatted if formatted else "0"

    def get_trade_tick(self):
        """최근 체결가(현재가) 조회 — public 엔드포인트"""
        return self._unwrap(self._request_get(
            self.SERVER_URL + "/api/v5/market/ticker",
            params={"instId": self.market},
        ))

    def get_account_info(self):
        """계좌 정보를 요청한다 (로컬 잔고/자산 + 실시간 시세)

        Returns:
            {
                balance: 계좌 현금 잔고 (USDT)
                asset: {코인: (평균 매입가, 수량)}
                quote: {코인: 현재가}
                date_time: 현재 시간
            }
        """
        result = {
            "balance": self.balance,
            "asset": {self.market_currency: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        trade_info = self.get_trade_tick()
        if trade_info is not None and "last" in trade_info:
            result["quote"][self.market_currency] = float(trade_info["last"])
        else:
            self.logger.error("fail query quote")
        self.logger.debug(f"account info {result}")
        return result

    def _query_order(self, order_id):
        """주문 상태 조회 (signed GET /api/v5/trade/order)"""
        return self._signed_get(
            "/api/v5/trade/order", {"instId": self.market, "ordId": order_id})

    def _cancel_order(self, order_id):
        """주문 취소 (signed POST /api/v5/trade/cancel-order)

        Binance의 DELETE와 달리 응답은 {ordId, clOrdId, sCode, sMsg}뿐이며
        체결 정보를 담지 않는다.
        """
        return self._signed_post(
            "/api/v5/trade/cancel-order", {"instId": self.market, "ordId": order_id})

    @staticmethod
    def _fill_price(response):
        """체결 평단. OKX는 avgPx를 직접 제공하며, 미체결이면 빈 문자열로 온다."""
        return float(response.get("avgPx") or 0)

    @staticmethod
    def _fill_amount(response):
        """누적 체결 수량. 미체결이면 0."""
        return float(response.get("accFillSz") or 0)

    def cancel_request(self, request_id):
        """거래 요청을 취소한다

        OKX cancel-order 응답에는 체결 정보(accFillSz/avgPx)가 없으므로 취소
        성공/실패와 무관하게 주문 조회로 최종 상태를 확정한다. 취소 실패는
        이미 체결됐을 가능성을 포함하므로 같은 경로로 처리된다.
        """
        if request_id not in self.order_map:
            self.logger.debug(f"already canceled or unknown: {request_id}")
            return

        order = self.order_map[request_id]
        del self.order_map[request_id]
        result = order["result"]

        self._cancel_order(order["order_id"])
        response = self._query_order(order["order_id"])
        if response is None:
            self.logger.error(
                f"fail confirm order state after cancel: {order['order_id']}")
            return

        result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
        result["price"] = self._fill_price(response)
        result["amount"] = self._fill_amount(response)
        result["state"] = "done"
        self._call_callback(order["callback"], result)
```

> `order_spec` import는 Task 4의 `_execute_order`에서 쓴다. Task 3 단계에서 pylint가
> unused-import를 경고하면 Task 4까지 그대로 두고, Task 4 완료 후 다시 확인한다.

- [ ] **Step 4: Register in factory and export**

`smtm/trader/trader_factory.py` — import와 `TRADER_LIST`에 추가:

```python
from .upbit_trader import UpbitTrader
from .bithumb_trader import BithumbTrader
from .binance_trader import BinanceTrader
from .okx_trader import OkxTrader
from .simulation_trader import SimulationTrader
```

```python
    TRADER_LIST = [
        UpbitTrader,
        BithumbTrader,
        BinanceTrader,
        OkxTrader,
    ]
```

`smtm/trader/__init__.py` — 한 줄 추가:

```python
from .okx_trader import OkxTrader
```

`smtm/__init__.py` — `from .trader.binance_trader import BinanceTrader` 바로 아래에 추가:

```python
from .trader.okx_trader import OkxTrader
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py -v`
Expected: PASS (37 tests — Scaffold 14 / Unwrap 6 / SignedRequest 3 / Account 3 / Factory 3 / Cancel 8)

`TypeError: Can't instantiate abstract class OkxTrader with abstract method ...`가 나면
그 이름의 메서드가 빠진 것이다. `Trader`의 추상 메서드 중 `send_request`와
`cancel_all_requests`는 `BaseExchangeTrader`가 제공하고, `get_account_info`와
`cancel_request`는 이 Task에서 `OkxTrader`가 직접 구현한다.

- [ ] **Step 6: Commit**

```bash
git add smtm/trader/okx_trader.py smtm/trader/trader_factory.py \
        smtm/trader/__init__.py smtm/__init__.py \
        tests/unit_tests/okx_trader_test.py
git commit -m "[feat] add OkxTrader with OKX v5 signing, envelope handling and order cancel"
```

---

## Task 4: OkxTrader 주문 전송

**Files:**
- Modify: `smtm/trader/okx_trader.py` (`_execute_order`, `_send_order` 추가)
- Modify: `tests/unit_tests/okx_trader_test.py` (주문 테스트 클래스 추가)

**Interfaces:**
- Consumes: Task 3의 `_signed_post(path, payload)`, `_format_number(value)`, `self.market`,
  `self.balance`, `self.asset`, `self.order_map`, `self._start_timer()`,
  `self._create_success_result(request)`(기반 클래스),
  `order_spec.get_ord_type(request)`, `order_spec.MARKET`, `order_spec.make_rejected_result(request, reason)`.
- Produces:
  - `_execute_order(task)` — `task = {"request": {...}, "callback": callable}`.
    성공 시 `self.order_map[request["id"]] = {"order_id": <ordId>, "callback": ..., "result": ...}`
  - `_send_order(side, ord_type, price, amount) -> dict | None` — `side`는 소문자 `"buy"`/`"sell"`

- [ ] **Step 1: Write the failing tests**

`tests/unit_tests/okx_trader_test.py` 맨 아래에 추가:

```python
@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderOrderTest(unittest.TestCase):
    def _trader(self):
        trader = OkxTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (50000, 1.0)
        trader._start_timer = MagicMock()
        return trader

    @staticmethod
    def _sent_payload(trader):
        return json.loads(trader._request_post.call_args[1]["data"])

    def test_limit_order_sends_px_and_sz_with_cash_mode(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "111", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "l1", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["instId"], "BTC-USDT")
        self.assertEqual(payload["tdMode"], "cash")
        self.assertEqual(payload["side"], "buy")
        self.assertEqual(payload["ordType"], "limit")
        self.assertEqual(payload["px"], "50000")
        self.assertEqual(payload["sz"], "0.1")
        self.assertNotIn("tgtCcy", payload)
        self.assertIn("/api/v5/trade/order", trader._request_post.call_args[0][0])

    def test_market_buy_sends_quote_ccy_total(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "222", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "mb", "type": "buy", "price": 50000, "amount": 0.1,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["ordType"], "market")
        self.assertEqual(payload["side"], "buy")
        self.assertEqual(payload["tgtCcy"], "quote_ccy")
        self.assertEqual(payload["sz"], "5000")  # price * amount
        self.assertNotIn("px", payload)

    def test_market_sell_sends_base_ccy_amount(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "333", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "ms", "type": "sell", "price": 0, "amount": 0.5,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["ordType"], "market")
        self.assertEqual(payload["side"], "sell")
        self.assertEqual(payload["tgtCcy"], "base_ccy")
        self.assertEqual(payload["sz"], "0.5")
        self.assertNotIn("px", payload)

    def test_small_quantity_not_scientific_notation(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "444", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "sm", "type": "sell", "price": 0, "amount": 0.00005,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        body = trader._request_post.call_args[1]["data"]
        self.assertIn('"sz": "0.00005"', body)
        self.assertNotIn("e-", body)

    def test_limit_order_with_zero_price_is_noop(self):
        # price==0은 기존 hold 신호 — 지정가에서는 주문을 내지 않는다
        trader = self._trader()
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "z1", "type": "buy", "price": 0, "amount": 0.1},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_not_called()

    def test_unsupported_ord_type_rejected(self):
        trader = self._trader()
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "x", "type": "sell", "price": 0, "amount": 1,
                        "ord_type": "oco"},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        self.assertEqual(callback.call_args[0][0]["state"], "failed")

    def test_buy_rejected_when_balance_too_small(self):
        trader = self._trader()
        trader.balance = 100
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "b2", "type": "buy", "price": 50000, "amount": 1.0},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_called_once_with("error!")

    def test_sell_rejected_when_amount_exceeds_asset(self):
        trader = self._trader()
        trader.asset = (50000, 0.1)
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "s2", "type": "sell", "price": 50000, "amount": 1.0},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_called_once_with("error!")

    def test_successful_order_registers_and_callbacks(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "555", "sCode": "0"}]})
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "ok", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": callback,
        })
        self.assertEqual(trader.order_map["ok"]["order_id"], "555")
        callback.assert_called_once()
        self.assertEqual(callback.call_args[0][0]["state"], "requested")
        trader._start_timer.assert_called_once()

    def test_business_error_envelope_reports_error(self):
        # code=1 + sCode 로 오는 업무 오류는 주문 실패로 처리한다
        trader = self._trader()
        trader._request_post = MagicMock(return_value={
            "code": "1", "msg": "",
            "data": [{"ordId": "", "sCode": "51008", "sMsg": "Insufficient balance"}],
        })
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "e1", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": callback,
        })
        callback.assert_called_once_with("error!")
        self.assertNotIn("e1", trader.order_map)

    def test_cancel_type_request_delegates_to_cancel_request(self):
        trader = self._trader()
        trader.cancel_request = MagicMock()
        trader._execute_order({
            "request": {"id": "c1", "type": "cancel", "price": 0, "amount": 0},
            "callback": MagicMock(),
        })
        trader.cancel_request.assert_called_once_with("c1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py::OkxTraderOrderTest -v`
Expected: FAIL — `_execute_order`가 없거나 아무 것도 하지 않아 `_request_post`가 호출되지 않음

- [ ] **Step 3: Write the implementation**

`smtm/trader/okx_trader.py`의 `get_account_info` 아래에 추가:

```python
    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        ord_type = order_spec.get_ord_type(request)
        if ord_type not in self.SUPPORTED_ORD_TYPES:
            task["callback"](order_spec.make_rejected_result(
                request, f"unsupported ord_type: {ord_type}"))
            return

        is_buy = request["type"] == "buy"
        is_market = ord_type == order_spec.MARKET

        if not is_market and request["price"] == 0:
            # price==0 은 기존 no-op(hold) 신호 — 지정가에서는 무시
            self.logger.warning("[REJECT] limit order requires price")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning(
                f"[REJECT] balance is too small! "
                f"{float(request['price']) * float(request['amount'])} > {self.balance}"
            )
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        side = "buy" if is_buy else "sell"
        response = self._send_order(
            side, ord_type, request["price"], request["amount"])
        if response is None or not response.get("ordId"):
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["ordId"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()

    def _send_order(self, side, ord_type, price, amount):
        """OKX 현물 주문 전송 (signed POST /api/v5/trade/order)

        - 지정가:      ordType=limit, px(가격), sz(코인 수량)
        - 시장가 매수:  ordType=market, tgtCcy=quote_ccy, sz(USDT 총액)
        - 시장가 매도:  ordType=market, tgtCcy=base_ccy,  sz(코인 수량)

        tgtCcy는 현물 시장가에서 방향에 따라 기본값이 달라지므로 양쪽 모두 명시한다.
        """
        payload = {"instId": self.market, "tdMode": "cash", "side": side}
        if ord_type == order_spec.MARKET and side == "buy":
            payload["ordType"] = "market"
            payload["tgtCcy"] = "quote_ccy"
            payload["sz"] = self._format_number(float(price) * float(amount))
        elif ord_type == order_spec.MARKET:
            payload["ordType"] = "market"
            payload["tgtCcy"] = "base_ccy"
            payload["sz"] = self._format_number(amount)
        else:
            payload["ordType"] = "limit"
            payload["px"] = self._format_number(price)
            payload["sz"] = self._format_number(amount)

        self.logger.info(f"ORDER ##### {side} {payload['ordType']}")
        self.logger.info(f"{self.market}, payload: {payload}")
        return self._signed_post("/api/v5/trade/order", payload)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py -v`
Expected: PASS (48 tests — Task 3의 37개 + Order 11개)

- [ ] **Step 5: Commit**

```bash
git add smtm/trader/okx_trader.py tests/unit_tests/okx_trader_test.py
git commit -m "[feat] OkxTrader places spot limit/market orders with tgtCcy handling"
```

---

## Task 5: OkxTrader 체결 폴링

**Files:**
- Modify: `smtm/trader/okx_trader.py` (`_update_order_result` 추가)
- Modify: `tests/unit_tests/okx_trader_test.py` (폴링 테스트 클래스 추가)

**Interfaces:**
- Consumes: Task 3의 `_query_order(order_id)`, `_fill_price(response)`, `_fill_amount(response)`,
  `self.TERMINAL_STATES`; 기반 클래스의 `self.order_map`, `self._call_callback(callback, result)`,
  `self._start_timer()`, `self._stop_timer()`, `self.ISO_DATEFORMAT`.
- Produces:
  - `_update_order_result(task)` — `_start_timer()`가 워커에 넣는 타이머 콜백.
    `task` 인자는 쓰지 않는다(`del task`). 종료 상태 주문을 `order_map`에서 비우고,
    남은 주문이 있으면 타이머를 재시작한다.

**⚠️ Binance와 다른 핵심 차이:** `filled`만 종료로 보면 안 된다. `canceled`/`mmp_canceled`도
오더북에서 사라진 상태이므로 `order_map`에 남겨두면 타이머가 **영구 폴링**한다.
(`BinanceTrader`에 남아 있는 결함 — 후속 과제 §3)

- [ ] **Step 1: Write the failing tests**

`tests/unit_tests/okx_trader_test.py` 맨 아래에 추가:

```python
@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderPollingTest(unittest.TestCase):
    def _trader_with_open_order(self):
        trader = OkxTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (0, 0)
        trader._start_timer = MagicMock()
        trader._stop_timer = MagicMock()
        cb = MagicMock()
        trader.order_map["ok"] = {
            "order_id": "444",
            "callback": cb,
            "result": {"state": "requested", "request": {"id": "ok"},
                       "type": "buy", "price": 50000, "amount": 0.1, "msg": "success"},
        }
        return trader, cb

    def test_filled_order_triggers_done_callback_and_clears_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "filled", "avgPx": "50000.0",
            "accFillSz": "0.1", "sz": "0.1",
        })
        trader._update_order_result(None)
        done = cb.call_args[0][0]
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["price"], 50000.0)
        self.assertEqual(done["amount"], 0.1)
        self.assertNotIn("ok", trader.order_map)

    def test_live_order_stays_in_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "live", "avgPx": "", "accFillSz": "0",
        })
        trader._update_order_result(None)
        self.assertIn("ok", trader.order_map)
        cb.assert_not_called()

    def test_partially_filled_order_stays_in_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "partially_filled",
            "avgPx": "50000.0", "accFillSz": "0.05",
        })
        trader._update_order_result(None)
        self.assertIn("ok", trader.order_map)
        cb.assert_not_called()

    def test_query_failure_keeps_order_in_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value=None)
        trader._update_order_result(None)
        self.assertIn("ok", trader.order_map)

    def test_canceled_order_is_terminal_and_clears_map(self):
        # 취소된 주문은 오더북에 없다 — 남겨두면 타이머가 영구 폴링한다
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "canceled", "avgPx": "", "accFillSz": "0",
        })
        trader._update_order_result(None)
        self.assertNotIn("ok", trader.order_map)
        done = cb.call_args[0][0]
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["price"], 0)
        self.assertEqual(done["amount"], 0)

    def test_unfilled_cancel_does_not_change_balance_or_asset(self):
        trader, cb = self._trader_with_open_order()
        trader.balance = 1000000
        trader.asset = (0, 0)
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "canceled", "avgPx": "", "accFillSz": "0",
        })
        trader._update_order_result(None)
        self.assertEqual(trader.balance, 1000000)
        self.assertEqual(trader.asset, (0, 0))

    def test_mmp_canceled_is_terminal(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "mmp_canceled", "avgPx": "", "accFillSz": "0",
        })
        trader._update_order_result(None)
        self.assertNotIn("ok", trader.order_map)

    def test_partial_fill_then_cancel_reports_filled_amount(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "canceled",
            "avgPx": "49000.0", "accFillSz": "0.04",
        })
        trader._update_order_result(None)
        done = cb.call_args[0][0]
        self.assertEqual(done["price"], 49000.0)
        self.assertEqual(done["amount"], 0.04)

    def test_remaining_orders_restart_the_timer(self):
        trader, _ = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "live", "avgPx": "", "accFillSz": "0",
        })
        trader._update_order_result(None)
        trader._start_timer.assert_called_once()

    def test_no_remaining_orders_does_not_restart_the_timer(self):
        trader, _ = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "filled", "avgPx": "50000.0", "accFillSz": "0.1",
        })
        trader._update_order_result(None)
        trader._start_timer.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py::OkxTraderPollingTest -v`
Expected: FAIL — `AttributeError: 'OkxTrader' object has no attribute '_update_order_result'`

- [ ] **Step 3: Write the implementation**

`smtm/trader/okx_trader.py`의 `_send_order` 아래에 추가
(`_query_order`/`_cancel_order`/`_fill_price`/`_fill_amount`/`cancel_request`는 Task 3에서 이미 만들었다):

```python
    def _update_order_result(self, task):
        del task
        waiting_request = {}
        self.logger.debug(f"waiting order count {len(self.order_map)}")
        for request_id, order in self.order_map.items():
            response = self._query_order(order["order_id"])
            if response is None:
                waiting_request[request_id] = order
                continue
            # filled 외에 canceled/mmp_canceled도 종료 상태다. 남겨두면
            # 오더북에 없는 주문을 타이머가 영구 폴링한다.
            if response.get("state") in self.TERMINAL_STATES:
                result = order["result"]
                result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
                result["price"] = self._fill_price(response)
                result["amount"] = self._fill_amount(response)
                result["state"] = "done"
                self._call_callback(order["callback"], result)
            else:
                waiting_request[request_id] = order

        self.order_map = waiting_request
        self.logger.debug(f"After update, waiting order count {len(self.order_map)}")
        self._stop_timer()
        if len(self.order_map) > 0:
            self._start_timer()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit_tests/okx_trader_test.py -v`
Expected: PASS (58 tests — Task 4의 48개 + Polling 10개)

- [ ] **Step 5: Run the whole unit test suite for regressions**

Run: `python -m pytest tests/unit_tests -q`
Expected: PASS — 신규 테스트 포함 전부 통과. 실패가 있으면 그것부터 고친다.

- [ ] **Step 6: Commit**

```bash
git add smtm/trader/okx_trader.py tests/unit_tests/okx_trader_test.py
git commit -m "[feat] OkxTrader polls fills and treats canceled states as terminal"
```

---

## Task 6: 문서 갱신 (OKX 안내 + 낡은 서술 정정)

OKX 안내를 추가하고, **Binance Trader 구현 이후 이미 사실과 달라진 서술**을 함께 바로잡는다.

**Files:**
- Modify: `README.md`, `README-ko-kr.md`
- Modify: `docs/exchanges-and-trading-ko.md`
- Modify: `docs/public/faq.md`, `docs/public/data-providers.md`, `docs/public/architecture.md`, `docs/public/requirements.md`
- Modify: `docs/wiki/SMTM_프로젝트_소개.md`

**Interfaces:**
- Consumes: Task 1–5의 최종 동작(환경변수 이름, 거래소 코드, 지원 통화·주기, 데모 스위치).
- Produces: 문서만 변경. 코드 변경 없음.

- [ ] **Step 1: README.md — 환경변수 블록**

`# Binance exchange (exchange code BNC)` 블록 **다음**에 삽입:

```
# OKX exchange (exchange code OKX)
OKX_API_ACCESS_KEY=your_okx_access_key
OKX_API_SECRET_KEY=your_okx_secret_key
OKX_API_PASSPHRASE=your_okx_api_passphrase
OKX_API_SERVER_URL=https://www.okx.com
# OKX_API_DEMO=1   # demo trading; needs API keys issued by the OKX demo account
```

- [ ] **Step 2: README.md — 지원 거래소 표**

`| \`BNC\` | Binance | Binance | Spot trading supported, USDT-based budget |` **다음 줄**에 삽입:

```
| `OKX` | OKX | OKX | Spot trading supported, USDT-based budget; requires an API passphrase |
```

- [ ] **Step 3: README-ko-kr.md — 환경변수 블록**

`# Binance 거래소 (거래소 코드 BNC)` 블록 **다음**에 삽입:

```
# OKX 거래소 (거래소 코드 OKX)
OKX_API_ACCESS_KEY=your_okx_access_key
OKX_API_SECRET_KEY=your_okx_secret_key
OKX_API_PASSPHRASE=your_okx_api_passphrase
OKX_API_SERVER_URL=https://www.okx.com
# OKX_API_DEMO=1   # 데모 거래. OKX 데모 계정에서 발급한 키가 따로 필요합니다
```

- [ ] **Step 4: README-ko-kr.md — 지원 거래소 표와 안내 문구**

`| \`BNC\` | Binance | Binance | 현물(spot) 매매 지원, 예산은 USDT 기준 |` **다음 줄**에 삽입:

```
| `OKX` | OKX | OKX | 현물(spot) 매매 지원, passphrase 필요, 예산은 USDT 기준 |
```

같은 절의 안내 문구를 교체:
- 기존: `> 💡 거래소별 사용법·환경변수·세션 생성 예시는 **[지원 거래소와 매매 가이드](docs/exchanges-and-trading-ko.md)**를 참고하세요. (Upbit·Bithumb·Binance 실거래 지원)`
- 변경: `> 💡 거래소별 사용법·환경변수·세션 생성 예시는 **[지원 거래소와 매매 가이드](docs/exchanges-and-trading-ko.md)**를 참고하세요. (Upbit·Bithumb·Binance·OKX 실거래 지원)`

- [ ] **Step 5: docs/exchanges-and-trading-ko.md — 개요·표·주문유형**

① 첫 문단 교체:
- 기존: `smtm은 이제 **Upbit·Bithumb·Binance** 세 거래소에서 실거래가 가능하며,`
- 변경: `smtm은 이제 **Upbit·Bithumb·Binance·OKX** 네 거래소에서 실거래가 가능하며,`

② 한눈에 보기 표의 `BNC` 행 **다음**에 삽입:

```
| `OKX` | OKX | **USDT** | BTC, ETH, DOGE, XRP | ✅ | **신규** — API passphrase 필요, 예산·금액이 USDT 기준 |
```

③ 표 아래 안내 문구 교체:
- 기존: `실주문 실행 Trader가 연결된 코드는 현재 \`UPB\`/\`BTH\`/\`BNC\` 세 가지이며,`
- 변경: `실주문 실행 Trader가 연결된 코드는 현재 \`UPB\`/\`BTH\`/\`BNC\`/\`OKX\` 네 가지이며,`

④ 주문 유형 표의 헤더 교체:
- 기존: `| 주문 유형 | Upbit / Bithumb / Binance (실거래) | 가상거래(Simulation) |`
- 변경: `| 주문 유형 | Upbit / Bithumb / Binance / OKX (실거래) | 가상거래(Simulation) |`

⑤ 주문 유형 표 아래 첫 불릿 교체:
- 기존: `- **시장가/지정가**는 세 거래소 모두에서 동작합니다.`
- 변경: `- **시장가/지정가**는 네 거래소 모두에서 동작합니다.`

⑥ 손절/익절 불릿의 `(Binance stop/OCO 등)` → `(Binance/OKX stop·OCO 등)`

- [ ] **Step 6: docs/exchanges-and-trading-ko.md — 환경변수·예시·주의사항**

① 환경변수 코드블록에서 Binance 3줄 **다음**에 삽입:

```
# OKX (거래소 코드 OKX) — 현물(spot)
OKX_API_ACCESS_KEY=your_okx_access_key
OKX_API_SECRET_KEY=your_okx_secret_key
OKX_API_PASSPHRASE=your_okx_api_passphrase
OKX_API_SERVER_URL=https://www.okx.com
```

② 코드블록 아래 안내 문구 **다음**에 한 줄 추가:

```
> OKX는 access/secret 외에 **passphrase**가 필요합니다. 계좌 등록 시 `passphrase_env`에 passphrase가 담긴 환경변수 '이름'을 함께 지정하세요(값이 아닙니다). 지정하지 않으면 전역 `OKX_API_PASSPHRASE`를 사용합니다.
```

③ `### 예시 — 가상거래로 먼저 검증` **앞**에 새 예시 절 삽입:

```markdown
### 예시 — OKX (USDT)

```
my-okx 계좌 등록해줘: 거래소 OKX, 액세스키 환경변수 OKX_API_ACCESS_KEY, 시크릿키 환경변수 OKX_API_SECRET_KEY, passphrase 환경변수 OKX_API_PASSPHRASE
okx-btc 프로파일 만들어줘: 거래소 OKX, 통화 BTC, 예산 300, 전략 SMA, 주기 60초, 실거래(virtual false), 계좌 my-okx
okx-btc로 세션 만들고 시작해줘
```

> **데모 거래로 먼저 확인하기**: `OKX_API_DEMO=1`을 설정하면 같은 엔드포인트에 `x-simulated-trading: 1` 헤더가 붙어 OKX 데모 환경으로 주문이 나갑니다. 단 **데모 환경은 데모 계정에서 별도 발급한 API 키만 받습니다** — 실계정 키를 그대로 쓰면 인증 오류가 납니다. 거래소 API를 아예 타지 않는 완전한 오프라인 검증이 필요하면 `virtual: true`(가상거래)를 쓰세요.
```

④ 주의사항 절의 불릿 3개 교체:
- 기존: `- **Binance는 USDT 기준**: 예산·수익·거래금액이 모두 USDT입니다. KRW 거래소(Upbit/Bithumb)와 숫자를 혼동하지 마세요.`
- 변경: `- **Binance·OKX는 USDT 기준**: 예산·수익·거래금액이 모두 USDT입니다. KRW 거래소(Upbit/Bithumb)와 숫자를 혼동하지 마세요.`

- 기존: `- **⚠️ USDT 세션의 안전장치 설정**: ... Binance(USDT) 세션은 프로파일의 \`safety\` 설정에서 **반드시 USDT 기준 값으로 지정**하세요. (거래소별 통화 인지형 기본값은 후속 과제)`
- 변경: `- **⚠️ USDT 세션의 안전장치 설정**: \`SafetyGuard\`의 금액 기반 기본값(\`max_trade_amount=100000\`, \`initial_budget\`)은 **KRW 전제**입니다. Binance·OKX(USDT) 세션은 프로파일의 \`safety\` 설정에서 **반드시 USDT 기준 값으로 지정**하세요. 지정하지 않으면 사실상 한도가 없는 것과 같습니다. (거래소별 통화 인지형 기본값은 후속 과제)`

- 기존: `- **시장가 매수 의미 차이**: 시장가 매수 시 Upbit/Binance는 "총액 지출"(price×amount) 기준으로 동작합니다. 시장가 매도는 세 거래소 모두 "수량" 기준입니다.`
- 변경: `- **시장가 매수 의미 차이**: 시장가 매수 시 Upbit/Binance/OKX는 "총액 지출"(price×amount) 기준으로 동작합니다(OKX는 \`tgtCcy=quote_ccy\`). 시장가 매도는 네 거래소 모두 "수량" 기준입니다.`

⑤ 주의사항 절 맨 끝에 불릿 추가:

```
- **주문 수량 정밀도**: Binance·OKX 모두 심볼별 최소 주문 단위(`lotSz`/`stepSize`)와 가격 단위(`tickSz`/`tickSize`) 라운딩이 아직 적용되지 않았습니다. 소액 주문이 거래소에서 거부될 수 있습니다. (후속 과제)
```

⑥ 관련 문서 절의 spec 줄 **다음**에 한 줄 추가:

```
- OKX 지원 설계: `docs/superpowers/specs/2026-07-25-okx-exchange-support-design.md`
```

- [ ] **Step 7: docs/public/faq.md — 낡은 서술 2곳 정정**

① `**Q. 어떤 거래소를 지원하나요?**` 답변 교체:
- 기존: `A. 실주문까지 가능한 거래소(Trader 구현 존재)는 **Upbit(\`UPB\`)** 와 **Bithumb(\`BTH\`)** 두 곳입니다. Binance(\`BNC\`)와 Upbit+Binance 병합(\`UBD\`)은 **데이터 조회만** 지원합니다.`
- 변경: `A. 실주문까지 가능한 거래소(Trader 구현 존재)는 **Upbit(\`UPB\`)**, **Bithumb(\`BTH\`)**, **Binance(\`BNC\`)**, **OKX(\`OKX\`)** 네 곳입니다. Upbit+Binance 병합(\`UBD\`)은 **데이터 조회만** 지원합니다.`

② `**Q. 거래소 코드 \`UPB\`와 \`BNC\`의 차이는?**` 문항 전체 교체:

```markdown
**Q. 거래소 코드 `UPB`와 `BNC`의 차이는?** (프로파일의 `exchange` 설정값)
A. 결제 통화와 거래소가 다릅니다. `UPB`는 Upbit 시장 데이터 + Upbit 실주문(KRW 기준), `BNC`는 Binance 시장 데이터 + Binance 현물 실주문(USDT 기준)입니다. `OKX`도 USDT 기준 현물 실주문을 지원하며, access/secret 외에 **API passphrase**가 추가로 필요합니다. 반면 `UBD`처럼 Trader가 없는 코드는 주문이 불가합니다(Factory가 `None`을 반환해 실행이 중단됩니다).
```

- [ ] **Step 8: docs/public/data-providers.md — 표 행 추가 + 낡은 주석 정정**

① `| \`BinanceDataProvider\` | \`BNC\` | ... |` 행 **다음**에 삽입:

```
| `OkxDataProvider` | `OKX` | `https://www.okx.com/api/v5/market/candles` | 동일 스키마(환산) | 불필요 |
```

② 아래 인용 문구 교체:
- 기존: `> **주문 가능 여부**: Trader가 존재하는 거래소는 Upbit(\`UPB\`) · Bithumb(\`BTH\`) 두 곳입니다. \`BNC\` · \`UBD\`는 데이터 전용.`
- 변경: `> **주문 가능 여부**: Trader가 존재하는 거래소는 Upbit(\`UPB\`) · Bithumb(\`BTH\`) · Binance(\`BNC\`) · OKX(\`OKX\`) 네 곳입니다. \`UBD\`는 데이터 전용.`

- [ ] **Step 9: docs/public/architecture.md — Integration 행 갱신**

`| Integration | 시장 데이터 / 주문 실행 | ...` 행에서 두 곳을 교체:
- `DataProvider 8종 (UPB · BTH · BNC · UBD · UPN · UMN · USC · UFC)` → `DataProvider 9종 (UPB · BTH · BNC · OKX · UBD · UPN · UMN · USC · UFC)`
- `\`Trader\` 2종 (+ Factory)` → `\`Trader\` 4종 (UPB · BTH · BNC · OKX, + Factory)`

- [ ] **Step 10: docs/wiki/SMTM_프로젝트_소개.md — 거래소 코드 표 정정**

`| \`BNC\` | Binance | — | 데이터 전용 |` 행을 두 줄로 교체:

```
| `BNC` | Binance | Binance | 현물(spot), USDT 기준 |
| `OKX` | OKX | OKX | 현물(spot), USDT 기준, passphrase 필요 |
```

- [ ] **Step 11: docs/public/requirements.md — 지원 코드·체크리스트 정정**

① `R-DATA-02` 교체:
- 기존: `- **[MVP] R-DATA-02** — 다음 코드를 지원한다: \`UPB\`(Upbit), \`BTH\`(Bithumb), \`BNC\`(Binance), \`UBD\`(Upbit+Binance 병합), \`UPN\`(Upbit+뉴스 RSS).`
- 변경: `- **[MVP] R-DATA-02** — 다음 코드를 지원한다: \`UPB\`(Upbit), \`BTH\`(Bithumb), \`BNC\`(Binance), \`OKX\`(OKX), \`UBD\`(Upbit+Binance 병합), \`UPN\`(Upbit+뉴스 RSS).`

② 4.1 설정 체크리스트 항목 교체(`BNC`는 이제 Trader가 있으므로 예시가 틀렸다):
- 기존: `- [ ] \`exchange\` 설정값을 \`BNC\`처럼 Trader가 없는 코드로 지정하면 안전하게 거부되는가`
- 변경: `- [ ] \`exchange\` 설정값을 \`UBD\`처럼 Trader가 없는 코드로 지정하면 안전하게 거부되는가`

③ 4.1 설정 체크리스트 맨 끝에 항목 추가:

```
- [ ] OKX 실거래 세션에서 `OKX_API_PASSPHRASE`(또는 계좌의 `passphrase_env`)가 없으면 주문이 차단되고 명확한 로그가 남는가
```

- [ ] **Step 12: Verify no stale claims remain**

Run:
```bash
grep -rn "데이터 전용\|Trader가 없\|Trader 2종\|두 곳입니다" README.md README-ko-kr.md docs/public docs/wiki docs/exchanges-and-trading-ko.md
```
Expected: `UBD`에 대한 서술만 남아야 한다. `BNC`가 "데이터 전용"이라거나 "Trader 2종"이라는 문장이
남아 있으면 고친다. (`docs/superpowers/` 아래의 과거 스펙·계획 문서는 당시 기록이므로 수정하지 않는다.)

Run:
```bash
grep -rn "OKX" README.md README-ko-kr.md docs/exchanges-and-trading-ko.md docs/public docs/wiki | wc -l
```
Expected: 15줄 이상 (모든 문서에 OKX가 반영됐는지 대략 확인)

- [ ] **Step 13: Run the full test suite one more time**

Run: `python -m pytest tests/unit_tests -q`
Expected: PASS (문서 변경이 코드에 영향을 주지 않았음을 확인)

- [ ] **Step 14: Commit**

```bash
git add README.md README-ko-kr.md docs/exchanges-and-trading-ko.md \
        docs/public/faq.md docs/public/data-providers.md \
        docs/public/architecture.md docs/public/requirements.md \
        docs/wiki/SMTM_프로젝트_소개.md
git commit -m "[docs] document OKX trading support and correct stale Trader coverage claims"
```

---

## 완료 조건

- [ ] `python -m pytest tests/unit_tests -q` 전부 통과
- [ ] `python -m pytest tests/integration_tests/okx_data_provider_ITG_test.py -v` 통과 (네트워크 필요)
- [ ] `DataProviderFactory.create("OKX")` → `OkxDataProvider`, `TraderFactory.create("OKX")` → `OkxTrader`
- [ ] `passphrase_env`가 있는 계좌로 `OKX`를 만들면 전달되고, `BNC`를 만들면 `TypeError` 없이 무시된다
- [ ] `passphrase` 미설정 시 OKX 주문이 전송되지 않고 에러 로그가 남는다
- [ ] 문서에서 "`BNC`는 데이터 전용" 류의 낡은 서술이 사라졌다

## 후속 과제 (이번 범위 밖 — 스펙 §6)

1. Binance·OKX 공통: `lotSz`/`tickSz`/`minSz` 정밀 라운딩 (`/api/v5/public/instruments`, `/api/v3/exchangeInfo`)
2. 거래소별 통화 인지형 `SafetyConfig` 기본값 (USDT 세션이 KRW 기본값을 쓰는 문제)
3. `BinanceTrader._update_order_result`가 `CANCELED`/`EXPIRED`를 종료로 보지 않아 영구 폴링하는 결함
4. `BinanceDataProvider`의 `600 → "10m"` 잘못된 매핑
