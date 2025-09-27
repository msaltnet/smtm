# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An algorithm-based automated cryptocurrency trading system made in Python. https://smtm.msalt.net

[한국어](https://github.com/msaltnet/smtm/blob/master/README-ko-kr.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

"Data Gathering🔍 ➡️ Strategy Algorithm🖥️ ➡️ Realtime Trading💸" Repeat the process at a set interval

1. The Data Provider module aggregates data  
2. Make a decision using the Strategy module  
3. Execute a trading via the Trader module  
 --- repeat ---
4. Create analyzing result by the Analyzer module  

❗ It is not suitable for high-performance trading machines that need to process many trades in a short timeframe of seconds.

![smtm-procedure](https://github.com/user-attachments/assets/b4bb1729-e455-4329-914c-19bca6914735)

## Features
- Mass-simulation with Multi-process
- Remote Control with Jupyter Notebook
- Automated trading programs controlled by Telegram

Controlling an automated trading program using the Telegram messenger

![smtm_bot](https://github.com/user-attachments/assets/bddcee69-469a-4e57-b0fa-b1b78266a8a7)

![smtm-telegram-mode](https://github.com/msaltnet/smtm/assets/9311990/22ba2ebd-13e6-4eee-a829-94209c5618a9)

## Architecture
Layered Architecture for Scalability and Maintainability

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**

![smtm component](https://user-images.githubusercontent.com/9311990/221420624-9807ca39-31c7-4bb6-b3de-3a4114f22430.png)



2. 거대한 클래스 분할
TelegramController (714줄): 너무 많은 책임을 가짐
메시지 처리, 설정 관리, 거래 실행, UI 로직이 모두 섞여있음
해결방안: Command Pattern과 State Pattern 적용하여 분할
Analyzer (935줄): 데이터 분석과 그래프 생성이 혼재
해결방안: DataAnalyzer, GraphGenerator, ReportGenerator로 분할

7. 타입 힌트 부족
대부분의 메서드에 타입 힌트가 없음
해결방안: Python 3.8+ 타입 힌트 추가

8. 로깅 개선
일관성 없는 로그 레벨 사용
해결방안: 구조화된 로깅 도입