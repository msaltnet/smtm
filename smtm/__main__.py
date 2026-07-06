import argparse
from argparse import RawTextHelpFormatter
import json
import sys

from .controller.controller import Controller
from .controller.telegram import TelegramController
from .log_manager import LogManager
from .__init__ import __version__


DEFAULT_MODE = 2
DEFAULT_CONFIG = {
    "budget": 500000,
    "term": 60,
    "exchange": "UPB",
    "currency": "BTC",
    "paper": False,
    "log": None,
    "token": None,
    "chatid": None,
    "mode": DEFAULT_MODE,
    "strategy": "BNH",
}
CONFIG_ALIASES = {
    "interval": "term",
    "chat_id": "chatid",
    "virtual": "paper",
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="""
smtm - LLM-powered Crypto Trading System

mode:
    0: Interactive CLI trading
    1: Telegram chatbot trading

Example)
# Run CLI interactive trading
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB

# Run with a JSON config file
python -m smtm --config config/virtual-upbit.json

# Run Telegram chatbot trading
python -m smtm --mode 1 --token <token> --chatid <chatid>
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument("--config", help="JSON config file path", default=None)
    parser.add_argument("--budget", help="budget", type=int, default=None)
    parser.add_argument(
        "--term", help="trading tick interval (seconds)", type=float, default=None
    )
    parser.add_argument(
        "--exchange",
        help="exchange code UPB: Upbit, BTH: Bithumb",
        default=None,
    )
    parser.add_argument("--currency", help="trading currency e.g.BTC", default=None)
    parser.add_argument(
        "--paper",
        "--virtual",
        help="virtual trading mode (simulation trader, real-time quotes)",
        action=argparse.BooleanOptionalAction,
        dest="paper",
        default=None,
    )
    parser.add_argument("--log", help="log file name", default=None)
    parser.add_argument("--token", help="telegram chat-bot token", default=None)
    parser.add_argument("--chatid", help="telegram chat id", default=None)
    parser.add_argument(
        "--mode",
        help="0: interactive CLI, 1: telegram chatbot",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--strategy",
        help="trading strategy code (BNH, RSI, SMA, LLM)",
        default=None,
    )
    parser.add_argument(
        "--profile",
        help="account profile name in config/profiles/",
        default=None,
    )
    parser.add_argument(
        "--version", action="version", version=f"smtm version: {__version__}"
    )
    return parser


def load_config(path):
    with open(path, "r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)

    if not isinstance(raw_config, dict):
        raise ValueError("config file must contain a JSON object")

    config = {}
    allowed_keys = set(DEFAULT_CONFIG.keys()) | set(CONFIG_ALIASES.keys())
    unknown_keys = sorted(set(raw_config.keys()) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"unknown config key(s): {', '.join(unknown_keys)}")

    for key, value in raw_config.items():
        config[CONFIG_ALIASES.get(key, key)] = value
    return config


def merge_config(args):
    config = dict(DEFAULT_CONFIG)
    if args.config:
        config.update(load_config(args.config))

    if getattr(args, "profile", None):
        # 프로파일은 config 파일보다 뒤, CLI 플래그보다 앞에 반영된다.
        # MVP 범위: 프로파일의 키는 모두 이 config 딕셔너리에 병합되지만,
        # Controller가 실제로 사용하는 것은 그중 6개 키(exchange/currency/
        # budget/virtual/term/strategy)뿐이다. strategy_params/safety 등은
        # 병합되어도 Controller 부팅 경로에서는 읽히지 않으므로 CLI 부팅
        # 시에는 적용되지 않는다 — 해당 값은 실행 중 에이전트의
        # switch_profile 경로로 적용된다.
        from .profile_store import ProfileStore
        profile = ProfileStore().load(args.profile)
        for key, value in profile.items():
            if key == "name":
                continue
            config[CONFIG_ALIASES.get(key, key)] = value

    for key in DEFAULT_CONFIG:
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            config[key] = cli_value

    return argparse.Namespace(config=args.config, profile=args.profile, **config)


def parse_args(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return parser, merge_config(args)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))


def main(argv=None):
    parser, args = parse_args(argv)
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
            paper=args.paper,
            strategy=args.strategy,
        )
        controller.main()
    elif args.mode == 1:
        try:
            tcb = TelegramController(token=args.token, chat_id=args.chatid)
        except ValueError:
            print("Please check your telegram chat-bot token")
            sys.exit(0)
        tcb.main()


if __name__ == "__main__":
    main()
