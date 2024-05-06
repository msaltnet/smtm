import json
import pytest

@pytest.fixture(scope="function")
def upbit_1m_data_1set():
    loaded_data = None
    with open("tests/unit_tests/data/upbit_1m_20200220_170000-20200220_202000.json", "r") as f:
        loaded_data = json.load(f)
    return loaded_data

@pytest.fixture(scope="function")
def upbit_1m_data_2set():
    loaded_data = None
    with open("tests/unit_tests/data/upbit_1m_20200220_202000-20200220_210000", "r") as f:
        loaded_data = json.load(f)
    return loaded_data
