import time
import unittest
from smtm import MassSimulator, Config
from unittest.mock import *


class MassSimulatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("builtins.print")
    def test_ITG_run_single_simulation(self, mock_print):
        mass = MassSimulator()

        mass.run("integration_tests/data/mass_simulation_config.json")


class MassSimulator3mIntervalIntegrationTests(unittest.TestCase):
    # It should be executed after set Config.candle_interval = 180

    def test_ITG_run_single_simulation(self):
        mass = MassSimulator()

        mass.run("integration_tests/data/mass_simulation_3m_config.json")
