import argparse
from argparse import RawTextHelpFormatter
import sys

from .controller.telegram import TelegramController
from .log_manager import LogManager
from .__init__ import __version__


def build_parser():
    parser = argparse.ArgumentParser(
        description="""
smtm - AI Agent 기반 암호화폐 자동매매 시스템

텔레그램 챗봇으로 제어합니다. 예산/전략/거래소 등 설정은 채팅으로 합니다.
default 세션은 가상거래로 시작하며, 실거래는 채팅으로 계좌를 등록한 뒤
세션을 만들어 시작합니다.

Example)
python -m smtm --token <telegram-bot-token> --chatid <chat-id>
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument("--token", help="telegram chat-bot token", default=None)
    parser.add_argument("--chatid", help="telegram chat id", default=None)
    parser.add_argument("--log", help="log file name", default=None)
    parser.add_argument(
        "--version", action="version", version=f"smtm version: {__version__}"
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.log is not None:
        LogManager.change_log_file(args.log)

    try:
        controller = TelegramController(token=args.token, chat_id=args.chatid)
    except ValueError:
        print("Please check your telegram chat-bot token")
        sys.exit(0)
    controller.main()


if __name__ == "__main__":
    main()
