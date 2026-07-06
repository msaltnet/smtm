import os
import unittest
import tempfile
from unittest.mock import patch
from smtm import AccountStore


ACCOUNT = {
    "name": "main",
    "exchange": "UPB",
    "access_key_env": "SMTM_TEST_KEY_1",
    "secret_key_env": "SMTM_TEST_SECRET_1",
}


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AccountStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        self.store.save(ACCOUNT)
        self.assertEqual(self.store.load("main"), ACCOUNT)

    def test_save_never_stores_key_values(self):
        # 파일 내용에 환경변수 '이름'만 있고 값이 없어야 한다
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "REAL-KEY-VALUE"}):
            self.store.save(ACCOUNT)
        path = os.path.join(self.tmp.name, "main.json")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("SMTM_TEST_KEY_1", content)
        self.assertNotIn("REAL-KEY-VALUE", content)

    def test_missing_env_vars_reports_unset_names(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SMTM_TEST_KEY_1", None)
            os.environ.pop("SMTM_TEST_SECRET_1", None)
            missing = self.store.missing_env_vars(ACCOUNT)
        self.assertEqual(set(missing), {"SMTM_TEST_KEY_1", "SMTM_TEST_SECRET_1"})

    def test_missing_env_vars_empty_when_set(self):
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            self.assertEqual(self.store.missing_env_vars(ACCOUNT), [])

    def test_list_accounts_includes_env_ready(self):
        self.store.save(ACCOUNT)
        with patch.dict(os.environ, {"SMTM_TEST_KEY_1": "a", "SMTM_TEST_SECRET_1": "b"}):
            accounts = self.store.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "main")
        self.assertEqual(accounts[0]["exchange"], "UPB")
        self.assertTrue(accounts[0]["env_ready"])

    def test_validate_rejects_missing_required_field(self):
        for key in ("name", "exchange", "access_key_env", "secret_key_env"):
            broken = dict(ACCOUNT)
            del broken[key]
            with self.assertRaises(ValueError):
                self.store.validate(broken)

    def test_validate_rejects_unknown_field_and_bad_name(self):
        with self.assertRaises(ValueError):
            self.store.validate({**ACCOUNT, "secret_key": "raw-value"})
        with self.assertRaises(ValueError):
            self.store.validate({**ACCOUNT, "name": "../evil"})

    def test_delete(self):
        self.store.save(ACCOUNT)
        self.assertTrue(self.store.delete("main"))
        self.assertFalse(self.store.delete("main"))

    def test_load_missing_raises(self):
        with self.assertRaises(ValueError):
            self.store.load("nope")

    def test_list_survives_account_file_missing_required_keys(self):
        self.store.save(ACCOUNT)
        import json
        with open(os.path.join(self.tmp.name, "broken.json"), "w") as f:
            json.dump({"name": "broken"}, f)  # 필수 키 누락 dict
        accounts = self.store.list_accounts()  # 크래시 없이 동작
        names = [a["name"] for a in accounts]
        self.assertIn("main", names)
