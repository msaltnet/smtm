# smtm — DataProvider 카탈로그

이 문서는 smtm에 내장된 모든 DataProvider가 **어디서(엔드포인트) 어떤 정보를(필드·타입) 가져오는지**를 한 눈에 정리한 레퍼런스입니다. 신규 소스를 붙이거나 기존 소스를 교체할 때 참고하세요.

- 최종 갱신일: 2026-04-22
- 기준 버전: 1.7.1
- 계약 정의: [`architecture.md §3.4`](architecture.md#34-dataprovider-다형-데이터-계약), `smtm/data/data_provider.py`
- 전체 목록: `smtm/data/` 및 `DataProviderFactory.DataProvider_LIST`

---

## 1. 한눈에 보기

`DataProvider.get_info()`는 `type` 필드로 자기 스키마를 알리는 딕셔너리 리스트를 반환합니다. 하나의 Provider가 여러 타입을 섞어 돌려줄 수 있습니다(예: `UpbitNewsDataProvider`는 `primary_candle` + `news`).

| 구분 | Provider 수 | 생성 `type` |
|------|------------|-------------|
| 거래소 캔들 | 4 | `primary_candle`, `binance` |
| 뉴스(RSS) | 10 | `news` |
| 소셜 | 4 | `reddit`, `hackernews` |
| 감정/지표 | 1 | `sentiment_index` |
| 가격 스냅샷 | 2 | `price_snapshot` |
| 온체인 | 3 | `onchain_stats`, `mempool_fees`, `eth_gas` |
| 파생 | 3 | `funding_rate`, `open_interest`, `long_short_ratio` |
| 거래소 공지 | 1 | `notice` |
| 매크로/환율 | 1 | `exchange_rate` |
| 전통시장/매크로 지수 | 1 | `macro_market` |
| 크립토 글로벌 지표 | 1 | `crypto_global` |
| 복합(Factory 등록) | 4 | 위 타입들의 조합 |

"Factory 등록"된 Provider는 프로파일의 `exchange` 설정값(채팅으로 지정)에 코드를 넣어 바로 선택할 수 있고, 그 외는 코드에서 직접 `from smtm import ...`로 사용합니다.

---

## 2. 거래소 캔들 (numeric)

실매매의 뼈대가 되는 **주거래 캔들**(`type='primary_candle'`)을 생성하는 Provider입니다. OHLCV + 누적 거래량을 동일 스키마로 제공합니다.

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 인증 |
|--------|--------|----------------|-----------|------|
| `UpbitDataProvider` | `UPB` | `https://api.upbit.com/v1/candles/minutes/{1,3,5,10}` | market, date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume | 불필요 |
| `BithumbDataProvider` | `BTH` | `https://api.bithumb.com/public/candlestick/{BTC_KRW}/1m` | 동일 스키마 | 불필요 |
| `BinanceDataProvider` | `BNC` | `https://api.binance.com/api/v3/klines` | 동일 스키마(환산) | 불필요 |
| `UpbitBinanceDataProvider` | `UBD` | Upbit + Binance 병합 | `primary_candle`(Upbit) + `binance`(Binance) 두 건 | 불필요 |

> **주문 가능 여부**: Trader가 존재하는 거래소는 Upbit(`UPB`) · Bithumb(`BTH`) 두 곳입니다. `BNC` · `UBD`는 데이터 전용.

---

## 3. 뉴스 (RSS → `type='news'`)

공개 RSS 피드를 파싱해 `title / summary / source / url / date_time` 스키마로 정규화합니다. 기본 `NewsDataProvider`는 **생성자에 URL을 주입하면 임의의 RSS**에 연결할 수 있고, 주요 매체 프리셋은 서브클래스로 제공합니다.

| 클래스 | `CODE` | 소스 엔드포인트 | `source` 라벨 | 인증 |
|--------|--------|----------------|--------------|------|
| `NewsDataProvider` | `NWS` | `https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml` (기본) | `coindesk` | 불필요 |
| `CoinTelegraphNewsDataProvider` | `CTN` | `https://cointelegraph.com/rss` | `cointelegraph` | 불필요 |
| `DecryptNewsDataProvider` | `DCN` | `https://decrypt.co/feed` | `decrypt` | 불필요 |
| `CryptoSlateNewsDataProvider` | `CSN` | `https://cryptoslate.com/feed/` | `cryptoslate` | 불필요 |
| `BitcoinMagazineNewsDataProvider` | `BMN` | `https://bitcoinmagazine.com/.rss/full/` | `bitcoinmagazine` | 불필요 |
| `TheBlockNewsDataProvider` | `TBN` | `https://www.theblock.co/rss.xml` | `theblock` | 불필요 |
| `WSJMarketsNewsDataProvider` | `WSJ` | `https://feeds.a.dj.com/rss/RSSMarketsMain.xml` | `wsj_markets` | 불필요 |
| `MarketWatchNewsDataProvider` | `MWN` | `http://feeds.marketwatch.com/marketwatch/topstories/` | `marketwatch` | 불필요 |
| `CNBCFinanceNewsDataProvider` | `CNB` | `https://www.cnbc.com/id/10000664/device/rss/rss.html` | `cnbc_finance` | 불필요 |
| `MultiNewsDataProvider` | `MNS` | 위 4개 크립토 매체를 동시에 호출해 합산 | 원본 라벨 그대로 | 불필요 |

> WSJ / MarketWatch / CNBC / The Block 은 **크립토·주식·매크로가 섞인 일반 금융 뉴스**입니다. 크립토 전용 프리셋(`CTN/DCN/CSN/BMN`)과 구분해 선택적으로 조합하세요.

**공통 옵션**: `count`(1회 반환 건수), `url`/`source`(커스텀 피드). **실패 시 빈 리스트 반환** → 매매 루프 차단 없음.

---

## 4. 소셜 (`type='reddit'`, `type='hackernews'`)

커뮤니티 시그널. 모두 공개 API이며 키가 필요 없습니다.

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 특이사항 |
|--------|--------|----------------|-----------|----------|
| `RedditDataProvider` | `RDT` | `https://www.reddit.com/r/{subreddit}/.rss` (Atom) | title, summary, source(`reddit/{sub}`), url, author, date_time | **User-Agent 필수** (내장 기본값 사용) |
| `CryptoCurrencyRedditDataProvider` | `RCC` | `r/CryptoCurrency` 프리셋 | 동일 | — |
| `BitcoinRedditDataProvider` | `RBT` | `r/Bitcoin` 프리셋 | 동일 | — |
| `HackerNewsDataProvider` | `HNS` | `https://hn.algolia.com/api/v1/search_by_date?tags=story&query=...` | title, url(없으면 HN 스토리 URL), author, points, num_comments, date_time | 기본 쿼리 `bitcoin OR crypto OR ethereum` |

---

## 5. 감정/지표 (`type='sentiment_index'`)

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 인증 |
|--------|--------|----------------|-----------|------|
| `FearGreedDataProvider` | `FGI` | `https://api.alternative.me/fng/?limit={N}` | index_name=`crypto_fear_and_greed`, value(0~100), classification, source=`alternative.me/fng`, date_time(timestamp) | 불필요 |

> value 가 낮을수록 공포, 높을수록 탐욕. `limit` 파라미터로 과거 히스토리 누적도 가능.

---

## 6. 가격 스냅샷 (`type='price_snapshot'`)

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 인증 |
|--------|--------|----------------|-----------|------|
| `CoinGeckoDataProvider` | `CGK` | `https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,krw&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true` | prices(dict, 예: {usd, krw}), market_cap_usd, volume_24h_usd, change_24h_pct, coin_id, currency | 불필요(무료 티어) |
| `CoinCapDataProvider` | `CCP` | `https://api.coincap.io/v2/assets/{id}` | prices(`{usd}`), market_cap_usd, volume_24h_usd, change_24h_pct, supply, max_supply, rank, vwap_24h_usd | 불필요 |

**통화 매핑**: `BTC→bitcoin, ETH→ethereum, DOGE→dogecoin, XRP→ripple(or xrp)`. 미지원 통화는 빈 리스트 반환.

> CoinCap은 CoinGecko보다 rate limit이 관대합니다. 둘을 함께 붙이면 교차검증·폴백이 가능합니다(소스 라벨로 구분: `coingecko` / `coincap`).

---

## 7. 온체인 / 네트워크

### 7.1 BTC 네트워크

| 클래스 | `CODE` | 소스 엔드포인트 | 생성 `type` | 주요 필드 |
|--------|--------|----------------|-------------|-----------|
| `BlockchainInfoDataProvider` | `BCI` | `https://api.blockchain.info/stats` | `onchain_stats` | chain, hash_rate_ghs, difficulty, total_btc, n_blocks_total, n_tx_24h, minutes_between_blocks, miners_revenue_usd, market_price_usd, timestamp |
| `MempoolFeesDataProvider` | `MPF` | `https://mempool.space/api/v1/fees/recommended` | `mempool_fees` | unit=`sat/vB`, fastest_fee, half_hour_fee, hour_fee, economy_fee, minimum_fee |

> 두 Provider 모두 **BTC 외 통화에서는 빈 리스트**를 반환합니다.

### 7.2 ETH 네트워크

| 클래스 | `CODE` | 소스 엔드포인트 | 생성 `type` | 주요 필드 |
|--------|--------|----------------|-------------|-----------|
| `EtherscanGasDataProvider` | `EGS` | `https://api.etherscan.io/api?module=gastracker&action=gasoracle` | `eth_gas` | unit=`gwei`, safe_gas_price, propose_gas_price, fast_gas_price, suggest_base_fee, gas_used_ratio, last_block |

- **키 선택**: 키 없이도 호출되지만 rate limit이 낮음. `ETHERSCAN_API_KEY` 환경변수 또는 생성자 `api_key=` 인자로 키를 넣으면 상향됩니다.
- **가스 급등 = 온체인 혼잡 = 단기 변동성 선행 지표**로 활용 가능. BTC 매매 중이어도 ETH 가스는 전체 크립토 활동성의 프록시가 됩니다.

---

## 8. 파생상품 / 포지셔닝

Binance USDT-M 선물의 주요 포지셔닝 지표. `currency` 설정값(BTC/ETH/…)을 기준으로 `{SYMBOL}USDT` 심볼이 자동 조립됩니다. 모든 Provider가 존재하지 않는 심볼에 대해 빈 리스트를 반환합니다.

| 클래스 | `CODE` | 소스 엔드포인트 | 생성 `type` | 주요 필드 |
|--------|--------|----------------|-------------|-----------|
| `BinanceFundingRateDataProvider` | `BFR` | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=...` | `funding_rate` | symbol, funding_rate, funding_rate_pct, mark_price, index_price, next_funding_time, time |
| `BinanceOpenInterestDataProvider` | `BOI` | `https://fapi.binance.com/futures/data/openInterestHist?symbol=...&period=5m&limit=1` | `open_interest` | symbol, period, open_interest_contracts, open_interest_notional_usd, timestamp |
| `BinanceLongShortRatioDataProvider` | `BLS` | `https://fapi.binance.com/futures/data/globalLongShortAccountRatio` (또는 `topLongShortAccountRatio`) | `long_short_ratio` | symbol, period, scope(`global`/`top`), long_short_ratio, long_account_pct, short_account_pct, timestamp |

**해석 포인트**
- **Funding rate 양(+)** → 롱이 숏에게 지급 → 과열 / **음(−)** → 숏이 롱에게 지급 → 공포
- **Open Interest ↑ + 가격 ↑** → 신규 롱 유입(강세) / **OI ↑ + 가격 ↓** → 신규 숏 유입(약세)
- **OI ↓ 급감** → 강제청산·포지션 정리(변동성 꼭지 신호)
- **Long/Short Ratio > 1** → 롱 계정 우세, **< 1** → 숏 우세. 극단값은 역방향 움직임의 잠재 신호(군집심리)
- **`scope="top"`**: 상위 트레이더(큰 지갑) 기준. `global`은 소매 포함 전체. 두 값의 괴리가 의미 있는 신호

---

## 9. 거래소 공지 (`type='notice'`)

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 비고 |
|--------|--------|----------------|-----------|------|
| `UpbitNoticeDataProvider` | `UPT` | `https://api-manager.upbit.com/api/v1/notices?page=1&per_page={N}&thread_name=general` | title, body, url(`https://upbit.com/service_center/notice?id=...`), date_time(listed_at), category, source=`upbit` | **비공식 엔드포인트** — 스키마 변경 가능, 방어적 파싱 내장 |

상장·점검·이벤트 공지를 LLM에 투입해 판단 컨텍스트를 넓힐 때 유용합니다.

---

## 10. 매크로 / 환율 (`type='exchange_rate'`)

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 인증 |
|--------|--------|----------------|-----------|------|
| `ExchangeRateDataProvider` | `FXR` | `https://open.er-api.com/v6/latest/{BASE}` (기본 `BASE=USD`) | base, rates(dict, 기본 `{KRW, JPY, EUR, CNY}`), date_time(time_last_update_utc), source=`open.er-api.com` | 불필요 |

원화 페어의 가격을 USD 기준과 비교하거나, 한국 시장과 글로벌 시장의 괴리를 읽을 때 사용합니다.

---

## 10-A. 전통시장 / 매크로 지수 (`type='macro_market'`)

크립토 가격과 상관도가 높은 **전통금융 시장 지표**를 한 번에 수집합니다. 각 심볼마다 한 건의 딕셔너리가 생성됩니다.

| 클래스 | `CODE` | 소스 엔드포인트 | 기본 심볼 세트 | 인증 |
|--------|--------|----------------|---------------|------|
| `YahooFinanceDataProvider` | `YFN` | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m` | DXY(`DX-Y.NYB`), S&P500(`^GSPC`), VIX(`^VIX`), Gold(`GC=F`), US10Y(`^TNX`), Nasdaq(`^IXIC`) | 불필요(User-Agent 헤더만 필요) |

**주요 필드**: `symbol`, `label`(가독 라벨), `price`(regularMarketPrice), `previous_close`, `change_24h_pct`, `currency`, `exchange`, `timestamp`.

**해석 포인트**
- **DXY ↑** → 달러 강세, 위험자산(BTC 포함) 하방 압력
- **VIX ↑** → 전통시장 공포, 크립토도 동조 가능
- **US10Y ↑** → 실질금리 상승, 위험자산 디스카운트
- **Gold / BTC 동조** → 매크로 헤지 내러티브
- **S&P 500 / Nasdaq** → 리스크 온·오프 일반 바로미터

> `symbols=[("심볼","라벨"), ...]` 리스트를 생성자에 넘기면 다른 조합(예: 원유 `CL=F`, 비트코인 선물 `BTC=F`, 유로달러 `EURUSD=X`)으로 교체 가능합니다. Yahoo Finance는 무료지만 **비공식**이라 과도한 폴링을 지양하세요.

---

## 10-B. 크립토 글로벌 지표 (`type='crypto_global'`)

특정 코인이 아닌 **전체 크립토 시장**의 거시 스냅샷입니다. CoinGecko Global 엔드포인트를 호출해 한 건의 딕셔너리를 반환합니다.

| 클래스 | `CODE` | 소스 엔드포인트 | 주요 필드 | 인증 |
|--------|--------|----------------|-----------|------|
| `CryptoGlobalDataProvider` | `CGL` | `https://api.coingecko.com/api/v3/global` | total_market_cap_usd, total_volume_24h_usd, market_cap_change_24h_pct, btc_dominance_pct, eth_dominance_pct, stablecoin_dominance_pct, dominance(dict), active_cryptocurrencies, markets, updated_at | 불필요(무료 티어) |

**해석 포인트**
- **BTC 도미넌스 ↑** → 알트에서 BTC로 자금 이동(리스크 오프)
- **스테이블코인 도미넌스 ↑** → 관망/대기자금 증가
- **total_volume / market_cap 비율** → 거래 활발도
- **market_cap_change_24h_pct** → 전체 시장 방향성 한 줄 요약

`stablecoin_dominance_pct`는 USDT·USDC·DAI·BUSD·FDUSD·TUSD 도미넌스를 합산한 값입니다.

---

## 11. 복합 Provider (Factory 등록)

여러 소스를 한 번의 `get_info()` 응답으로 합쳐 주는 오케스트레이션 Provider입니다. 프로파일의 `exchange` 설정값으로 바로 선택할 수 있고, 생성자에 `providers=[...]` 리스트를 주입해 구성을 직접 바꿀 수도 있습니다.

| 클래스 | `CODE` | 구성 | 생성 타입(합집합) |
|--------|--------|------|------------------|
| `UpbitNewsDataProvider` | `UPN` | Upbit 캔들 + `NewsDataProvider`(기본 CoinDesk) | `primary_candle`, `news` |
| `UpbitMultiNewsDataProvider` | `UMN` | Upbit 캔들 + `MultiNewsDataProvider`(4개 매체) | `primary_candle`, `news` |
| `UpbitSocialDataProvider` | `USC` | Upbit 캔들 + 다중 뉴스 + r/CryptoCurrency + r/Bitcoin + FGI | `primary_candle`, `news`, `reddit`, `sentiment_index` |
| `UpbitFullContextDataProvider` | `UFC` | Upbit 캔들 + CoinGecko + Blockchain.info + Mempool.space + Binance Funding + FGI + 환율 + Upbit 공지 + 다중 뉴스 + Reddit 2종 + HackerNews | `primary_candle`, `price_snapshot`, `onchain_stats`, `mempool_fees`, `funding_rate`, `sentiment_index`, `exchange_rate`, `notice`, `news`, `reddit`, `hackernews` |

> `UFC`는 가장 무겁습니다. 틱마다 토큰이 크게 증가하므로 `term` 설정값을 길게(예: 300초 이상) 잡거나 실험·연구 용도로 사용하세요.

---

## 12. 실패 처리와 Rate Limit

모든 Provider는 공통 규칙을 따릅니다.

- **네트워크·파싱 오류 → 빈 리스트 반환**. 매매 루프를 막지 않습니다.
- **HTTP 5xx → `request_with_retry`가 최대 2회 지수 백오프 후 재시도** (`smtm/http_session.py`).
- **타임아웃 5초** 기본(각 Provider의 `TIMEOUT` 상수).
- **로그**: 실패는 `logger.warning`으로 남깁니다(`log/smtm.log`).

| 소스 | 공식 Rate Limit (참고치) | 완화 방법 |
|------|-------------------------|----------|
| Upbit / Bithumb / Binance | 공개 티어 기준 초당 수회~수십회 | `term` 설정값 늘리기 |
| CoinGecko 무료 티어 | 분당 ~30회 | `term` 설정값을 60초 이상으로 유지 |
| Reddit | UA 없는 경우 429, UA 있으면 관대 | 기본 UA 사용, 필요 시 `user_agent=` 오버라이드 |
| HackerNews Algolia | 매우 관대 | — |
| alternative.me(FGI) | 명시 없음 | `limit` 작게 유지 |
| mempool.space / blockchain.info | 명시 없음 | 공격적 폴링 지양 |
| Upbit Notice (비공식) | 명시 없음 | 과도한 호출 지양 |
| open.er-api.com | 분당 제한 낮음 | 시간당 1~2회로 충분 |
| Yahoo Finance (비공식) | 명시 없음, User-Agent 없으면 차단 가능 | 기본 UA 사용, 심볼 개수 최소화 |
| CoinGecko Global | CoinGecko 무료 티어 공유(분당 ~30회) | `term` 설정값 60초+ 유지 |
| 일반 금융 RSS(WSJ/MarketWatch/CNBC/The Block) | 명시 없음 | 업데이트 주기가 느리므로 공격적 폴링 불필요 |
| CoinCap | 공개 API, 분당 ~200회 | CoinGecko 백업으로 사용해도 충분 |
| Binance Futures Data(OI/LSR) | 분당 수십회 가용 | `period` 5m+ 권장, `limit=1`만 조회 |
| Etherscan (무키) | IP당 5 req/sec 공유 | 무키면 `term` 설정값 60초+, 키 있으면 `ETHERSCAN_API_KEY` 설정 |

---

## 13. 새 Provider 추가하기

1. `smtm/data/` 아래에 `DataProvider`를 상속한 클래스를 만든다.
2. `NAME`, `CODE`(3자 대문자 권장), `__init__(self, currency="BTC", interval=60, ...)`, `get_info()` 구현.
3. `get_info()`는 `type` 필드가 있는 딕셔너리 리스트를 반환한다. 실패 시 `[]`.
4. 프로파일 설정값으로 노출하려면 `DataProviderFactory.DataProvider_LIST`에 등록한다. 이후 `exchange` 설정값에 `{CODE}`를 넣어 바로 선택할 수 있다.
5. `smtm/__init__.py`에서 export.
6. 단위 테스트는 `@patch("requests.get")`으로 외부 호출을 모킹(기존 `tests/unit_tests/*_data_provider_test.py` 참고).
7. `MarketDataTool.description`에 새 `type`을 한 줄 추가해 LLM에게 해석법을 알려준다.

기존 타입을 그대로 사용한다면 description 수정은 불필요합니다.

---

## 14. 관련 문서

- 시스템 구조와 폴리모픽 계약 → [`architecture.md`](architecture.md)
- 기능 스펙 → [`requirements.md`](requirements.md)
- 자주 묻는 질문(소스·한도·확장) → [`faq.md`](faq.md)
- 버전별 변경 / 로드맵 → [`release-notes.md`](release-notes.md)
