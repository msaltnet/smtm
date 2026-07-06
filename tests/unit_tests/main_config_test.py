import json
import tempfile
import unittest

from smtm.__main__ import parse_args


class MainConfigTests(unittest.TestCase):
    def _write_config(self, data):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        with temp:
            json.dump(data, temp)
        return temp.name

    def test_config_file_supplies_cli_values(self):
        path = self._write_config({
            "mode": 0,
            "budget": 500000,
            "currency": "BTC",
            "exchange": "UPB",
            "paper": True,
            "term": 30,
        })

        parser, args = parse_args(["--config", path])

        self.assertIsNotNone(parser)
        self.assertEqual(args.mode, 0)
        self.assertEqual(args.budget, 500000)
        self.assertEqual(args.currency, "BTC")
        self.assertEqual(args.exchange, "UPB")
        self.assertTrue(args.paper)
        self.assertEqual(args.term, 30)

    def test_cli_args_override_config_file(self):
        path = self._write_config({
            "mode": 0,
            "budget": 500000,
            "currency": "BTC",
            "exchange": "UPB",
            "paper": True,
        })

        _, args = parse_args([
            "--config", path,
            "--budget", "1000000",
            "--currency", "ETH",
            "--no-paper",
        ])

        self.assertEqual(args.budget, 1000000)
        self.assertEqual(args.currency, "ETH")
        self.assertFalse(args.paper)

    def test_config_aliases_are_supported(self):
        path = self._write_config({
            "mode": 1,
            "interval": 15,
            "chat_id": "1234",
            "token": "token",
            "virtual": True,
        })

        _, args = parse_args(["--config", path])

        self.assertEqual(args.mode, 1)
        self.assertEqual(args.term, 15)
        self.assertEqual(args.chatid, "1234")
        self.assertTrue(args.paper)

    def test_virtual_cli_alias_sets_paper_mode(self):
        _, args = parse_args(["--mode", "0", "--virtual"])

        self.assertTrue(args.paper)

    def test_no_virtual_cli_alias_disables_config_value(self):
        path = self._write_config({"mode": 0, "virtual": True})

        _, args = parse_args(["--config", path, "--no-virtual"])

        self.assertFalse(args.paper)

    def test_unknown_config_key_exits_with_error(self):
        path = self._write_config({"mode": 0, "unknown": True})

        with self.assertRaises(SystemExit):
            parse_args(["--config", path])


class StrategyProfileConfigTests(unittest.TestCase):
    def test_default_strategy_is_bnh(self):
        _, args = parse_args([])
        self.assertEqual(args.strategy, "BNH")

    def test_strategy_flag_overrides_default(self):
        _, args = parse_args(["--strategy", "RSI"])
        self.assertEqual(args.strategy, "RSI")

    def test_config_file_strategy_key_is_accepted(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"strategy": "SMA"}, f)
            path = f.name
        _, args = parse_args(["--config", path])
        self.assertEqual(args.strategy, "SMA")

    def test_profile_flag_parsed(self):
        # ProfileStore().load(...) hits the real config/profiles/ directory,
        # so mock it out rather than depending on a fixture profile file
        # existing on disk.
        from unittest.mock import patch
        with patch(
            "smtm.profile_store.ProfileStore.load",
            return_value={"name": "my-profile", "strategy": "RSI", "budget": 300000, "virtual": True},
        ):
            _, args = parse_args(["--profile", "my-profile"])
        self.assertEqual(args.profile, "my-profile")
        self.assertEqual(args.strategy, "RSI")      # profile value merged
        self.assertEqual(args.budget, 300000)
        self.assertTrue(args.paper)                  # virtual → paper alias mapping

    def test_cli_flag_overrides_profile(self):
        # Verify CLI flags override profile values
        from unittest.mock import patch
        with patch(
            "smtm.profile_store.ProfileStore.load",
            return_value={"name": "my-profile", "strategy": "RSI", "budget": 300000, "virtual": True},
        ):
            _, args = parse_args(["--profile", "my-profile", "--strategy", "LLM"])
        self.assertEqual(args.strategy, "LLM")      # CLI flag overrides profile


if __name__ == "__main__":
    unittest.main()
