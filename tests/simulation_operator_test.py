import unittest
from smtm import SimulationOperator
from unittest.mock import *
import requests
import threading

class SimulationOperatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("smtm.Operator.initialize")
    def test_initialize_call_simulator_trader_initialize_with_config(self, OperatorInitialize):
        sop = SimulationOperator()
        trader = Mock()
        trader.initialize = MagicMock()
        strategy = Mock()
        strategy.initialize = MagicMock()
        sop.trader = trader
        sop.strategy = strategy
        sop.initialize("apple", "kiwi", "mango", strategy, "orange", "papaya", "pear", "grape")
        OperatorInitialize.assert_called_once_with("apple", "kiwi", "mango", strategy, "orange")
        trader.initialize.assert_called_once_with("apple", "papaya", "pear", "grape")

    @patch("smtm.Operator.initialize")
    def test_initialize_call_strategy_initialize_with_config(self, OperatorInitialize):
        sop = SimulationOperator()
        trader = Mock()
        trader.initialize = MagicMock()
        strategy = Mock()
        strategy.initialize = MagicMock()
        sop.trader = trader
        sop.strategy = strategy
        sop.initialize("apple", "kiwi", "mango", strategy, "orange", "papaya", "pear", "grape")
        strategy.initialize.assert_called_once_with("grape")

    @patch("smtm.Operator.setup")
    def test_setup_call_super_setup(self, OperatorSetup):
        sop = SimulationOperator()
        sop.setup(10)
        OperatorSetup.assert_called_once_with(10)

    @patch("smtm.Operator.start")
    def test_start_call_super_start(self, OperatorStart):
        sop = SimulationOperator()
        sop.start()
        OperatorStart.assert_called_once()

    @patch("smtm.Operator.stop")
    def test_stop_call_super_stop(self, OperatorStop):
        sop = SimulationOperator()
        sop.stop()
        OperatorStop.assert_called_once()
