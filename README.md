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
