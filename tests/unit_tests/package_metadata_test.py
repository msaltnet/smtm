import configparser
from pathlib import Path


def test_package_metadata_declares_openai_sdk():
    config = configparser.ConfigParser()
    config.read(Path(__file__).parents[2] / "setup.cfg")

    requirements = config["options"]["install_requires"]
    assert "openai" in requirements
