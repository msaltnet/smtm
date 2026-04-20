# SMTM 프로젝트 상세 문서

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [전체 프로젝트 구조와 동작 원리](#전체-프로젝트-구조와-동작-원리)
3. [주요 모듈들의 세부 동작](#주요-모듈들의-세부-동작)
4. [개발 방법](#개발-방법)
5. [전략 추가 방법](#전략-추가-방법)

---

## 프로젝트 개요

**SMTM (Show Me The Money)** 은 파이썬으로 개발된 알고리즘 기반 암호화폐 자동매매 시스템입니다.

### 핵심 특징
- **계층화된 아키텍처**: 확장성과 유지보수성을 고려한 설계
- **다양한 실행 모드**: 시뮬레이션, 실전거래, 텔레그램 봇 등
- **멀티프로세스 대량시뮬레이션**: 여러 전략을 동시에 테스트
- **원격 제어**: Jupyter Notebook과 텔레그램을 통한 원격 관리

### 주요 기능
- 데이터 수집 → 알고리즘 분석 → 실시간 거래의 반복 프로세스
- 다양한 거래소 지원 (Upbit, Bithumb, Binance)
- 실시간 수익률 분석 및 그래프 생성
- 텔레그램 챗봇을 통한 원격 거래 제어

---

## 전체 프로젝트 구조와 동작 원리

### 아키텍처 개요

SMTM은 **3계층 아키텍처**로 설계되어 있습니다:

```
┌─────────────────────────────────────┐
│           Controller Layer          │
│  Simulator, Controller,             │
│  TelegramController, JptController  │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│           Operator Layer            │
│     Operator, SimulationOperator    │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│            Core Layer               │
│  DataProvider, Strategy, Trader,    │
│  Analyzer                           │
└─────────────────────────────────────┘
```

### 동작 원리

#### 1. 데이터 수집 단계 (Data Gathering)
```
Operator → DataProvider: 거래현황 데이터 요청
DataProvider → Operator: OHLC 캔들 데이터 응답
Operator → Analyzer: 거래현황 데이터 업데이트
```

#### 2. 거래 판단 단계 (Trading Judgment)
```
Operator → Strategy: 거래현황 데이터 업데이트
Operator → Strategy: 거래 진행 의사 결정 요청
Strategy → Operator: 거래 진행 의사 결정 응답
Operator → Analyzer: 거래 진행 의사 결정 업데이트
```

#### 3. 거래 실행 단계 (Trading Execution)
```
Operator → Trader: 거래 진행 요청
Trader → Operator: 거래 진행 응답
Trader → Operator: 거래 진행 결과 응답
Operator → Analyzer: 거래 진행 결과 업데이트
```

### 핵심 컴포넌트 간 상호작용

1. **Controller Layer**: 사용자 인터페이스 제공
   - CLI 기반 Controller
   - 텔레그램 챗봇 Controller
   - Jupyter Notebook Controller
   - 시뮬레이터

2. **Operator Layer**: 시스템 운영 관리
   - 주기적 거래 프로세스 실행
   - 모듈 간 조율
   - 상태 관리

3. **Core Layer**: 핵심 기능 구현
   - **DataProvider**: 시장 데이터 수집
   - **Strategy**: 매매 전략 구현
   - **Trader**: 실제 거래 실행
   - **Analyzer**: 성과 분석 및 리포트 생성

---

## 주요 모듈들의 세부 동작

### 1. Operator 모듈 (`smtm/operator.py`)

**역할**: 전체 시스템의 운영을 담당하는 핵심 모듈

**주요 기능**:
- **초기화**: DataProvider, Strategy, Trader, Analyzer 모듈 연결
- **주기적 실행**: 설정된 간격으로 거래 프로세스 반복
- **상태 관리**: ready, running, terminating 상태 관리
- **타이머 관리**: 거래 간격 제어

**핵심 메서드**:
```python
def initialize(self, data_provider, strategy, trader, analyzer, budget=500):
    """운영에 필요한 모듈들을 설정하고 초기화"""

def start(self):
    """자동 거래 시작"""

def stop(self):
    """자동 거래 중지 및 최종 리포트 생성"""

def _execute_trading(self, task):
    """실제 거래 프로세스 실행"""
```

### 2. DataProvider 모듈 (`smtm/data/`)

**역할**: 거래소에서 시장 데이터를 수집하여 표준화된 형태로 제공

**구현체들**:
- `UpbitDataProvider`: 업비트 거래소 데이터
- `BithumbDataProvider`: 빗썸 거래소 데이터
- `BinanceDataProvider`: 바이낸스 거래소 데이터
- `SimulationDataProvider`: 시뮬레이션용 과거 데이터

**데이터 포맷**:
```python
{
    "type": "primary_candle",
    "market": "BTC",
    "date_time": "2023-01-01T00:00:00",
    "opening_price": 1000000,
    "high_price": 1100000,
    "low_price": 950000,
    "closing_price": 1050000,
    "acc_price": 1000000000,
    "acc_volume": 1000
}
```

### 3. Strategy 모듈 (`smtm/strategy/`)

**역할**: 수집된 데이터를 분석하여 매매 결정을 내리는 핵심 모듈

**추상 클래스 구조**:
```python
class Strategy(metaclass=ABCMeta):
    CODE = "---"  # 전략 코드
    NAME = "---"  # 전략 이름

    @abstractmethod
    def initialize(self, budget, min_price, callbacks):
        """전략 초기화"""

    @abstractmethod
    def get_request(self):
        """매매 요청 생성"""

    @abstractmethod
    def update_trading_info(self, info):
        """새로운 거래 정보 업데이트"""

    @abstractmethod
    def update_result(self, result):
        """거래 결과 업데이트"""
```

**구현된 전략들**:

#### StrategyBuyAndHold (BNH)
- **전략**: 분할 매수 후 홀딩
- **특징**: 5번에 걸쳐 예산의 1/5씩 매수
- **용도**: 벤치마크 전략

#### StrategySma0 (SMA)
- **전략**: 이동평균선 교차 전략
- **매수 조건**: 단기 > 중기 > 장기 이동평균선
- **매도 조건**: 단기 < 중기 < 장기 이동평균선
- **특징**: 표준편차 기반 노이즈 필터링

#### StrategySmaMl (SML)
- **전략**: 이동평균선 + 머신러닝
- **특징**: 선형회귀를 이용한 트렌드 분석
- **고급 기능**: 지지/저항선 분석, 분할 매매

#### StrategyRsi (RSI)
- **전략**: RSI 지표 기반 매매
- **특징**: 과매수/과매도 구간에서 매매

### 4. Trader 모듈 (`smtm/trader/`)

**역할**: 실제 거래소와 통신하여 매매 주문을 실행

**구현체들**:
- `UpbitTrader`: 업비트 거래소 연동
- `BithumbTrader`: 빗썸 거래소 연동
- `SimulationTrader`: 시뮬레이션용 가상 거래
- `DemoTrader`: 데모 거래

**주요 메서드**:
```python
def send_request(self, request_list, callback):
    """거래 요청 실행"""

def cancel_request(self, request_id):
    """특정 거래 요청 취소"""

def cancel_all_requests(self):
    """모든 대기 중인 거래 취소"""

def get_account_info(self):
    """계좌 정보 조회"""
```

### 5. Analyzer 모듈 (`smtm/analyzer/`)

**역할**: 거래 성과 분석 및 리포트 생성

**주요 기능**:
- **실시간 수익률 계산**
- **거래 기록 관리**
- **그래프 생성** (캔들차트 + 매매 포인트)
- **리포트 생성** (수익률, 거래 내역 등)

**핵심 메서드**:
```python
def put_trading_info(self, info):
    """거래 정보 저장"""

def put_requests(self, requests):
    """매매 요청 기록"""

def put_result(self, result):
    """거래 결과 기록"""

def create_report(self, tag):
    """최종 리포트 생성"""

def get_return_report(self, graph_filename, index_info):
    """수익률 리포트 생성"""
```

### 6. Controller 모듈들

#### Controller (`smtm/controller/controller.py`)
- **CLI 기반 인터페이스**
- **명령어**: h(도움말), r(시작), s(중지), q(조회), t(종료)

#### TelegramController (`smtm/controller/telegram_controller.py`)
- **텔레그램 봇 연동**
- **원격 거래 제어**
- **실시간 알림**

#### Simulator (`smtm/controller/simulator.py`)
- **시뮬레이션 실행**
- **과거 데이터 기반 백테스팅**

---

## 개발 방법

### 환경 설정

#### 1. 기본 설치
```bash
# 저장소 클론
git clone https://github.com/msaltnet/smtm.git
cd smtm

# 기본 패키지 설치
pip install -r requirements.txt

# 개발용 패키지 설치 (선택사항)
pip install -r requirements-dev.txt
```

#### 2. 환경 변수 설정 (`.env` 파일)
```bash
# 업비트 API (실전 거래용)
UPBIT_OPEN_API_ACCESS_KEY=your_access_key
UPBIT_OPEN_API_SECRET_KEY=your_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# 텔레그램 봇 (봇 모드용)
TELEGRAM_BOT_TOKEN=bot123456789:your_bot_token
TELEGRAM_CHAT_ID=123456789

# 시스템 설정
SMTM_LANG=ko  # 언어 설정 (ko/en)
```

### 실행 모드

#### 1. 시뮬레이션 모드
```bash
# 인터렉티브 시뮬레이터
python -m smtm --mode 0

# 단일 시뮬레이션
python -m smtm --mode 1 --budget 500000 --from_dash_to 201220.080000-201221 --term 0.001 --strategy SMA --currency BTC
```

#### 2. 실전 거래 모드
```bash
# CLI 기반 실전 거래
python -m smtm --mode 2 --budget 100000 --term 60 --strategy BNH --currency ETH

# 텔레그램 봇 모드
python -m smtm --mode 3
```

#### 3. 대량 시뮬레이션
```bash
# 설정 파일로 대량 시뮬레이션
python -m smtm --mode 4 --config /data/sma0_simulation.json

# 설정 파일 생성
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy SMA --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```

### 테스트 방법

#### 1. 단위 테스트
```bash
# 전체 단위 테스트
python -m unittest discover ./tests *test.py -v

# 또는 pytest 사용
python -m pytest ./tests/unit_tests
```

#### 2. 통합 테스트
```bash
# 통합 테스트 실행
python -m unittest integration_tests

# 특정 통합 테스트
python -m unittest integration_tests.simulation_ITG_test
```

#### 3. Jupyter Notebook 테스트
- `notebook/` 폴더의 노트북 파일들을 사용
- 개별 모듈 테스트 및 디버깅에 유용

### 개발 도구

#### 1. 코드 품질 도구
```bash
# 코드 포맷팅
black smtm/

# 린팅
pylint smtm/

# 커버리지 테스트
coverage run --omit="*/test*" -m pytest ./tests/unit_tests
coverage report
```

#### 2. 디버깅
- **로그 레벨 조정**: `Config.operation_log_level` 설정
- **Jupyter Notebook**: 개별 모듈 테스트
- **시뮬레이션 모드**: 실제 거래 없이 전략 테스트

---

## 전략 추가 방법

### 1. 기본 전략 클래스 구조

새로운 전략을 추가하려면 `Strategy` 추상 클래스를 상속받아 구현해야 합니다:

```python
from smtm.strategy.strategy import Strategy
from smtm.log_manager import LogManager
from smtm.date_converter import DateConverter

class MyCustomStrategy(Strategy):
    # 전략 식별자
    NAME = "My Custom Strategy"
    CODE = "MCS"

    # 전략별 상수
    COMMISSION_RATIO = 0.0005
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        # 전략별 상태 변수 초기화
        self.is_initialized = False
        self.budget = 0
        self.balance = 0
        self.data = []
        self.logger = LogManager.get_logger(__class__.__name__)
        # 기타 필요한 변수들...

    def initialize(self, budget, min_price=5000, add_spot_callback=None, 
                   add_line_callback=None, alert_callback=None):
        """전략 초기화"""
        if self.is_initialized:
            return

        self.is_initialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
        # 콜백 함수 저장
        self.add_spot_callback = add_spot_callback
        self.add_line_callback = add_line_callback
        self.alert_callback = alert_callback

    def update_trading_info(self, info):
        """새로운 거래 정보 업데이트"""
        if not self.is_initialized:
            return

        # primary_candle 데이터 추출
        target = None
        for item in info:
            if item["type"] == "primary_candle":
                target = item
                break

        if target is None:
            return

        # 데이터 저장 및 분석
        self.data.append(target)
        self._analyze_data(target)

    def get_request(self):
        """매매 요청 생성"""
        if not self.is_initialized or len(self.data) == 0:
            return None

        # 전략 로직에 따른 매매 결정
        request = self._make_trading_decision()

        if request is None:
            return None

        # 요청 정보 생성
        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        if self.is_simulation:
            now = self.data[-1]["date_time"]

        request["date_time"] = now
        request["id"] = DateConverter.timestamp_id()

        return [request]

    def update_result(self, result):
        """거래 결과 업데이트"""
        if not self.is_initialized:
            return

        # 거래 결과 처리
        request = result["request"]

        if result["state"] == "requested":
            # 대기 중인 요청으로 저장
            self.waiting_requests[request["id"]] = result
            return

        if result["state"] == "done":
            # 거래 완료 처리
            self._process_trade_result(result)

    def _analyze_data(self, data):
        """데이터 분석 로직"""
        # 전략별 분석 로직 구현
        pass

    def _make_trading_decision(self):
        """매매 결정 로직"""
        # 전략별 매매 결정 로직 구현
        return None

    def _process_trade_result(self, result):
        """거래 결과 처리"""
        # 잔고 업데이트 등
        pass
```

### 2. StrategyFactory에 등록

새로운 전략을 시스템에 등록하려면 `StrategyFactory`에 추가해야 합니다:

```python
# smtm/strategy/strategy_factory.py 수정

from .strategy_bnh import StrategyBuyAndHold
from .strategy_sma_0 import StrategySma0
from .strategy_rsi import StrategyRsi
from .strategy_sma_ml import StrategySmaMl
from .strategy_sma_dual_ml import StrategySmaDualMl
from .strategy_sas import StrategySas
from .strategy_hey import StrategyHey
from .my_custom_strategy import MyCustomStrategy  # 새 전략 추가

class StrategyFactory:
    STRATEGY_LIST = [
        StrategyBuyAndHold,
        StrategySma0,
        StrategyRsi,
        StrategySmaMl,
        StrategySmaDualMl,
        StrategySas,
        StrategyHey,
        MyCustomStrategy,  # 새 전략 추가
    ]
```

### 3. 전략 개발 가이드라인

#### 기본 구조 준수
- **상태 관리**: `is_initialized` 플래그로 초기화 상태 관리
- **데이터 저장**: `self.data` 리스트에 거래 데이터 저장
- **잔고 관리**: `self.balance`로 현금 잔고 추적
- **로깅**: `self.logger`로 전략별 로그 기록

#### 매매 요청 형식
```python
{
    "id": "고유_요청_ID",
    "type": "buy" | "sell" | "cancel",
    "price": 거래_가격,
    "amount": 거래_수량,
    "date_time": "요청_시간"
}
```

#### 거래 결과 처리
```python
{
    "request": 원본_요청_정보,
    "type": "buy" | "sell" | "cancel",
    "price": 체결_가격,
    "amount": 체결_수량,
    "state": "requested" | "done",
    "msg": "success" | "error_message",
    "date_time": "체결_시간"
}
```

### 4. 전략 테스트 방법

#### 시뮬레이션 테스트
```bash
# 새 전략으로 시뮬레이션 실행
python -m smtm --mode 1 --budget 100000 --strategy MCS --currency BTC --from_dash_to 20230101.000000-20230107.000000
```

#### 단위 테스트 작성
```python
# tests/unit_tests/strategy_my_custom_test.py

import unittest
from smtm.strategy.my_custom_strategy import MyCustomStrategy

class TestMyCustomStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MyCustomStrategy()
        
    def test_initialize(self):
        self.strategy.initialize(100000)
        self.assertTrue(self.strategy.is_initialized)
        self.assertEqual(self.strategy.budget, 100000)
        
    def test_update_trading_info(self):
        self.strategy.initialize(100000)
        test_data = [{
            "type": "primary_candle",
            "market": "BTC",
            "date_time": "2023-01-01T00:00:00",
            "closing_price": 1000000
        }]
        self.strategy.update_trading_info(test_data)
        self.assertEqual(len(self.strategy.data), 1)
```

### 5. 고급 전략 개발 팁

#### 기술적 지표 활용
```python
import pandas as pd
import numpy as np

def calculate_sma(prices, period):
    """단순 이동평균 계산"""
    return pd.Series(prices).rolling(period).mean().values[-1]

def calculate_rsi(prices, period=14):
    """RSI 지표 계산"""
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).values[-1]
```

#### 리스크 관리
```python
def calculate_position_size(self, price, risk_percent=0.02):
    """리스크 기반 포지션 크기 계산"""
    risk_amount = self.balance * risk_percent
    position_size = risk_amount / price
    return min(position_size, self.balance / price)
```

#### 백테스팅 최적화
- **과최적화 방지**: 여러 기간에 걸친 테스트
- **트랜잭션 비용 고려**: 수수료 및 슬리피지 반영
- **시장 상황별 성능**: 상승장/하락장/횡보장에서의 성능 분석

---

## 프로젝트의 장점

### 1. 기술적 장점

#### 모듈화된 아키텍처
- **계층화된 설계**: Controller → Operator → Core Layer로 명확한 책임 분리
- **느슨한 결합**: 각 모듈이 독립적으로 개발/테스트/배포 가능
- **높은 확장성**: 새로운 거래소, 전략, 분석 도구를 쉽게 추가
- **재사용성**: 공통 인터페이스를 통한 컴포넌트 재사용

#### 견고한 설계 패턴
- **Factory Pattern**: StrategyFactory를 통한 전략 생성 관리
- **Observer Pattern**: 콜백 함수를 통한 이벤트 처리
- **Template Method**: 추상 클래스를 통한 일관된 인터페이스
- **Strategy Pattern**: 다양한 매매 전략의 플러그인 방식 지원

#### 실시간 처리 능력
- **멀티스레딩**: Worker 클래스를 통한 비동기 처리
- **타이머 기반 실행**: 정확한 간격으로 거래 프로세스 실행
- **상태 관리**: 명확한 상태 전환 (ready → running → terminating)

### 2. 사용자 경험 장점

#### 다양한 인터페이스 지원
- **CLI 인터페이스**: 개발자 친화적인 명령어 기반 제어
- **텔레그램 봇**: 모바일에서 원격 거래 제어
- **Jupyter Notebook**: 대화형 분석 및 실험
- **웹 인터페이스**: 사용자 친화적인 GUI (향후 확장 가능)

#### 포괄적인 분석 도구
- **실시간 모니터링**: 현재 수익률 및 거래 현황 실시간 확인
- **시각화**: 캔들차트 + 매매 포인트 그래프 생성
- **리포트 생성**: 상세한 거래 내역 및 성과 분석
- **백테스팅**: 과거 데이터를 이용한 전략 검증

#### 유연한 실행 환경
- **시뮬레이션 모드**: 실제 자금 없이 전략 테스트
- **데모 모드**: 가상 자금으로 실전 환경 시뮬레이션
- **실전 모드**: 실제 거래소와 연동한 라이브 트레이딩
- **대량 시뮬레이션**: 여러 전략을 동시에 테스트

### 3. 개발자 친화적 특징

#### 풍부한 테스트 환경
- **단위 테스트**: 각 모듈별 독립적인 테스트
- **통합 테스트**: 실제 거래소와의 연동 테스트
- **노트북 테스트**: 대화형 모듈 테스트 및 디버깅
- **CI/CD**: GitHub Actions를 통한 자동화된 테스트

#### 상세한 문서화
- **API 문서**: 각 클래스와 메서드의 상세한 docstring
- **사용 예제**: 다양한 실행 모드별 사용법
- **아키텍처 다이어그램**: PlantUML을 이용한 시각적 설명
- **개발 가이드**: 새로운 전략 개발 방법론

#### 오픈소스 생태계
- **MIT 라이선스**: 자유로운 사용 및 수정 가능
- **활발한 커뮤니티**: GitHub Issues를 통한 지원
- **지속적인 업데이트**: 정기적인 기능 개선 및 버그 수정

---

## 결론

SMTM은 잘 구조화된 암호화폐 자동매매 시스템으로, 계층화된 아키텍처를 통해 확장성과 유지보수성을 확보했습니다. 

**주요 장점**:
- **모듈화된 설계**: 각 컴포넌트가 독립적으로 개발/테스트 가능
- **다양한 실행 모드**: 시뮬레이션부터 실전거래까지 지원
- **확장 가능한 전략 시스템**: 새로운 전략을 쉽게 추가 가능
- **포괄적인 분석 도구**: 실시간 성과 분석 및 리포트 생성
- **사용자 친화적 인터페이스**: CLI, 텔레그램, Jupyter 등 다양한 접근 방식
- **강력한 백테스팅**: 과거 데이터를 이용한 전략 검증
- **오픈소스 생태계**: 활발한 커뮤니티와 지속적인 개발

**다양한 활용 분야**:
- **개인 투자**: 초보자부터 전문가까지 다양한 수준의 투자자 지원
- **교육 연구**: 대학 강의 및 연구 프로젝트에 활용
- **기관 투자**: 헤지펀드, 자산운용사의 포트폴리오 관리
- **개발 플랫폼**: 새로운 전략 및 거래소 연동 개발

**개발 시 주의사항**:
- **실전 거래 전 충분한 시뮬레이션 테스트 필수**
- **API 키 보안 관리**
- **리스크 관리 및 포지션 크기 조절**
- **시장 상황 변화에 대한 대응 방안**

이 문서를 참고하여 SMTM 시스템을 효과적으로 활용하고 새로운 전략을 개발하시기 바랍니다. 개인의 투자 목적과 경험 수준에 맞는 활용 방안을 선택하여 안전하고 효과적인 암호화폐 투자를 진행하시기 바랍니다.
