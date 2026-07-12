import unittest

from smtm.__main__ import parse_args


class MainArgsTests(unittest.TestCase):
    def test_token_and_chatid_are_parsed(self):
        args = parse_args(["--token", "my-token", "--chatid", "1234"])

        self.assertEqual(args.token, "my-token")
        self.assertEqual(args.chatid, "1234")

    def test_log_is_parsed(self):
        args = parse_args(["--log", "smtm.log"])

        self.assertEqual(args.log, "smtm.log")

    def test_defaults_are_none(self):
        args = parse_args([])

        self.assertIsNone(args.token)
        self.assertIsNone(args.chatid)
        self.assertIsNone(args.log)

    def test_removed_flags_are_rejected(self):
        # CLI 인터랙티브 모드가 사라지면서 함께 제거된 플래그들
        for argv in (
            ["--mode", "0"],
            ["--config", "config/whatever.json"],
            ["--budget", "500000"],
            ["--currency", "BTC"],
            ["--exchange", "UPB"],
            ["--term", "60"],
            ["--strategy", "RSI"],
            ["--profile", "my-profile"],
            ["--virtual"],
            ["--paper"],
        ):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    parse_args(argv)


class ControllerExportTests(unittest.TestCase):
    def test_cli_controller_is_gone(self):
        import smtm

        self.assertFalse(hasattr(smtm, "Controller"))
        self.assertNotIn("Controller", smtm.__all__)
        # 텔레그램과 주피터 컨트롤러는 유지된다
        self.assertTrue(hasattr(smtm, "TelegramController"))
        self.assertTrue(hasattr(smtm, "JptController"))


if __name__ == "__main__":
    unittest.main()
