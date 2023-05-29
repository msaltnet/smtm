author: Jeong Seongmoon
summary: Install smtm and run a trading simulation
id: smtm-simulation
categories: codelab,smtm
environments: Web
status: Published
feedback link: https://github.com/msaltnet/smtm

# CodeLab to Install smtm and Run a trading simulation

## CodeLab Overview
Duration: 0:02:00

이 코드랩에서는 암호화폐 자동매매 시스템 오픈소스 프로젝트 smtm를 설치하고, 트레이딩 시뮬레이션을 실행하는 방법에 대해서 설명하고 있습니다.

### 사전 준비
1. python (3.6 이상 권장)
1. Upbit에 접속 가능한 인터넷 환경 (시뮬레이션 데이터 다운로드)

Upbit 계좌나 계정은 없어도 됩니다

### 배우게 될 것
1. pip를 사용해서 smtm을 설치하는 방법
1. 설치한 smtm을 사용하여 트레이딩 시뮬레이션 하는 방법
1. smtm 시뮬레이션 결과 확인

![시뮬레이션 결과 화면](./img/SIM-SMA-230112.190000-230113.070000.jpg)

## smtm 설치
Duration: 0:02:00

smtm은 암호화폐 자동매매 오픈소스 프로젝트로써 깃허브에 [소스코드](https://github.com/msaltnet/smtm)가 공개되어 있습니다. 또한 [pypi.org](https://pypi.org/project/smtm/)에 패키지가 등록되어 있습니다.

python이 설치된 환경에서 python 패키지 관리 프로그램 pip를 통해서 smtm 패키지를 설치합니다.

```
(venv) PS C:\smtm> pip install smtm
Collecting smtm
  Downloading smtm-1.2.0-py3-none-any.whl (80 kB)
     |████████████████████████████████| 80 kB 5.5 MB/s
Requirement already satisfied: pyjwt in c:\venv\lib\site-packages (from smtm) (2.0.1)
Requirement already satisfied: python-dotenv in c:\venv\lib\site-packages (from smtm) (0.19.0)
Requirement already satisfied: requests in c:\venv\lib\site-packages\requests-2.25.0-py3.6.egg (from smtm) (2.25.0)
...
Installing collected packages: smtm
Successfully installed smtm-1.2.0
(venv) PS C:\smtm> 
```

<aside class="positive">
효과적인 패키지 관리를 위해서 <a href="https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment">virtual environment</a>을 사용할 것을 권장합니다.
</aside>

pip를 사용하지 않고 소스코드와 패키지를 깃허브에서 다운로드하여 사용할 수도 있습니다.

[github smtm repo](https://github.com/msaltnet/smtm)에 접속해서 [설치방법](https://github.com/msaltnet/smtm#%EC%84%A4%EC%B9%98%EB%B0%A9%EB%B2%95)을 확인해 보세요.

## 트레이딩 시뮬레이션 실행
Duration: 0:03:00

smtm에서 트레이딩은 Data Provider, Strategy, Trader 모듈이 순차적으로 동작하면서 진행됩니다. 기본적으로 트레이딩은 1분 간격으로 반복 수행되며, 시뮬레이션에서는 분봉을 사용합니다.

![자동 거래 시퀀스 다이어그램](./img/smtm_sequence_kr.png)

smtm 시스템에서 제공하는 트레이딩 시뮬레이션은 Upbit의 거래 정보를 사용해서 진행됩니다. Upbit Open API를 사용하여 데이터를 다운로드하고, 전략 모듈에 따라서 트레이딩 시뮬레이션이 진행됩니다.

*Upbit Open API* 중 거래 데이터 조회는 특별한 권한이 필요없기 때문에 계좌 정보등의 별도 정보가 필요하지 않습니다.

시뮬레이션에 필요한 파라미터 값은 다음과 같습니다.
- budget: 예산 정보
- from_dash_to: 기간 정보 년월일.시분초 또는 년월일 예) 201220.170000-201221
- term: 반복시간으로 시뮬레이션에서는 0.1 권장
- strategy:  사용할 전략 코드 예) BNH, SMA, SML
- currency: 거래할 암호화폐 예) BTC

현재 기본 제공되는 전략은 다음과 같으며, 전략은 직접 구현/최적화하여 사용해야 합니다.
- BNH: Buy and Hold 단순 분할 매수
- SMA: Simple Moving Average 단순 이동 평균선 전략
- SML: SMA + ML 단순 이동 평균선 전략에 Machine Learning 도입

현재 지원하는 암호화폐는 KRW-BTC, KRW-ETH, KRW-DOGE, KRW-XRP이 있으며, 필요에 따라 직접 추가가능합니다. [코인 추가하는 방법 영상](https://youtu.be/UikVC3b-j2M)을 보시면 간단하게 가능할 수 있습니다.

```
python -m smtm --mode 1 --budget 500000 --from_dash_to 230112.190000-230113.070000 --term 0.1 --strategy SMA --currency BTC
```

위의 명령어를 사용해서 시뮬레이션을 실행할 경우 다음과 같이 시뮬레이션이 수행되는 것을 확인 할 수 있습니다.

```
(venv) PS C:\01_Code\smtm> python -m smtm --mode 1 --budget 500000 --from_dash_to 230112.190000-230113.070000 --term 0.1 --strategy SMA --currency BTC
...
2023-05-29 09:49:07,364 DEBUG             Analyzer - yield record KRW-BTC, buy_avg: 22744000.0, 23621000.0, 0.0, 3.856
2023-05-29 09:49:07,364 DEBUG             Analyzer - price change ratio 22779000.0 -> 23621000.0, 3.696%
2023-05-29 09:49:07,365  INFO             Analyzer - cumulative_return 500000 -> 509381.0, 1.876%
2023-05-29 09:49:07,365  INFO             Analyzer - ### Return Report ===============================
2023-05-29 09:49:07,365  INFO             Analyzer - Property                     500000 ->     509381
2023-05-29 09:49:07,365  INFO             Analyzer - Gap                                          9381
2023-05-29 09:49:07,366  INFO             Analyzer - Cumulative return                         1.876 %
2023-05-29 09:49:07,366  INFO             Analyzer - Price_change_ratio {'KRW-BTC': 3.696}
2023-05-29 09:49:07,366  INFO             Analyzer - Period 2023-01-12T19:00:00 - 2023-01-13T06:59:00
2023-05-29 09:49:08,168  INFO             Analyzer - "output/SIM-SMA-230112.190000-230113.070000.jpg" graph file created!
2023-05-29 09:49:08,168 DEBUG   SimulationOperator - ############# Simulation trading is completed
2023-05-29 09:49:08,168 DEBUG   SimulationOperator - start timer False : simulation_terminated : 33684
2023-05-29 09:49:08,169 DEBUG      Operator-Worker - Worker[Operator-Worker:33684] WAIT ==========
2023-05-29 09:49:08,206  INFO            Simulator - Terminating......
Terminating......
2023-05-29 09:49:08,206  INFO            Simulator - 프로그램을 재시작하려면 초기화하세요
프로그램을 재시작하려면 초기화하세요
2023-05-29 09:49:08,207  INFO            Simulator - Good Bye~
Good Bye~
```

## 시뮬레이션 결과 확인
Duration: 0:03:00

시뮬레이션 결과 보고서 파일은 `output` 폴더에 저장됩니다. `SIM-SMA-230112.190000-230113.070000.txt` 파일에는 모든 거래 정보 내역을 포함해서 전체 거래 요약 정보를 제공합니다.

`{'KRW-BTC': 3.696}` 시뮬레이션 기간 동안 대상 암호화폐는 3.696% 상승했으며, 최종 누적 수익률은 1.876% 입니다. 50만원을 투자해서 하루만에 9381원을 벌었네요. 5회 거래 시도를 했으며 4회 거래가 이뤄졌습니다.

```
### SUMMARY =======================================
Property                     500000 ->     509381
Gap                                          9381
Cumulative return                         1.876 %
Price_change_ratio {'KRW-BTC': 3.696}
### DEBUG INFO ====================================
memory usage:  143.53516 MB
request_list: 5
result_list: 4
info_list: 720
asset_info_list: 362
score_list: 362
```

`SIM-SMA-230112.190000-230113.070000.jpg` 파일에는 그래프가 저장됩니다. Analyzer 모듈에 설정된 이동평균선이 그려지고, 전략에서 지정한 위치에 녹색 스팟이 그려집니다. 파란색 삼각형은 매수 지점이며, 노란색은 매도 지점입니다.

아래쪽 그래프는 거래량과 누적 수익률이며, 붉은 직선은 평균 매수 가격입니다.

그래프를 통해서 한 눈에 결과를 확인 할 수 있습니다.😀

![시뮬레이션 결과 화면](./img/SIM-SMA-230112.190000-230113.070000.jpg)

그래프에 녹색 스팟을 추가하는 방법은 [smtm 사용팁 - 그래프에 스팟 그래프 추가하기](https://youtu.be/FR14ZodyDqA) 영상에 소개되어 있습니다. 직접 Analyzer 모듈을 수정해서 다양한 그래프를 추가 할 수도 있습니다.

## 정리
Duration: 0:01:00

간단하게 smtm을 설치하고 시뮬레이션을 실행해보았습니다. 그리고 시뮬레이션 결과를 확인해 보았습니다.

기본 제공되는 전략을 참고하여 직접 전략을 만들어 보세요. 그리고 대량 시뮬레이션을 통해서 전략을 최적화 보세요.

실시간 거래에서는 어떻게 동작하는지 데모 모드를 통해서 텔레그램 컨트롤러를 사용해 보는것도 좋습니다.

해당 프로그램은 오픈소스로 무료 제공되고 있으며, 필요에 따라 자유롭게 수정하여 사용이 가능합니다.

### 더 알아보기
- [썰 - 왜 암호화폐인가](https://youtu.be/lwrMAJzy8V4)
- [smtm 사용팁 - 그래프에 스팟 그래프 추가하기](https://youtu.be/FR14ZodyDqA)
- [암호화폐 자동매매 시스템 smtm - 대량 시뮬레이션](https://youtu.be/i6g2VhPl7hQ)
- [무료 오픈소스 암호화폐 자동매매 시스템 smtm 바로 써보기](https://youtu.be/la-IGHgI95g)
