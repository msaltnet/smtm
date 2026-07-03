"""
E2E 테스트: 채팅 기반 거래 흐름 (Task 15에서 2계층 아키텍처 기준으로 재작성 예정)

기존 시나리오는 LlmOperator + execute_trade Tool 기반이었으며,
Task 11에서 SystemOperator(오케스트레이션 전용) + TradingOperator(매매 전담)
구조로 전환되면서 폐기되었다.
"""

import unittest


@unittest.skip("rewritten in Task 15 for two-layer architecture")
class ChatTradingE2ETest(unittest.TestCase):
    """placeholder — Task 15에서 SystemOperator/TradingOperator 시나리오로 재작성"""

    def test_placeholder(self):
        pass
