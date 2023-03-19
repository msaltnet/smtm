####
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

### v1.1.0
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

### v1.0.0
First release with main features

#### Main Features
1. Simulation
2. Mass-Simulation
3. Real Trading
4. Telegram Chatbot Controller
5. Jupyter Notebook Controller
