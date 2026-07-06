import json
import os
import unittest
import tempfile
from smtm import ProfileStore


PROFILE = {
    "name": "test-btc-virtual",
    "exchange": "UPB",
    "currency": "BTC",
    "budget": 500000,
    "virtual": True,
    "term": 60,
    "strategy": "BNH",
    "strategy_params": {},
    "safety": {"max_trade_amount": 100000},
}


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        self.store.save(PROFILE)
        loaded = self.store.load("test-btc-virtual")
        self.assertEqual(loaded, PROFILE)
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp.name, "test-btc-virtual.json")))

    def test_list_profiles_returns_summaries(self):
        self.store.save(PROFILE)
        self.store.save({**PROFILE, "name": "second", "strategy": "RSI"})
        profiles = self.store.list_profiles()
        names = {p["name"] for p in profiles}
        self.assertEqual(names, {"test-btc-virtual", "second"})
        self.assertIn("strategy", profiles[0])

    def test_delete_removes_profile(self):
        self.store.save(PROFILE)
        self.assertTrue(self.store.delete("test-btc-virtual"))
        self.assertEqual(self.store.list_profiles(), [])
        self.assertFalse(self.store.delete("test-btc-virtual"))

    def test_load_missing_profile_raises(self):
        with self.assertRaises(ValueError):
            self.store.load("nope")

    def test_save_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "name": "../evil"})
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "name": ""})

    def test_save_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "hack": 1})

    def test_save_rejects_missing_name(self):
        profile = dict(PROFILE)
        del profile["name"]
        with self.assertRaises(ValueError):
            self.store.save(profile)

    def test_load_ignores_corrupt_json_in_list(self):
        self.store.save(PROFILE)
        with open(os.path.join(self.tmp.name, "broken.json"), "w") as f:
            f.write("{not json")
        profiles = self.store.list_profiles()
        self.assertEqual(len(profiles), 1)

    def test_list_ignores_non_dict_json(self):
        self.store.save(PROFILE)
        with open(os.path.join(self.tmp.name, "weird.json"), "w") as f:
            f.write("[1, 2, 3]")
        profiles = self.store.list_profiles()
        self.assertEqual(len(profiles), 1)
