import io
import unittest
from setuptools import find_packages, setup

# Package meta-data.
NAME = "smtm"
DESCRIPTION = "make money using algorithm with python"
URL = "https://github.com/msaltnet/smtm"
EMAIL = "salt.jeong@gmail.com"
AUTHOR = "msalt"
VERSION = "0.1"

# What packages are required for this module to be executed?
REQUIRED = [
    "requests",
    "numpy",
    "matplotlib",
    "pandas",
    "mplfinance",
    "pyjwt",
    "python-dotenv",
    "jupyter",
]


def long_description():
    with io.open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()
    return readme


def smtm_test_suite():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover("tests", pattern="*test.py")
    return test_suite


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description(),
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=REQUIRED,
    extras_require={"dev": ["coverage"]},
    test_suite="setup.smtm_test_suite",
    zip_safe=False,
)
