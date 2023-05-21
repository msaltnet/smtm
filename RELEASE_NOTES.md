####

---

### v1.2.0
Simulation 속도 개선 (약 3배이상 향상)
  - interval이 1초 미만일 때, `threading.Timer`를 사용하지 않고 바로 핸들러 호출하도록 수정
  - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
CI를 Travis -> github action으로 변경
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
전략 이름 대신 코드를 사용
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

#### 기능 추가
- 이동 평균선을 이용한 기본 전략에 간단한 ML을 추가한 StrategySmaMl 전략 추가
  - aad85ce841b90505017d94a6034f7f3b5b12965f

#### 버그 수정
- 텔레그램 컨트롤러에서 전략 선택 문자 비교 버그 수정
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

### v1.2.0 (English)
Enhance simulation performance (about 3x more speedup)
  - when interval is under 1sec, call handler directly instead of using `threading.Timer`
  - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
Change CI Travis -> github action
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
Use strategy code instead of names
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

#### New Features
- add StrategySmaMl
  - aad85ce841b90505017d94a6034f7f3b5b12965f

#### Fixed Bugs
- fix a bug for telegram controller strategy selector
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

---

### v1.1.1
StrategyFactory 추가 및 integration_tests를 패키지에서 제거

#### 기능 추가
- 전략을 쉽게 추가/제거 할 수 있도록 StrategyFactory 추가. 전략을 추가할 때 StrategyFactory에만 추가해주면 됨
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- 로그 파일을 log 폴더에 저장
  - e74e91095425228038344ced0484416b00ea787a

#### 버그 수정
- integration_tests가 별도의 패키지로 top_level에 추가되고 있는 문제 수정. smtm 패키지 설치시 smtm과 integration_tests 두 개의 패키지가 따로 설치되는 문제
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

### v1.1.1 (English)
Add StrategyFactory and remove integration_tests from package

#### New Features
- Add StrategyFactory to add/remove a strategy easily.
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- Add log directory to write log files
  - e74e91095425228038344ced0484416b00ea787a

#### Fixed Bugs
- Remove integration_tests package in the top_level of packages.
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

---

### v1.1.0
Demo 모드와 RSI 전략 추가

#### 기능 추가
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

#### 버그 수정
- Worker runnable에 문제 발생시 종료 후 텔레그램 메세지 전송
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

### v1.1.0 (English)
Demo feature and RSI strategy

#### New Features
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

#### Fixed Bugs
- Send warning message via telegram when Worker catch exception from runnable
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

---

### v1.0.0
주요 기능을 포함한 첫번째 릴리즈

#### 주요 기능
1. 시뮬레이션
2. 대량시뮬레이션
3. 실전 거래
4. 텔레그램봇 모드
5. 주피터 노트북 컨트롤러

### v1.0.0 (English)
First release with main features

#### Main Features
1. Simulation
2. Mass-Simulation
3. Real Trading
4. Telegram Chatbot Controller
5. Jupyter Notebook Controller
