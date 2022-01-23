# smtm
[![Travis](https://travis-ci.com/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://app.travis-ci.com/github/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

파이썬 알고리즘기반 암호화폐 자동매매 프로그램. https://smtm.msalt.net

[English](https://github.com/msaltnet/smtm/blob/master/README-en_us.md) 👈

[![icon_wide](https://user-images.githubusercontent.com/9311990/150662620-9c2ef1d8-7384-4856-a8fa-f1e52031d6fa.jpg)](https://smtm.msalt.net/)


데이터 수집 -> 알고리즘 분석 -> 거래로 이루어진 간단한 프로세스를 정해진 간격으로 반복 수행하는 것이 기본 개념이며, 기본적으로 분당 1회 프로세스를 처리하는 것으로 검증되었습니다.

1. Data Provider 모듈이 데이터 취합  
2. Strategy 모듈을 통한 알고리즈 매매 판단  
3. Trader 모듈을 통한 거래 처리  
 --- 반복 ---
4. Create analyzing result by Analyzer

❗ 초 단위의 짧은 시간에 많은 거래를 처리해야하는 고성능 트레이딩 머신으로는 적합하지 않으며, 처리 시간이 중요한 성능이 요구되는 경우 충분한 검토가 필요합니다.

![intro](https://user-images.githubusercontent.com/9311990/140635409-93e4b678-5a6b-40b8-8e28-5c8f819aa88c.jpg)

## Architecture
계층화된 아키텍쳐 Layered architecture

| Layer | Role |
|:---:|:---:|
| Controller | User Interface |
| Operator | Operating Manager |
| Analyzer, Trader, Strategy, Data Provider | Core Feature |

### 텔레그램 챗봇 모드
텔레그램 챗봇 모드를 사용하면 자동매매 프로그램을 텔레그램 메신저를 사용해서 컨트롤 할 수 있습니다.

텔레그램 챗봇 모드를 위해서는 챗봇을 만들고 API 토큰과 대화방 정보를 입력해서 구동해야 합니다.

Telegram Controller 모듈은 제공된 정보를 바탕으로 사용자와 텔레그램 메신저를 통해 입력을 받아 Operator를 컨트롤합니다.

![smtm_bot](https://user-images.githubusercontent.com/9311990/150667094-95139bfb-03e0-41d5-bad9-6be05ec6c9df.png)

![telegram_chatbot](https://user-images.githubusercontent.com/9311990/150663864-c5a7ed27-f1c6-4b87-8220-e31b8ccce368.PNG)

### 시뮬레이션 모드
시뮬레이션 모드을 통해 과거 거래 데이터를 바탕으로 시뮬레이션을 수행해서 결과를 확인할 수도 있습니다. 간단한 시뮬레이션부터 대량시뮬레이션까지 가능합니다.

![simulator](https://user-images.githubusercontent.com/9311990/140635388-5ced5e05-23ad-44df-a14f-8492f489cfd9.jpg)

## 사용방법
일반적인 파이썬 패키지와 같이 설치하고 실행하면 됩니다.

### 설치방법
소스 코드를 다운로드하고 관련된 패키지를 설치하세요.

```
pip install -r requirements.txt
```

시스템 수정 및 개발을 원할 때는 -e 옵션으로 개발관련 패키지도 설치하세요.

```
pip install -r requirements-dev.txt
```

### 실행방법
시뮬레이션, 대량 시뮬레이션, 챗봇 모드를 포함하여 아래 6개의 기능을 제공합니다.

- 0: 인터렉티브 모드로 시뮬레이터
- 1: 입려받은 설정값으로 싱글 시뮬레이션
- 2: 기본 실전 매매 프로그램
- 3: 텔레그램 챗봇 모드로 실전 매매 프로그램
- 4: 컨피그 파일을 사용한 대량 시뮬레이션
- 5: 대량 시뮬레이션을 위한 컨피그 파일 생성

#### 인터렉티브 모드 시뮬레이터
아래 명령어로 인터렉티브 모드 시뮬레이터 실행.

```
python -m smtm --mode 0
```

#### 싱글 시뮬레이션
시뮬레이션 파라미터와 아래 명령어로 단일 시뮬레이션을 바로 실행 후 결과 반환.

```
python -m smtm --mode 1 --budget 50000 --from_dash_to 201220.170000-201221 --term 0.1 --strategy 0 --currency BTC
```

#### 기본 실전 매매 프로그램
초기값과 함께 기본 실전 매매 프로그램을 실행. 기본 실전 매매 프로그램은 인터렉티브 모드로 실행되어 입력에 따라 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 2 --budget 50000 --term 60 --strategy 0 --currency ETH
```

#### 텔레그램 챗봇 모드 실전 매매 프로그램
아래 명령어로 텔레그램 챗봇 모드 실전 매매 프로그램을 실행. 텔레그램 챗봇 모드 실전 매매 프로그램은 입력받은 텔레그램 챗봇 API 토큰과 대화방 정보를 사용하여 텔레그램 챗봇 메세지를 통해서 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 3
```

#### 대량 시뮬레이션
대량 시뮬레이션 설정 파일과 함께 실행. 설정 파일을 json 형식이며 텍스트 편집기를 통해서 직접 생성해도 되고, 명령어를 통해 생성도 가능합니다.

```
python -m smtm --mode 4 --config /data/sma0_simulation.json
```

#### 대량 시뮬레이션 설정 파일 생성
파라미터와 함께 아래 명령어로 대량 시뮬레이션에 사용될 설정 파일을 생성할 수 있습니다.

```
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy 1 --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```

### 테스트 방법
#### 단위 테스트
unittest를 사용해서 프로젝트의 단위 테스트를 실행.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

#### 통합 테스트
통합 테스트는 실제 거래소를 사용해서 테스트가 진행됩니다. 몇몇 테스트는 주피터 노트북을 사용해서 테스트가 가능하도록 하였습니다. `notebook` 폴더를 확인해 보세요.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```

#### 개발팁
커밋을 생성하기 전에 아래 명령어를 사용하여 Jupyter notebook의 출력을 삭제하세요.

```
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```
