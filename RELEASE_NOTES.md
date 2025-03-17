## v1.6.2
- Fix `setup.py`, `setup.cfg`

---

## v1.6.1
- Fix README image link

---

## v1.6.0

### Telegram Controller multilingual support (English)
- https://github.com/msaltnet/smtm/commit/bd6decb7d9a14f22e8c0d429b16be07a5fa30b85

## v1.6.0 (한국어)

### TelegramController 다국어 지원(영어)
- https://github.com/msaltnet/smtm/commit/bd6decb7d9a14f22e8c0d429b16be07a5fa30b85

---

## v1.5.0

### Add the alert_callback interface
Added `alert_callback` which can be used to send notifications from the core module to the controller. It can be used to make no transaction, send only a notification, or to notify the Analyzer about errors in data processing. Added `StrategySas` strategy as an example.
- https://github.com/msaltnet/smtm/commit/7dcd9e1843b15cd281dfe7af4b35fa4ca1352514
- https://github.com/msaltnet/smtm/commit/3cd4328d8af1aa5749af6be646dec57b68c2db3b
- https://github.com/msaltnet/smtm/commit/5263cdb6e0ca707977a9a966d2bb25321debab60
- https://github.com/msaltnet/smtm/commit/231a58868d0bbd5c18f62171e231b8e1e19a5964
- https://github.com/msaltnet/smtm/commit/95485d5d5d068644cf4de0da3aadf094056b6b2c

### Added StrategyHey
A new strategy, **StrategyHey**, has been added, which analyzes trading data and sends alerts only. It inherits from `StrategySas` and implements an alert system through `alert_callback` when a moving average breakdown occurs or a volatility breakout event is detected. This strategy is particularly useful for short-term trading in ranging markets.
- https://github.com/msaltnet/smtm/commit/a420001d626d1a628c723eda01e676e95e1fbeda
- https://github.com/msaltnet/smtm/commit/b1a2bbc48af339cd5eafde88df481a1faaa20161

### Other Refactoring
- **Implemented `pytest`**: Unit and integration tests have been consolidated into the `tests` directory. The transition to `pytest` has also improved the clarity of test results, as shown below.
  - https://github.com/msaltnet/smtm/commit/087e910fb78f9f6328779ad89594633e34514cd4

![image](https://github.com/msaltnet/smtm/assets/9311990/4b3d2e5a-991a-4525-839a-1a2bf828d531)

- **Code Cleanup**: Removed warning messages by refining the code.
  - https://github.com/msaltnet/smtm/commit/02fb5c08fa829be67f1866cb4367d367cbebf5b6
  - https://github.com/msaltnet/smtm/commit/601b275bcba0b19b959672d6dc9e1d4d8c6410e6
  - https://github.com/msaltnet/smtm/commit/5c15e2a12cce0ff75faa97eafb17ccd81016f92d

## v1.5.0 (한국어)

### alert_callback 인터페이스 추가
코어 모듈에서 컨트롤러에 알림을 보내는 용도로 사용될 수 있는 `alert_callback`이 추가되었습니다. 거래를 하지 않고, 알림만 보내거나, Analyzer에서 데이터 처리시 오류에 대해서 알림을 보내는 등의 용도로 사용할 수 있습니다. 예제로는 `StrategySas` 전략이 추가 되었습니다.
- https://github.com/msaltnet/smtm/commit/7dcd9e1843b15cd281dfe7af4b35fa4ca1352514
- https://github.com/msaltnet/smtm/commit/3cd4328d8af1aa5749af6be646dec57b68c2db3b
- https://github.com/msaltnet/smtm/commit/5263cdb6e0ca707977a9a966d2bb25321debab60
- https://github.com/msaltnet/smtm/commit/231a58868d0bbd5c18f62171e231b8e1e19a5964
- https://github.com/msaltnet/smtm/commit/95485d5d5d068644cf4de0da3aadf094056b6b2c

### StrategyHey 전략 추가
거래 정보를 분석해서 알림만 보내는 전략으로 StrategyHey 전략이 추가되었습니다. `StrategySas` 전략을 상속 받아서 이동 평균선이 깨질 때 또는 변동성 돌파 이벤트가 발생하였을 때, `alert_callback`을 통해 알림을 전달하는 앱을 구현하였습니다. 횡보장에서 단기 트레이딩시에 유용하게 사용할 수 있습니다.
- https://github.com/msaltnet/smtm/commit/a420001d626d1a628c723eda01e676e95e1fbeda
- https://github.com/msaltnet/smtm/commit/b1a2bbc48af339cd5eafde88df481a1faaa20161

### 그 외 리팩터링
- `pytest`를 적용하고, 단위테스트와 통합테스트를 `tests`로 모았습니다. `pytest`를 사용하게 되면서 테스트 결과 화면도 아래와 같이 깔끔하게 변경되었습니다.
  - https://github.com/msaltnet/smtm/commit/087e910fb78f9f6328779ad89594633e34514cd4

![image](https://github.com/msaltnet/smtm/assets/9311990/4b3d2e5a-991a-4525-839a-1a2bf828d531)

- 코드를 정리하여 경고 문구를 제거하였습니다.
  - https://github.com/msaltnet/smtm/commit/02fb5c08fa829be67f1866cb4367d367cbebf5b6
  - https://github.com/msaltnet/smtm/commit/601b275bcba0b19b959672d6dc9e1d4d8c6410e6
  - https://github.com/msaltnet/smtm/commit/5c15e2a12cce0ff75faa97eafb17ccd81016f92d

---

## v1.4.0

### Analyzer 기능 추가

Analyzer를 통해서 선 그래프를 그릴 수 있는 `add_line_callback`를 추가되었습니다. Strategy에서 `add_line_callback` 콜백을 사용해서 선 그래프를 추가할 수 있으며, StrategySmaDualMl 전략에서 활용되고 있는 예제를 확인할 수 있습니다.
- https://github.com/msaltnet/smtm/commit/d67614f12cdfdebd312c1a55a7169a0721e16be6
- https://github.com/msaltnet/smtm/commit/1a4efb2b87e306e4e873247ca1f1bfcba1ed48f5

### Binance Data Provider 추가와 Data Provider Interface 변경

Binance Data Provider가 추가되었습니다. 이제 Binance 캔들 정보를 사용해서 시뮬레이션을 할 수 있습니다. Config 모듈의 simulation_source 정보를 변경해서 시뮬레이션에 사용할 데이터를 선택 할 수 있습니다.

```
class Config:
    """시스템 전역 설정 모듈"""

    # 시뮬레이션에 사용할 거래소 데이터 simulation_source: upbit, binance
    simulation_source = "upbit"
```

Binance 캔들 정보와 Upbite 캔들 정보를 동시에 사용할 수 있도록 Data Provider의 반환 데이터 형식이 변경되었습니다. Data Provider는 복수개의 data를 하나의 리스트로 한 번에 전달할 수 있게 되었으며, 각각의 데이터는 추가된 type 항목을 통해서 구분할 수 있습니다. 변경된 Data Provider의 Data 형식은 다음과 같으며, Binance와 Upbit 데이터를 모두 제공하는 UpbitBinanceDataProvider가 추가되었습니다.

```
  [
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "market": 거래 시장 종류 BTC
          "date_time": 정보의 기준 시간
          "opening_price": 시작 거래 가격
          "high_price": 최고 거래 가격
          "low_price": 최저 거래 가격
          "closing_price": 마지막 거래 가격
          "acc_price": 단위 시간내 누적 거래 금액
          "acc_volume": 단위 시간내 누적 거래 양
      },
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "usd_krw": 환율
          "date_time": 정보의 기준 시간
      },
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "market": 거래 시장 종류 BTC
          "date_time": 정보의 기준 시간
          "opening_price": 시작 거래 가격
          "high_price": 최고 거래 가격
          "low_price": 최저 거래 가격
          "closing_price": 마지막 거래 가격
          "acc_price": 단위 시간내 누적 거래 금액
          "acc_volume": 단위 시간내 누적 거래 양
      }
  ]
```

Binance와 Upbit 두 거래소의 정보를 동시에 사용해서 시뮬레이션을 할 수 있는 SimulationDualDataProvider도 추가되었으며, Config에서 사용 여부를 선택 할 수 있습니다.

```
class Config:
    """시스템 전역 설정 모듈"""

    # SimulationDualDataProvider의 데이터를 사용할지 여부: normal, dual
    simulation_data_provider_type = "normal"
```

Upbit, Binance 두 거래소의 캔들 정보를 동시에 사용하는 예제 전략 StrategySmaDualMl이 추가되었습니다. SML 전략과 동일한 로직을 가지고 있으며 Binance 데이터로 add_line_callback를 사용해서 선 그래프를 추가하도록 하였습니다. 아래 붉은 색 선이 Binance 데이터의 closing price입니다.

![68e7d3d8-9cce-4eb1-ae5c-166d591e1641](https://github.com/msaltnet/smtm/assets/9311990/ea339501-d679-449d-b582-1e29244e01c2)

- https://github.com/msaltnet/smtm/commit/e8f490e5b8d61ad2b3520f00e296498d6004488c
- https://github.com/msaltnet/smtm/commit/34ca568b6112e0b0d60f8e19afb9425c45d9e537
- https://github.com/msaltnet/smtm/commit/d46064c08344685aaf89042d321c8687b914e93a
- https://github.com/msaltnet/smtm/commit/77c482bf5658e31ce802b0fb82f0ffbbdabeb110
- https://github.com/msaltnet/smtm/commit/ac7f3421603b4dc4b7b19c0b9efa5b03be846e25
- https://github.com/msaltnet/smtm/commit/69d9c63f4a135f0357b441a27f4bc9d0d55e585d
- https://github.com/msaltnet/smtm/commit/b8f1f938be58e23d3a003cbd57c1f1985bc82120
- https://github.com/msaltnet/smtm/commit/1cb1adbd19b69ed2e8ab1b0be6678e6d1d57151b
- https://github.com/msaltnet/smtm/commit/3a038d740b82f370a46cd84b0bf7a1167b48402b

DataProviderFactory를 추가하여 Telegram Controller에서 Data Provider를 동적으로 선택할 수 있도록 하였습니다. 기존에는 Trader와 Data Provider가 일치하였지만 Binance 데이터나 다른 데이터를 복합적으로 사용하는 Data Provider를 추가해서 전략을 운영할 수 있게 되었습니다. 환율정보, 주가정보, 암호화폐 지수를 사용한 다양한 전략을 만들어서 운영이 가능합니다.

![image](https://github.com/msaltnet/smtm/assets/9311990/3a9a4da7-d285-498b-8329-63264d8b843f)

### 그 외 수정 사항

모듈이 많아짐에 따라 관리를 위해서 controller, data, strategy, trader 폴더로 구분하였습니다.
- https://github.com/msaltnet/smtm/commit/b58e100380ca6e28163944bf6ef5cb1688c4ebea

0.0024와 같은 값을 소숫점 4자리 수로 변경할 때 발생하는 부동 소수점 문제를 수정하였습니다.
- https://github.com/msaltnet/smtm/commit/2fff47b1e5caf1bee36388194e031c190585e786 


---

## v1.3.0 (English)
Improve architecture to change candel interval for both simulation and real-trading
  - Make `Config` module for global interval setting
    - 5542498c66804aa2f6dba3fa0e6a9002c628b79f
    - 7de1ae1452346910819f2a96d4801832f62cea0a
    - 40657f816366dd1b98fa3eaa975a813f41c97b40
    - c3728b4a2b2e53dbfe0659563333d9bb6837e173
    - c64c2215e073283baadbfad7e529c2da5137e9fd
    - 6ffcee97f6d3fa13604d037e1da9b4eb9d660ad6
    - 031fcdf789f4f4e0a43ec0ff7173772a1476df33

## v1.3.0 (한국어)
Candle Interval을 변경해서 시뮬레이션, 거래 진행 할 수 있도록 구조 개선
  - `Config` 모듈을 만들어서 전역적으로 interval 설정 가능하도록 변경
    - 5542498c66804aa2f6dba3fa0e6a9002c628b79f
    - 7de1ae1452346910819f2a96d4801832f62cea0a
    - 40657f816366dd1b98fa3eaa975a813f41c97b40
    - c3728b4a2b2e53dbfe0659563333d9bb6837e173
    - c64c2215e073283baadbfad7e529c2da5137e9fd
    - 6ffcee97f6d3fa13604d037e1da9b4eb9d660ad6
    - 031fcdf789f4f4e0a43ec0ff7173772a1476df33

---

## v1.2.0 (English)
Enhance simulation performance (about 3x more speedup)
  - when interval is under 1sec, call handler directly instead of using `threading.Timer`
    - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
Change CI Travis -> github action
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
Use strategy code instead of names
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

### New Features
- add StrategySmaMl
  - aad85ce841b90505017d94a6034f7f3b5b12965f

### Fixed Bugs
- fix a bug for telegram controller strategy selector
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

## v1.2.0
Simulation 속도 개선 (약 3배이상 향상)
  - interval이 1초 미만일 때, `threading.Timer`를 사용하지 않고 바로 핸들러 호출하도록 수정
    - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
CI를 Travis -> github action으로 변경
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
전략 이름 대신 코드를 사용
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

### 기능 추가
- 이동 평균선을 이용한 기본 전략에 간단한 ML을 추가한 StrategySmaMl 전략 추가
  - aad85ce841b90505017d94a6034f7f3b5b12965f

### 버그 수정
- 텔레그램 컨트롤러에서 전략 선택 문자 비교 버그 수정
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

---

## v1.1.1 (English)
Add StrategyFactory and remove integration_tests from package

### New Features
- Add StrategyFactory to add/remove a strategy easily.
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- Add log directory to write log files
  - e74e91095425228038344ced0484416b00ea787a

### Fixed Bugs
- Remove integration_tests package in the top_level of packages.
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

## v1.1.1
StrategyFactory 추가 및 integration_tests를 패키지에서 제거

### 기능 추가
- 전략을 쉽게 추가/제거 할 수 있도록 StrategyFactory 추가. 전략을 추가할 때 StrategyFactory에만 추가해주면 됨
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- 로그 파일을 log 폴더에 저장
  - e74e91095425228038344ced0484416b00ea787a

### 버그 수정
- integration_tests가 별도의 패키지로 top_level에 추가되고 있는 문제 수정. smtm 패키지 설치시 smtm과 integration_tests 두 개의 패키지가 따로 설치되는 문제
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

---

## v1.1.0 (English)
Demo feature and RSI strategy

### New Features
- Analyzer `add_drawing_spot` can add green spots to graph
  - bff9cefc51fb9b0df7710e16b16d5889aeffe8b7
  - 254e1165358a6d2055bbddea9133f135651ded41
  - a98cb0075fa1a08554d94e1dc797846645f912d3
  - 5893198250611ec60c50a5218d95b7e11a92e6da
- Add DOGE, XRP for Upbit
  - 6f68ea3975f12e42bfb579740c376d52f5504499
- Can save periodic graph for Simulation, MassSimulation 
  - 692cc7323b502d2ab69aeb3be43a648208d7f89b
  - e448005c07623b158de642a94483286644f511da
- Add RSI index to Analyzer graph
  - a12b565fc047de6e145861995d79c7c70139b628
- Add RSI Strategy
  - 59ef24c2e15a76cc24a952e7d8bebba7031aa020
- Telegram controller demo mode with DemoTrader
  - 698b7240e9a62492d8f87815a96477e4372602b4

### Fixed Bugs
- Send warning message via telegram when Worker catch exception from runnable
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

## v1.1.0
Demo 모드와 RSI 전략 추가

### 기능 추가
- Analyzer `add_drawing_spot` 그래프에 점 추가 가능
  - bff9cefc51fb9b0df7710e16b16d5889aeffe8b7
  - 254e1165358a6d2055bbddea9133f135651ded41
  - a98cb0075fa1a08554d94e1dc797846645f912d3
  - 5893198250611ec60c50a5218d95b7e11a92e6da
- Upbit에 DOGE, XRP 화폐 추가
  - 6f68ea3975f12e42bfb579740c376d52f5504499
- Simulation, MassSimulation 주기적으로 그래프 저장
  - 692cc7323b502d2ab69aeb3be43a648208d7f89b
  - e448005c07623b158de642a94483286644f511da
- RSI index 추가
  - a12b565fc047de6e145861995d79c7c70139b628
- RSI 전략 추가
  - 59ef24c2e15a76cc24a952e7d8bebba7031aa020
- Telegram controller Demo 모드 추가
  - 698b7240e9a62492d8f87815a96477e4372602b4

### 버그 수정
- Worker runnable에 문제 발생시 종료 후 텔레그램 메세지 전송
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

---

## v1.0.0 (English)
First release with main features

### Main Features
1. Simulation
2. Mass-Simulation
3. Real Trading
4. Telegram Chatbot Controller
5. Jupyter Notebook Controller

## v1.0.0
주요 기능을 포함한 첫번째 릴리즈

### 주요 기능
1. 시뮬레이션
2. 대량시뮬레이션
3. 실전 거래
4. 텔레그램봇 모드
5. 주피터 노트북 컨트롤러

