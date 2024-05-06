import unittest
from smtm import (
    DataProviderFactory,
    BinanceDataProvider,
    UpbitDataProvider,
    BithumbDataProvider,
    UpbitBinanceDataProvider,
)
from unittest.mock import *


class DataProviderFactoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_return_None_when_called_with_invalid_code(self):
        strategy = DataProviderFactory.create("")
        self.assertEqual(strategy, None)

    def test_create_return_correct_strategy(self):
        self.assertTrue(
            isinstance(DataProviderFactory.create("BNC"), BinanceDataProvider)
        )
        self.assertTrue(
            isinstance(DataProviderFactory.create("BTH"), BithumbDataProvider)
        )
        self.assertTrue(
            isinstance(DataProviderFactory.create("UPB"), UpbitDataProvider)
        )
        self.assertTrue(
            isinstance(DataProviderFactory.create("UBD"), UpbitBinanceDataProvider)
        )

    def test_get_name_return_None_when_called_with_invalid_code(self):
        strategy = DataProviderFactory.get_name("")
        self.assertEqual(strategy, None)

    def test_get_name_return_correct_strategy(self):
        self.assertTrue(DataProviderFactory.get_name("BNC"), BinanceDataProvider.NAME)
        self.assertTrue(DataProviderFactory.get_name("BTH"), BithumbDataProvider.NAME)
        self.assertTrue(DataProviderFactory.get_name("UPB"), UpbitDataProvider.NAME)
        self.assertTrue(
            DataProviderFactory.get_name("UBD"), UpbitBinanceDataProvider.NAME
        )

    def test_get_all_strategy_info_return_correct_info(self):
        all = DataProviderFactory.get_all_strategy_info()
        self.assertTrue(all[0]["name"], BinanceDataProvider.NAME)
        self.assertTrue(all[0]["code"], BinanceDataProvider.CODE)
        self.assertTrue(all[0]["class"], BinanceDataProvider)
        self.assertTrue(all[1]["name"], UpbitDataProvider.NAME)
        self.assertTrue(all[1]["code"], UpbitDataProvider.CODE)
        self.assertTrue(all[1]["class"], UpbitDataProvider)
        self.assertTrue(all[2]["name"], BithumbDataProvider.NAME)
        self.assertTrue(all[2]["code"], BithumbDataProvider.CODE)
        self.assertTrue(all[2]["class"], BithumbDataProvider)
        self.assertTrue(all[3]["name"], UpbitBinanceDataProvider.NAME)
        self.assertTrue(all[3]["code"], UpbitBinanceDataProvider.CODE)
        self.assertTrue(all[3]["class"], UpbitBinanceDataProvider)
