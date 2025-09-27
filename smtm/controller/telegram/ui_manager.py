"""
Telegram UI Manager
텔레그램 UI 관리 담당 클래스

Handles UI-related logic such as keyboard generation and message formatting.
키보드 생성, 메시지 포맷팅 등 UI 관련 로직을 담당합니다.
"""

import json
from urllib import parse
from typing import Dict, List, Any, Optional
from ...log_manager import LogManager


class TelegramUIManager:
    """
    Telegram UI Manager Class
    텔레그램 UI 관련 로직을 담당하는 클래스

    Handles Telegram UI-related logic such as keyboard generation and message formatting.
    키보드 생성, 메시지 포맷팅 등 텔레그램 UI 관련 로직을 담당합니다.
    """

    MESSAGE = {
        "ko": {
            "GUIDE_READY": "자동 거래 시작 전입니다.\n명령어를 입력해주세요.\n\n",
            "GUIDE_RUNNING": "자동 거래 운영 중입니다.\n명령어를 입력해주세요.\n\n",
            "PERIOD_1": "1. 최근 6시간",
            "PERIOD_2": "2. 최근 12시간",
            "PERIOD_3": "3. 최근 24시간",
            "PERIOD_4": "4. 24시간 전부터 12시간",
            "PERIOD_5": "5. 48시간 전부터 24시간",
            "COMMAND_G_1": "1. 시작 - 자동 거래 시작",
            "COMMAND_G_2": "2. 중지 - 자동 거래 중지",
            "COMMAND_G_3": "3. 상태 조회 - 운영 상태 조회",
            "COMMAND_G_4": "4. 수익률 조회 - 기간별 수익률 조회",
            "COMMAND_G_5": "5. 거래내역 조회 - 모든 거래내역 조회",
            "COMMAND_C_1": "시작",
            "COMMAND_C_2": "중지",
            "COMMAND_C_3": "상태 조회",
            "COMMAND_C_4": "수익률 조회",
            "COMMAND_C_5": "거래내역 조회",
            "SETUP_1": "운영 예산을 정해주세요",
            "SETUP_2": "거래할 화폐를 정해주세요",
            "SETUP_3": "사용할 데이터를 선택해 주세요",
            "SETUP_4": "거래소를 선택해 주세요",
            "SETUP_5": "전략을 선택해 주세요",
            "SETUP_6": "자동 거래를 시작할까요?",
            "SETUP_7": "조회할 기간을 정해주세요",
            "ERROR_EXCHANGE": "지원하지 않는 거래소입니다.",
            "ERROR_CURRENCY": "현재 지원하지 않는 코인입니다.",
            "ERROR_RESTART": "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요",
            "ERROR_QUERY": "수익률 조회중 문제가 발생하였습니다.",
            "INFO_CURRENCY": "화폐",
            "INFO_STRATEGY": "전략",
            "INFO_TRADER": "거래소",
            "INFO_BUDGET": "예산",
            "INFO_INTERVAL": "거래 간격",
            "INFO_START": "자동 거래가 시작되었습니다",
            "NOTIFY_STOP": "자동 거래가 중지되었습니다",
            "NOTIFY_ASSET": "자산",
            "NOTIFY_RATE": "수익률",
            "NOTIFY_COMPARE_RATE": "비교 수익률",
            "NOTIFY_PERIOD_RATE": "구간 수익률",
            "NOTIFY_TOTAL_RATE": "누적 수익률",
            "INFO_STATUS_READY": "자동 거래 시작 전입니다",
            "INFO_STATUS_RUNNING": "자동 거래 운영 중입니다",
            "INFO_RESTART_QUERY": "다시 시작해 주세요",
            "INFO_QUERY_RUNNING": "조회중입니다",
            "INFO_QUERY_EMPTY": "거래 기록이 없습니다",
        },
        "en": {
            "GUIDE_READY": "Before starting automatic trading.\nPlease enter a command.\n\n",
            "GUIDE_RUNNING": "Automatic trading is in operation.\nPlease enter a command.\n\n",
            "PERIOD_1": "1. Last 6 hours",
            "PERIOD_2": "2. Last 12 hours",
            "PERIOD_3": "3. Last 24 hours",
            "PERIOD_4": "4. 24 hours to 12 hours ago",
            "PERIOD_5": "5. 48 hours to 24 hours ago",
            "COMMAND_G_1": "1. Start - Start automatic trading",
            "COMMAND_G_2": "2. Stop - Stop automatic trading",
            "COMMAND_G_3": "3. Status - Operation status check",
            "COMMAND_G_4": "4. Return rate - Return rate by period",
            "COMMAND_G_5": "5. Transaction history - View all transaction history",
            "COMMAND_C_1": "Start",
            "COMMAND_C_2": "Stop",
            "COMMAND_C_3": "Status",
            "COMMAND_C_4": "Return rate",
            "COMMAND_C_5": "Transaction history",
            "SETUP_1": "Please set the operating budget",
            "SETUP_2": "Please select the currency to trade",
            "SETUP_3": "Please select the data to use",
            "SETUP_4": "Please select the exchange",
            "SETUP_5": "Please select a strategy",
            "SETUP_6": "Do you want to start automatic trading?",
            "SETUP_7": "Please select the period to query",
            "ERROR_EXCHANGE": "Unsupported exchange",
            "ERROR_CURRENCY": "Currently unsupported coin",
            "ERROR_RESTART": "Automatic trading has not started.\nPlease start over",
            "ERROR_QUERY": "There was a problem with the return rate query.",
            "INFO_CURRENCY": "Currency",
            "INFO_STRATEGY": "Strategy",
            "INFO_TRADER": "Exchange",
            "INFO_BUDGET": "Budget",
            "INFO_INTERVAL": "Trading interval",
            "INFO_START": "Automatic trading has started",
            "NOTIFY_STOP": "Automatic trading has stopped",
            "NOTIFY_ASSET": "Asset",
            "NOTIFY_RATE": "Return rate",
            "NOTIFY_COMPARE_RATE": "Comparison rate",
            "NOTIFY_PERIOD_RATE": "Period rate",
            "NOTIFY_TOTAL_RATE": "Total rate",
            "INFO_STATUS_READY": "Before starting automatic trading",
            "INFO_STATUS_RUNNING": "Automatic trading is in operation",
            "INFO_RESTART_QUERY": "Please start over",
            "INFO_QUERY_RUNNING": "Querying",
            "INFO_QUERY_EMPTY": "No transaction history",
        },
    }

    def __init__(self, language: str = "ko"):
        """
        Initialize Telegram UI Manager
        텔레그램 UI 매니저 초기화

        Args:
            language: UI language (ko/en) / UI 언어 (ko/en)
        """
        self.logger = LogManager.get_logger("TelegramUIManager")
        self.msg = self.MESSAGE.get(language, self.MESSAGE["ko"])
        self.main_keyboard: Optional[str] = None
        self.setup_list: List[Dict[str, Any]] = []
        self.score_query_list: List[Dict[str, Any]] = []
        self._create_keyboards()

    def _create_keyboards(self) -> None:
        """
        Create all keyboards
        키보드들을 생성합니다.
        """
        self._create_main_keyboard()
        self._create_setup_keyboards()
        self._create_score_query_keyboards()

    def _create_main_keyboard(self) -> None:
        """
        Create main keyboard
        메인 키보드를 생성합니다.
        """
        main_keyboard = {
            "keyboard": [
                [{"text": self.msg["COMMAND_C_1"]}, {"text": self.msg["COMMAND_C_2"]}],
                [
                    {"text": self.msg["COMMAND_C_3"]},
                    {"text": self.msg["COMMAND_C_4"]},
                    {"text": self.msg["COMMAND_C_5"]},
                ],
            ]
        }
        main_keyboard = json.dumps(main_keyboard)
        self.main_keyboard = parse.quote(main_keyboard)

    def _create_setup_keyboards(self) -> None:
        """
        Create setup keyboards
        설정 키보드들을 생성합니다.
        """
        self.setup_list = [
            {
                "guide": self.msg["SETUP_1"],
                "keyboard": ["50000", "100000", "500000", "1000000"],
            },
            {
                "guide": self.msg["SETUP_2"],
                "keyboard": ["BTC", "ETH", "DOGE", "XRP"],
            },
            {
                "guide": self.msg["SETUP_3"],
                "keyboard": [],
            },
            {"guide": self.msg["SETUP_4"], "keyboard": ["1. Upbit", "2. Bithumb"]},
            {
                "guide": self.msg["SETUP_5"],
                "keyboard": [],
            },  # Strategies are set dynamically / 전략은 동적으로 설정
            {"guide": self.msg["SETUP_6"], "keyboard": ["1. Yes", "2. No"]},
        ]
        self._convert_keyboard_markup(self.setup_list)

    def _create_score_query_keyboards(self) -> None:
        """
        Create score query keyboards
        수익률 조회 키보드들을 생성합니다.
        """
        self.score_query_list = [
            {
                "guide": self.msg["SETUP_7"],
                "keyboard": [
                    self.msg["PERIOD_1"],
                    self.msg["PERIOD_2"],
                    self.msg["PERIOD_3"],
                    self.msg["PERIOD_4"],
                    self.msg["PERIOD_5"],
                ],
            },
        ]
        self._convert_keyboard_markup(self.score_query_list)

    @staticmethod
    def _convert_keyboard_markup(setup_list: List[Dict[str, Any]]) -> None:
        """
        Convert keyboard markup
        키보드 마크업을 변환합니다.
        """
        for item in setup_list:
            markup = {"keyboard": []}
            for key in item["keyboard"]:
                markup["keyboard"].append([{"text": key}])
            markup = json.dumps(markup)
            item["keyboard"] = parse.quote(markup)

    def update_data_provider_keyboard(
        self, data_providers: List[Dict[str, Any]]
    ) -> None:
        """
        Update data provider keyboard
        데이터 프로바이더 키보드를 업데이트합니다.
        """
        data_provider_list = []
        for dp_item in data_providers:
            data_provider_list.append(dp_item["name"])
        self.setup_list[2]["keyboard"] = data_provider_list
        self._convert_keyboard_markup([self.setup_list[2]])

    def update_strategy_keyboard(self, strategies: List[Dict[str, Any]]) -> None:
        """
        Update strategy keyboard
        전략 키보드를 업데이트합니다.
        """
        strategy_list = []
        for s_item in strategies:
            strategy_list.append(s_item["name"])
        self.setup_list[4]["keyboard"] = strategy_list
        self._convert_keyboard_markup([self.setup_list[4]])

    def get_guide_message(self, is_running: bool = False) -> str:
        """
        Get guide message
        가이드 메시지를 반환합니다.
        """
        if is_running:
            message = self.msg["GUIDE_RUNNING"]
        else:
            message = self.msg["GUIDE_READY"]

        command_guides = [
            self.msg["COMMAND_G_1"],
            self.msg["COMMAND_G_2"],
            self.msg["COMMAND_G_3"],
            self.msg["COMMAND_G_4"],
            self.msg["COMMAND_G_5"],
        ]

        for guide in command_guides:
            message += guide + "\n"

        return message

    def get_setup_message(self, step: int) -> tuple[str, str]:
        """
        Get setup message for specific step
        설정 단계별 메시지와 키보드를 반환합니다.
        """
        if step >= len(self.setup_list):
            return "", ""

        item = self.setup_list[step]
        return item["guide"], item["keyboard"]

    def get_score_query_message(self, step: int) -> tuple[str, str]:
        """
        Get score query message for specific step
        수익률 조회 단계별 메시지와 키보드를 반환합니다.
        """
        if step >= len(self.score_query_list):
            return "", ""

        item = self.score_query_list[step]
        return item["guide"], item["keyboard"]

    def format_trading_summary(
        self, currency: str, strategy_name: str, trader_name: str, budget: float
    ) -> str:
        """
        Format trading summary message
        거래 설정 요약 메시지를 포맷합니다.
        """
        return "".join(
            [
                f"{self.msg['INFO_CURRENCY']}: {currency}\n",
                f"{self.msg['INFO_STRATEGY']}: {strategy_name}\n",
                f"{self.msg['INFO_TRADER']}: {trader_name}\n",
                f"{self.msg['INFO_BUDGET']}: {budget}\n",
            ]
        )

    def format_start_message(
        self,
        currency: str,
        strategy_name: str,
        trader_name: str,
        budget: float,
        interval: int,
    ) -> str:
        """
        Format start message
        시작 메시지를 포맷합니다.
        """
        return "".join(
            [
                f"{self.msg['INFO_START']}\n",
                f"{self.msg['INFO_CURRENCY']}: {currency}\n",
                f"{self.msg['INFO_STRATEGY']}: {strategy_name}\n",
                f"{self.msg['INFO_TRADER']}: {trader_name}\n",
                f"{self.msg['INFO_BUDGET']}: {budget}\n",
                f"{self.msg['INFO_INTERVAL']}: {interval}",
            ]
        )

    def format_stop_message(self, last_report: Optional[Dict[str, Any]] = None) -> str:
        """
        Format stop message
        중지 메시지를 포맷합니다.
        """
        if last_report is None:
            return self.msg["NOTIFY_STOP"]

        score_message = [
            f"{self.msg['NOTIFY_STOP']}\n",
            f"{last_report['summary'][8][1]} - {last_report['summary'][8][2]}\n",
            f"{self.msg['NOTIFY_ASSET']}: {last_report['summary'][0]} -> {last_report['summary'][1]}\n",
            f"{self.msg['NOTIFY_RATE']}: {last_report['summary'][2]}\n",
            f"{self.msg['NOTIFY_COMPARE_RATE']}: {last_report['summary'][3]}\n",
        ]
        return "".join(score_message)

    def format_score_message(self, score: Dict[str, Any]) -> str:
        """
        Format score message
        수익률 메시지를 포맷합니다.
        """
        diff = score[1] - score[0]
        ratio = round(diff / score[0] * 100, 3)
        score_message = [
            f"{score[8][1]} - {score[8][2]}\n",
            f"{self.msg['NOTIFY_ASSET']}: {score[0]} -> {score[1]}\n",
            f"{self.msg['NOTIFY_PERIOD_RATE']}: {ratio}\n",
            f"{score[8][0]}~\n",
            f"{self.msg['NOTIFY_TOTAL_RATE']}: {score[2]}\n",
            f"{self.msg['NOTIFY_COMPARE_RATE']}: {score[3]}\n",
        ]
        return "".join(score_message)

    def format_trading_records(self, results: List[Dict[str, Any]]) -> str:
        """
        Format trading records message
        거래 기록 메시지를 포맷합니다.
        """
        if not results:
            return self.msg["INFO_QUERY_EMPTY"]

        message = []
        for result in results:
            message.append(f"@{result['date_time']}, {result['type']}\n")
            message.append(f"{result['price']} x {result['amount']}\n")
        message.append(f"Total {len(results)} records\n")
        return "".join(message)
