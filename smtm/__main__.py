import argparse
from argparse import RawTextHelpFormatter
import os
import sys

from .controller.controller import Controller
from .controller.telegram_controller import TelegramController
from .log_manager import LogManager
from .__init__ import __version__

if __name__ == "__main__":
    DEFAULT_MODE = 2
    parser = argparse.ArgumentParser(
        description="""
smtm - LLM-powered Crypto Trading System

mode:
    0: Interactive CLI trading
    1: Telegram chatbot trading

Example)
# Run CLI interactive trading
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB

# Run Telegram chatbot trading
python -m smtm --mode 1 --token <token> --chatid <chatid>
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument("--budget", help="budget", type=int, default=500000)
    parser.add_argument(
        "--term", help="trading tick interval (seconds)", type=float, default=60
    )
    parser.add_argument(
        "--exchange",
        help="exchange code UPB: Upbit, BTH: Bithumb",
        default="UPB",
    )
    parser.add_argument("--currency", help="trading currency e.g.BTC", default="BTC")
    parser.add_argument("--log", help="log file name", default=None)
    parser.add_argument("--token", help="telegram chat-bot token", default=None)
    parser.add_argument("--chatid", help="telegram chat id", default=None)
    parser.add_argument(
        "--mode",
        help="0: interactive CLI, 1: telegram chatbot",
        type=int,
        default=DEFAULT_MODE,
    )
    parser.add_argument(
        "--version", action="version", version=f"smtm version: {__version__}"
    )

    args = parser.parse_args()
    if args.log is not None:
        LogManager.change_log_file(args.log)

    if args.mode == DEFAULT_MODE:
        parser.print_help()
        sys.exit(0)

    if args.mode == 0:
        controller = Controller(
            budget=args.budget,
            interval=args.term,
            currency=args.currency,
            exchange=args.exchange,
        )
        controller.main()
    elif args.mode == 1:
        try:
            tcb = TelegramController(token=args.token, chat_id=args.chatid)
        except ValueError:
            print("Please check your telegram chat-bot token")
            sys.exit(0)
        tcb.main()
