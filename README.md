# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

파이썬 알고리즘기반 암호화폐 자동매매 프로그램. https://smtm.msalt.net

[교보문고 - 암호화폐 자동매매 시스템 만들기 with 파이썬](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967)

[예스24 - 암호화폐 자동매매 시스템 만들기 with 파이썬](http://www.yes24.com/Product/Goods/107635612)

[알라딘 - 암호화폐 자동매매 시스템 만들기 with 파이썬](https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=289526248)

[English](https://github.com/msaltnet/smtm/blob/master/README-en_us.md) 👈

[![icon_wide_gold](https://user-images.githubusercontent.com/9311990/161744914-05e3d116-0e9b-447f-a015-136e0b9ec22b.png)](https://smtm.msalt.net/)


데이터 수집 -> 알고리즘 분석 -> 거래로 이루어진 간단한 프로세스를 정해진 간격으로 반복 수행하는 것이 기본 개념이며, 기본적으로 분당 1회 프로세스를 처리하는 것으로 검증되었습니다.

1. Data Provider 모듈이 데이터 취합  
2. Strategy 모듈을 통한 알고리즘 매매 판단  
3. Trader 모듈을 통한 거래 처리  
 --- 반복 ---
4. Analyzer 모듈을 통한 분석

❗ 초 단위의 짧은 시간에 많은 거래를 처리해야하는 고성능 트레이딩 머신으로는 적합하지 않으며, 처리 시간이 중요한 성능이 요구되는 경우 충분한 검토가 필요합니다.

![intro](https://user-images.githubusercontent.com/9311990/140635409-93e4b678-5a6b-40b8-8e28-5c8f819aa88c.jpg)

## 주요기능
- 파라미터를 설정 가능한 시뮬레이션
- 멀티프로세스 대량시뮬레이션
- CLI 모드 자동 거래 프로그램
- JupyterNotebook을 활용한 원격컨트롤
- 텔레그램으로 컨트롤 하는 자동거래 프로그램

### 텔레그램 챗봇 모드
텔레그램 챗봇 모드를 사용하면 자동매매 프로그램을 텔레그램 메신저를 사용해서 컨트롤 할 수 있습니다.

텔레그램 챗봇 모드를 위해서는 챗봇을 만들고 API 토큰과 대화방 정보를 입력해서 구동해야 합니다.

![smtm_bot](https://user-images.githubusercontent.com/9311990/150667094-95139bfb-03e0-41d5-bad9-6be05ec6c9df.png)

![telegram_chatbot](https://user-images.githubusercontent.com/9311990/150663864-c5a7ed27-f1c6-4b87-8220-e31b8ccce368.PNG)

### 시뮬레이션 모드
시뮬레이션 모드을 통해 과거 거래 데이터를 바탕으로 시뮬레이션을 수행해서 결과를 확인할 수도 있습니다. 간단한 시뮬레이션부터 대량시뮬레이션까지 가능합니다.

## 설치방법
소스 코드를 다운로드하고 관련된 패키지를 설치하세요.

```
pip install -r requirements.txt
```

시스템 수정 및 개발을 원할 때는 -e 옵션으로 개발관련 패키지도 설치하세요.

```
pip install -r requirements-dev.txt
```

## 사용방법
시뮬레이션, 대량 시뮬레이션, 챗봇 모드를 포함하여 아래 6개의 기능을 제공합니다.

- 0: 인터렉티브 모드 시뮬레이터
- 1: 입력받은 설정값으로 싱글 시뮬레이션 실행
- 2: 인터렉티브 모드 기본 실전 매매 프로그램
- 3: 텔레그램 챗봇 모드로 실전 매매 프로그램
- 4: 컨피그 파일을 사용한 대량 시뮬레이션 실행
- 5: 대량 시뮬레이션을 위한 컨피그 파일 생성

### 인터렉티브 모드 시뮬레이터
아래 명령어로 인터렉티브 모드 시뮬레이터 실행.

```
python -m smtm --mode 0
```

### 싱글 시뮬레이션
시뮬레이션 파라미터와 함께 아래 명령어로 단일 시뮬레이션을 실행하면 결과를 반환합니다.

```
python -m smtm --mode 1 --budget 500000 --from_dash_to 201220.080000-201221 --term 0.001 --strategy 1 --currency BTC
```

### 기본 실전 매매 프로그램
아래 명령어로 초기값과 함께 기본 실전 매매 프로그램을 실행합니다. 기본 실전 매매 프로그램은 인터렉티브 모드로 실행되어 입력에 따라 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 2 --budget 100000 --term 60 --strategy 0 --currency ETH
```

실전 거래를 위해서는 `.env` 파일에 거래소 API KEY와 API host url을 넣어 주어야 합니다.

```
UPBIT_OPEN_API_ACCESS_KEY=Your API KEY
UPBIT_OPEN_API_SECRET_KEY=Your API KEY
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com
```

### 텔레그램 챗봇 모드 실전 매매 프로그램
아래 명령어로 텔레그램 챗봇 모드 실전 매매 프로그램을 실행합니다. 텔레그램 챗봇 모드 실전 매매 프로그램은 입력받은 텔레그램 챗봇 API 토큰과 대화방 정보를 사용하여 텔레그램 챗봇 메세지를 통해서 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 3
```

챗봇 모드를 위해서는 `.env` 파일에 텔레그램 챗봇 API 토큰과 챗봇 대화방 아이디를 넣어 주어야 합니다.

```
TELEGRAM_BOT_TOKEN=bot123456789:YOUR bot Token
TELEGRAM_CHAT_ID=123456789
```

### 대량 시뮬레이션
대량 시뮬레이션 설정 파일과 함께 실행합니다. 설정 파일을 json 형식이며 텍스트 편집기를 통해서 직접 생성해도 되고, 명령어를 통해 생성도 가능합니다.

```
python -m smtm --mode 4 --config /data/sma0_simulation.json
```

### 대량 시뮬레이션 설정 파일 생성
파라미터와 함께 아래 명령어로 대량 시뮬레이션에 사용될 설정 파일을 생성할 수 있습니다.

```
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy 1 --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```

## 소프트웨어 설계구조
계층화된 아키텍쳐 Layered architecture

| Layer | Module | Role |
|:---:|:---:|:---:|
| Controller Layer | Simulator, Controller, TelegramController| User Interface |
| Operator Layer | Operator, SimulationOperator |Operating Manager |
| Core Layer |Analyzer, Trader, Strategy, Data Provider | Core Feature |

### Component Diagram

![Component Diagram](https://user-images.githubusercontent.com/9311990/221420624-9807ca39-31c7-4bb6-b3de-3a4114f22430.png)

### Class Diagram

![Class Diagram](https://user-images.githubusercontent.com/9311990/221420583-6b335aec-1547-47b3-8b64-6a6313127890.png)

### Sequence Diagram

![Sequence Diagram](https://user-images.githubusercontent.com/9311990/221420634-7ede859b-6b80-4b9d-9af2-0b04a0bfd9d3.png)


## 테스트 방법
### 단위 테스트
unittest를 사용해서 프로젝트의 단위 테스트를 실행.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

### 통합 테스트
통합 테스트는 실제 거래소를 사용해서 테스트가 진행됩니다. 몇몇 테스트는 주피터 노트북을 사용해서 테스트가 가능하도록 하였습니다. `notebook` 폴더를 확인해 보세요.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```

### 개발팁
커밋을 생성하기 전에 아래 명령어를 사용하여 Jupyter notebook의 출력을 삭제하세요.

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

시뮬레이션이나 데모 모드를 사용하는 경우, SimulationDataProvider는 업비트의 정보를 사용하므로, 시스템 시간의 타임존이 한국으로 설정되어야 합니다. 특히, 클라우트 리눅스의 경우 아래 명령어로 설정 할 수 있습니다.

```bash
timedatectl set-timezone 'Asia/Seoul'
```

원격 터미널에서 프로그램 실행 후 연결을 종료하더라도 프로그램이 종료되지 않도록 하기 위해서 `nohup`을 사용하는 방법이 있습니다. 표준 출력과 에러를 별도의 파일에 저장하며 백그라운드로 실행하기 위해서는 다음과 같이 실행하면 됩니다.

```bash
nohup python -m smtm --mode 3 --demo 1 > nohup.out 2> nohup.err < /dev/null &
```

## Code Lab
- [시뮬레이션 Code Lab](https://smtm.msalt.net/codelab/smtm-simulation/)
- [모의 투자 Code Lab](https://smtm.msalt.net/codelab/smtm-demo/)

## 관련 도서

[![smtm-book](https://user-images.githubusercontent.com/9311990/157685437-dcedd2c0-9f0c-400c-a3d4-017354279b60.png)](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967)
