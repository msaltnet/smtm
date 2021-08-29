import time
import unittest
from smtm import MassSimulator
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
