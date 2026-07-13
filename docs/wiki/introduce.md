# smtm

> It's a game to get money. 

AI Agent 기반 자율 암호화폐 자동매매 프로그램. https://smtm.msalt.net

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

채팅으로 제어하는 AI Agent가 계좌 등록, 프로파일 관리, 하나 이상의 매매 세션 병렬 시작/중지를 담당하고, 실제 매매는 각 세션마다 별도의 고정 주기 루프가 수행합니다.

1. SystemOperator(채팅 에이전트)가 Tool을 통해 세션을 생성/시작/중지/비교하며, 기존 단일 세션 select/start/stop 흐름도 그대로 지원  
2. 각 세션의 TradingOperator가 고정 주기 루프를 실행: DataProvider -> Strategy -> SafetyGuard -> Trader -> Analyzer  
3. Strategy는 교체 가능 — 알고리즘 전략(Buy & Hold, RSI, SMA) 또는 매 틱 LLM 판단 1회(`LLM`)  
4. SafetyGuard가 모든 주문 전에 거래 제한을 강제하고(같은 계좌를 공유하는 세션 간에는 계좌 단위 가드도 함께 적용), SystemMonitor가 세션별로 태깅하여 독립적으로 모든 활동을 기록  

❗ 초 단위의 짧은 시간에 많은 거래를 처리해야하는 고성능 트레이딩 머신으로는 적합하지 않으며 충분한 검토가 필요합니다.

## 주요기능
- 채팅 기반 오케스트레이션 에이전트: 계좌 등록, 프로파일 관리, 매매 세션 병렬 생성/시작/중지
- 고정 주기로 실행되는 교체 가능한 매매 전략: Buy & Hold, RSI, SMA, 또는 매 틱 LLM 판단 1회(`LLM`)
- 안전 가드레일 (최대 거래 금액, 일일 거래 제한, 손실 비율 상한)
- 텔레그램 챗봇 제어
- 가상거래 모드 (실시간 시세 + 가상 잔고)
- 교체 가능한 LLM 클라이언트 인터페이스 — 현재 Claude 구현, OpenAI / Ollama 어댑터는 예정

텔레그램 메신저로 보낸 메시지가 AI Agent에 전달되어, 계좌·프로파일·세션 관리부터 거래 시작/중지, 포트폴리오 조회까지 모두 채팅으로 제어할 수 있습니다.

## 관련 도서

"암호화폐 자동매매 시스템 만들기 with 파이썬" 도서 - [교보문고](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967) [예스24](http://www.yes24.com/Product/Goods/107635612) [알라딘](https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=289526248)

이 도서는 smtm의 이전 룰 기반 버전(v1.x)을 기반으로 작성되었습니다.

[![smtm-book](https://user-images.githubusercontent.com/9311990/157685437-dcedd2c0-9f0c-400c-a3d4-017354279b60.png)](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967)


# smtm

> It's a game to get money. 

An AI Agent-powered autonomous cryptocurrency trading system made in Python. https://smtm.msalt.net

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

A chat-driven AI Agent orchestrates the system -- registering accounts, managing profiles, and starting/stopping one or more trading sessions in parallel -- while each session runs its own separate fixed-interval loop that executes the actual trades.

1. SystemOperator (the chat agent) manages sessions via tools -- create/start/stop/compare -- and still supports the legacy single-session select/start/stop flow  
2. Each session's TradingOperator runs a fixed-interval loop: DataProvider -> Strategy -> SafetyGuard -> Trader -> Analyzer  
3. Strategy is pluggable -- algorithmic (Buy & Hold, RSI, SMA) or a single LLM judgment per tick (`LLM`)  
4. SafetyGuard enforces trading limits before every order (with an account-level guard across sessions sharing an account); SystemMonitor independently logs all activity, tagged by session  

❗ It is not suitable for high-performance trading machines that need to process many trades in a short timeframe of seconds.

## Features
- Chat-based orchestration agent: register accounts, manage profiles, and create/start/stop parallel trading sessions
- Pluggable trading strategies executed on a fixed interval: Buy & Hold, RSI, SMA, or a single LLM judgment per tick (`LLM`)
- Safety guardrails (max trade amount, daily trade limit, loss ratio ceiling)
- Telegram chatbot control
- Virtual trading mode (real-time quotes with a simulated balance)
- Pluggable LLM client interface — Claude is implemented; OpenAI / Ollama adapters are planned

Every message you send through the Telegram messenger is forwarded to the AI Agent, so you can manage accounts, profiles, and sessions, start/stop trading, and check your portfolio -- all by chatting.

## Related Book

The book "Building a Cryptocurrency Auto-Trading System with Python" (Korean) is based on the earlier rule-based version (v1.x) of smtm.

[![smtm-book](https://user-images.githubusercontent.com/9311990/157685437-dcedd2c0-9f0c-400c-a3d4-017354279b60.png)](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967)
