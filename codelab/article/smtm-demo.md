author: Jeong Seongmoon
summary: smtm 설치 및 실시간 모의 투자
id: smtm-demo
categories: codelab,smtm
environments: Web
status: Published
feedback link: https://github.com/msaltnet/smtm

# smtm 설치 및 실시간 모의 투자

## CodeLab Overview
Duration: 0:02:00

이 코드랩에서는 암호화폐 자동매매 시스템 오픈소스 프로젝트 smtm를 설치하고, 실시간 모의 투자를 진행해 보는 방법에 대해서 설명하고 있습니다.

### 사전 준비
1. python (3.6 이상 권장)
1. Upbit에 접속 가능한 인터넷 환경 (시뮬레이션 데이터 다운로드)
1. 텔레그램 계정 (텔레그램을 이용한 컨트롤)

Upbit 계좌나 계정은 없어도 됩니다

### 배우게 될 것
1. pip를 사용해서 smtm을 설치하는 방법
1. 설치한 smtm을 사용하여 실시간 모의 투자를 하는 방법
1. smtm 모의 투자 결과 확인 및 컨트롤러 사용방법

[무료 오픈소스 암호화폐 자동매매 시스템 smtm 바로 써보기](https://youtu.be/la-IGHgI95g) 영상을 통해 코드 랩과 동일한 내용을 확인 할 수 있습니다.

![텔레그램 컨트롤러 화면](./img/IMG_3309.PNG)

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

## 텔레그램 봇 생성
Duration: 0:03:00

smtm 텔레그램 컨트롤러는 텔레그램 챗 봇을 활용해서 암호화폐 자동매매 시스템을 컨트롤 하는 방식입니다. 따라서, 텔레그램 컨트롤러를 사용하기 위해서는 텔레그램 챗봇을 생성해야 합니다.

텔레그램 챗봇은 무료이며 사용량 제한이 없습니다.😃

![텔레그램 챗봇 동작 방식](./img/telegram_controller.PNG)

텔레그램은 모바일 앱을 통해 언제 어디서나 편하게 사용할 수 있는 장점이 있습니다. 동시에 PC 브라우저를 통해서도 편리하게 사용이 가능합니다.

PC 브라우저에서 `https://web.telegram.org`을 입력하여 텔레그램을 실행합니다. `botfather`를 검색해서 대화를 시작합니다. `newbot` 커맨드로 새로운 봇을 생성합니다.

![봇 생성](./img/s1.png)

봇 이름을 입력하여 봇을 생성하면 봇을 컨틀롤 할 수 있는 토큰이 생성됩니다. 토큰을 통해서 봇 이름으로 대화를 할 수 있으므로 토큰을 잘 저장해 둡니다.

![봇 토큰](./img/s2.png)

## 텔레그램 챗 아이디 확인
Duration: 0:03:00

봇 대화방 아이디 확인을 위해서 봇과의 대화를 시작합니다. 토큰 정보와 함께 제공되는 링크를 클릭해 주면 됩니다. 대화 목록에서 봇 이름으로 검색해서 대화를 시작해도 됩니다.

![봇 대화 시작](./img/s3.png)

`getUpdated` 봇 API를 사용해서 봇에 전달된 메세지를 확인합니다. 브라우저에 아래와 같이 입력하고, token 부분을 변경하여 실행하면 봇이 수신한 메세지를 확인 할 수 있습니다.

```
https://api.telegram.org/bot1234567890:ABCDEF1234ghIklzyx57W2v1u123ew11/getUpdates
```

![봇 메세지 확인](./img/s4.png)

메세지 내용에서 대화방 아이디를 확인 할 수 있습니다. 대화방 아이디는 smtm 자동매매 시스템이 동작할 대화방 아이디를 정해주기 위해서 필요합니다. **대화방 아이디**와 **토큰 정보**가 있어야 모의 투자를 실행할 수 있습니다.

![봇 대화방 아이디 확인](./img/s5.png)

## 모의 투자 실행
Duration: 0:03:00

smtm에서 트레이딩은 Data Provider, Strategy, Trader 모듈이 순차적으로 동작하면서 진행됩니다. 기본적으로 트레이딩은 1분 간격으로 반복 수행되며, 모의 투자에서는 실시간 데이터를 기반으로 진행됩니다.

![자동 거래 시퀀스 다이어그램](./img/smtm_sequence_kr.png)

모의 투자의 경우 `DemoTrader` 모듈이 거리를 처리해 주며, 실제 계좌와는 무관하게 거래가 체결된 것 처럼 처리를 해서 가상 계좌 정보를 전달합니다.

모의 투자는 아래와 같이 앞서 생성한 텔레그램 챗 봇 토큰과 대화방 아이디와 함께 실행하면 됩니다.

```
python -m smtm --mode 3 --demo 1 --token <telegram chat-bot token> --chatid <chat id>
```

![모의 투자](./img/s6.png)

암호화폐 자동매매 시스템을 시작했다고 해서 바로 모의 투자가 시작되는 것은 아닙니다.

모의 투자를 위해서는 예산, 화폐 종류, 거래소, 전략 등을 설정해 주어야 합니다. 텔레그램 챗 봇과의 대화를 통해서 투자를 시작해 주면 됩니다.

현재 기본 제공되는 전략은 다음과 같으며, 전략은 직접 구현/최적화하여 사용해야 합니다.
- BNH: Buy and Hold 단순 분할 매수
- SMA: Simple Moving Average 단순 이동 평균선 전략
- SML: SMA + ML 단순 이동 평균선 전략에 Machine Learning 도입

현재 지원하는 암호화폐는 KRW-BTC, KRW-ETH, KRW-DOGE, KRW-XRP이 있으며, 필요에 따라 직접 추가가능합니다. [코인 추가하는 방법 영상](https://youtu.be/UikVC3b-j2M)을 보시면 간단하게 가능할 수 있습니다.

![모의 투자 시작 화면](./img/s7.png)

## 모의 투자 결과 확인
Duration: 0:01:00

투자를 시작하면 상태 조회를 통해서 현재 투자가 진행 중인지 확인 할 수 있습니다.

![모의 투자 화면](./img/s8.png)

투자 결과도 실시간으로 조회 해볼 수 있습니다. 실시간 모의 투자이기 때문에 시간이 많이 지나야 투자 결과 그래프가 제대로 그려집니다.

![모의 투자 결과 조회](./img/s9.png)

실시간 모의 투자는 실시간 시세 정보를 바탕으로 운영됩니다.

![실행 화면](./img/smtm-demo.gif)

## 정리
Duration: 0:01:00

간단하게 smtm을 설치하고 모의 투자를 실행해보았습니다. 그리고 투자 결과 조회를 확인해 보았습니다.

기본 제공되는 전략을 참고하여 직접 전략을 만들어 보세요. 그리고 대량 시뮬레이션을 통해서 전략을 최적화 보세요.

실제 계좌로 거래를 진행하기 위해서는 거래소 계좌와 API 토큰이 필요합니다. 자세한 내용은 [암호화폐 자동매매 프로그램 smtm - 실전 거래 해보기](https://youtu.be/lTeXUP-JXQc) 영상을 확인해 보세요.

해당 프로그램은 오픈소스로 무료 제공되고 있으며, 필요에 따라 자유롭게 수정하여 사용이 가능합니다.

### 더 알아보기
- [썰 - 왜 암호화폐인가](https://youtu.be/lwrMAJzy8V4)
- [smtm 사용팁 - 그래프에 스팟 그래프 추가하기](https://youtu.be/FR14ZodyDqA)
- [암호화폐 자동매매 시스템 smtm - 대량 시뮬레이션](https://youtu.be/i6g2VhPl7hQ)
- [무료 오픈소스 암호화폐 자동매매 시스템 smtm 바로 써보기](https://youtu.be/la-IGHgI95g)
